"""Offline loader controls. Live check/upload status is documented separately."""

import contextlib
import csv
import io
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.ingestion import load_gl as loader
from src.synthetic.generate import generate, load_config, write_tables


def destination():
    return SimpleNamespace(location=loader.LOCATION, table_type="TABLE", time_partitioning=None,
        range_partitioning=None, table_constraints=None, clustering_fields=None,
        schema=loader.gl_schema(), expires=datetime.now(timezone.utc) + timedelta(days=50), num_rows=2)


class LoadGLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.source = Path(cls.temp.name)
        config = load_config(loader.ROOT / "config/scenario.json")
        write_tables(generate(config), cls.source, config)

    def test_generated_source_matches_known_controls(self):
        payload, expected, digest = loader.prepare_source(self.source)
        self.assertEqual(expected, {"rows": 16648, "debits": 7774104010, "credits": 7774104010})
        self.assertTrue(payload.startswith(b"line_id,"))
        self.assertEqual(len(digest), 64)

    def test_changed_source_rejected_before_load(self):
        path = self.source / "netsuite/gl_lines.csv"
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"\n")
            with self.assertRaisesRegex(ValueError, "differs"):
                loader.prepare_source(self.source)
        finally:
            path.write_bytes(original)

    def test_billing_unknown_or_enabled_or_linked_blocks(self):
        for info in ({}, {"billingEnabled": "false"}, {"billingEnabled": True}, {"billingEnabled": False, "billingAccountName": "linked"}):
            with self.subTest(info=info), self.assertRaises(ValueError):
                loader.require_unbilled(info)
        loader.require_unbilled({"billingEnabled": False, "billingAccountName": ""})

    def test_preview_does_not_authenticate(self):
        with patch.object(loader, "prepare_source", return_value=(b"x", {"rows": 2}, "hash")), patch.object(loader.google.auth, "default") as auth, contextlib.redirect_stdout(io.StringIO()):
            loader.run()
        auth.assert_not_called()

    def client(self):
        client = Mock()
        client.get_dataset.return_value = SimpleNamespace(location=loader.LOCATION,
            default_table_expiration_ms=5097600000, default_partition_expiration_ms=5097600000)
        client.get_table.return_value = destination()
        return client

    def test_destination_rejects_region_schema_expiry_and_partitioning(self):
        for attribute, bad in [("location", "US"), ("schema", []), ("expires", None), ("time_partitioning", True)]:
            with self.subTest(attribute=attribute):
                client = self.client()
                setattr(client.get_table.return_value, attribute, bad)
                with self.assertRaises(ValueError):
                    loader.check_destination(client)
                client.load_table_from_file.assert_not_called()

    def test_missing_partition_default_rejected(self):
        client = self.client()
        client.get_dataset.return_value.default_partition_expiration_ms = None
        with self.assertRaisesRegex(ValueError, "expiration"):
            loader.check_destination(client)

    def test_check_mode_never_loads_or_queries(self):
        client = self.client()
        with patch.object(loader, "prepare_source", return_value=(b"x", {"rows": 2}, "hash")), patch.object(loader.google.auth, "default", return_value=(object(), loader.PROJECT)), patch.object(loader, "check_billing"), patch.object(loader.bigquery, "Client") as constructor, contextlib.redirect_stdout(io.StringIO()):
            constructor.return_value.__enter__.return_value = client
            loader.run("check")
        client.load_table_from_file.assert_not_called()
        client.query.assert_not_called()

    def test_two_refreshes_replace_and_reconcile_instead_of_appending(self):
        client = self.client()
        original = loader.check_destination(client)
        payload = b"debit_cents,credit_cents\n100,0\n0,100\n"
        expected = {"rows": 2, "debits": 100, "credits": 100}
        state = {"rows": 0, "debits": 0, "credits": 0}
        def load(handle, target, **kwargs):
            rows = list(csv.DictReader(io.StringIO(handle.read().decode())))
            config = kwargs["job_config"]
            self.assertEqual(target, loader.TARGET)
            self.assertEqual(config.create_disposition, "CREATE_NEVER")
            self.assertEqual(kwargs["num_retries"], 0)
            if config.write_disposition == "WRITE_TRUNCATE":
                state.update(rows=0, debits=0, credits=0)
            state["rows"] += len(rows)
            state["debits"] += sum(int(r["debit_cents"]) for r in rows)
            state["credits"] += sum(int(r["credit_cents"]) for r in rows)
            client.get_table.return_value.num_rows = state["rows"]
            return Mock()
        client.load_table_from_file.side_effect = load
        client.query.side_effect = lambda *a, **k: SimpleNamespace(result=lambda **k: [dict(state)])
        with contextlib.redirect_stdout(io.StringIO()):
            loader.refresh(client, payload, expected, original)
            loader.refresh(client, payload, expected, original)
        self.assertEqual(state, expected)
        self.assertEqual(client.query.call_args.kwargs["job_config"].maximum_bytes_billed, loader.QUERY_LIMIT)
        ids = [call.kwargs["job_id"] for call in client.load_table_from_file.call_args_list]
        self.assertNotEqual(ids[0], ids[1])

    def test_failed_job_stops_without_resubmission_or_query(self):
        client = self.client()
        client.load_table_from_file.return_value.result.side_effect = TimeoutError("wait expired")
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(TimeoutError):
            loader.refresh(client, b"test", {"rows": 2}, destination())
        self.assertEqual(client.load_table_from_file.call_count, 1)
        client.query.assert_not_called()

    def test_wrong_post_load_finance_totals_fail(self):
        client = self.client()
        client.query.return_value.result.return_value = [{"rows": 2, "debits": 0, "credits": 0}]
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "finance totals"):
            loader.refresh(client, b"test", {"rows": 2, "debits": 100, "credits": 100}, client.get_table.return_value)
