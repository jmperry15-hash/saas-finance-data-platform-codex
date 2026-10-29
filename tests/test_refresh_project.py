"""Failure and repeatability controls; no cloud access in this test suite."""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from google.api_core.exceptions import NotFound
from scripts.refresh_project import dashboard_candidate, promote, run_lock
from src.ingestion import refresh_sources as loader
from src.synthetic.generate import generate, load_config, write_tables


def table(name, rows=1):
    return SimpleNamespace(location=loader.LOCATION, table_type="TABLE",
        time_partitioning=None, range_partitioning=None, table_constraints=None,
        clustering_fields=None, schema=loader.schema(name), num_rows=rows,
        expires=datetime.now(timezone.utc) + timedelta(days=30))


class RefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cfg = load_config(Path(__file__).resolve().parents[1] / "config/scenario.json")
        write_tables(generate(cfg), cls.root / "source", cfg)

    def test_freeze_is_independent_and_detects_changed_input(self):
        payloads, tables, report, _ = loader.freeze_sources(self.root / "source", self.root / "frozen")
        self.assertEqual(sum(map(len, tables.values())), 23794)
        self.assertEqual(report["checks_passed"], 764)
        path = self.root / "source/shared/departments.csv"
        previous = path.read_bytes()
        try:
            path.write_bytes(previous + b"\n")
            self.assertEqual(payloads["shared/departments"], previous)
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                loader.freeze_sources(self.root / "source", self.root / "bad")
            self.assertFalse((self.root / "bad").exists())
        finally:
            path.write_bytes(previous)

    def client(self):
        client = Mock()
        client.get_dataset.return_value = SimpleNamespace(location=loader.LOCATION,
            default_table_expiration_ms=5097600000, default_partition_expiration_ms=5097600000)
        client.get_table.side_effect = lambda target, **kwargs: table(target.split(".raw_")[1].replace(".", "/"))
        return client

    def test_late_preflight_error_makes_no_writes(self):
        client = self.client()
        names = list(loader.SCHEMAS)
        objects = [table(n) for n in names]
        objects[-1].schema = []
        client.get_table.side_effect = objects
        with self.assertRaisesRegex(ValueError, "Schema mismatch"):
            loader.preflight(client)
        self.assertEqual(client.get_table.call_count, 14)
        client.load_table_from_file.assert_not_called()

    def test_missing_table_is_recoverable_but_wrong_region_is_not(self):
        client = self.client()
        client.get_table.side_effect = NotFound("expired")
        self.assertTrue(all(v is None for v in loader.preflight(client).values()))
        client.get_dataset.return_value.location = "EU"
        with self.assertRaisesRegex(ValueError, "location/expiration"):
            loader.preflight(client)
        client.load_table_from_file.assert_not_called()

    def test_load_replaces_never_appends_and_checks_exact_values(self):
        name = "shared/departments"
        row = {"department_id": "D01", "department_name": "Customer Success", "function": "Cost of revenue"}
        for missing in (False, True):
            for wrong in (False, True):
                with self.subTest(missing=missing, wrong=wrong):
                    client, original = Mock(), table(name)
                    client.get_table.return_value = original
                    actual = {**row, "department_name": "wrong"} if wrong else row
                    query = Mock(job_id="query-123", total_bytes_processed=10)
                    query.result.return_value = [actual]
                    client.query.side_effect = [SimpleNamespace(total_bytes_processed=10), query]
                    receipt = {"tables": {}}
                    with patch.object(loader, "SCHEMAS", {name: loader.SCHEMAS[name]}):
                        if wrong:
                            with self.assertRaisesRegex(ValueError, "Values differ"):
                                loader.refresh(client, {name: b"csv"}, {name: [row]}, {name: None if missing else original}, receipt, Mock())
                        else:
                            loader.refresh(client, {name: b"csv"}, {name: [row]}, {name: None if missing else original}, receipt, Mock())
                    config = client.load_table_from_file.call_args.kwargs["job_config"]
                    self.assertEqual(config.write_disposition, "WRITE_TRUNCATE")
                    self.assertEqual(config.create_disposition, "CREATE_IF_NEEDED" if missing else "CREATE_NEVER")
                    self.assertEqual(client.load_table_from_file.call_args.kwargs["num_retries"], 0)

    def test_build_failure_restores_previous_dashboard(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot, dist, backup = root / "data.json", root / "dist", root / "backup"
            snapshot.write_text('{"id":"old"}')
            dist.mkdir(); backup.mkdir()
            (dist / "index.html").write_text("previous app")
            def fail():
                (dist / "index.html").write_text("broken build")
                raise ValueError("build failed")
            with self.assertRaisesRegex(ValueError, "build failed"):
                promote({"id": "new"}, snapshot, dist, backup, fail)
            self.assertEqual(snapshot.read_text(), '{"id":"old"}')
            self.assertEqual((dist / "index.html").read_text(), "previous app")

    def test_failed_reconciliation_cannot_be_exported(self):
        with self.assertRaisesRegex(ValueError, "passed reconciliation"):
            dashboard_candidate({"id": "keep"}, {}, {"status": "FAIL"})

    def test_export_preserves_identity_and_records_real_warehouse_provenance(self):
        from scripts.reconcile_dashboard import KEYS
        expected = {"queries": {}}
        receipt = {"status": "PASS", "finished_at": "2026-10-29T01:00:00Z", "datasets": {}}
        for name, keys in KEYS.items():
            row = {key: "2025-01-01" if key == "month" else "ID01" for key in keys}
            row["value"] = None
            expected["queries"][name] = {"rows": [row], "source": {"type": "sqlite", "files": ["old.csv"], "grain": "test grain"}}
            receipt["datasets"][name] = {"status": "PASS", "cloud_rows": [row], "job_id": "bq-job",
                "sql": "SELECT * FROM `saas-finance-learning-512616.finance.report`"}
        template = {"id": "keep-this-id", "title": "Existing title", "filters": [{"id": "date"}], "queries": {}}
        candidate = dashboard_candidate(template, expected, receipt)
        self.assertEqual(candidate["id"], template["id"])
        self.assertEqual(candidate["filters"], template["filters"])
        self.assertEqual(candidate["queries"]["finance"]["source"]["type"], "bigquery")
        self.assertNotIn("files", candidate["queries"]["finance"]["source"])
        self.assertIsNone(candidate["queries"]["finance"]["rows"][0]["value"])
        self.assertEqual(template["queries"], {})

    def test_timeout_keeps_job_id_and_does_not_retry_or_verify(self):
        name = "shared/departments"
        client = Mock()
        client.load_table_from_file.return_value.result.side_effect = TimeoutError("inspect job")
        receipt = {"tables": {}}
        with patch.object(loader, "SCHEMAS", {name: loader.SCHEMAS[name]}), self.assertRaises(TimeoutError):
            loader.refresh(client, {name: b"csv"}, {name: [{}]}, {name: table(name)}, receipt, Mock())
        self.assertTrue(receipt["tables"][name]["load_job_id"].startswith("finance_batch_"))
        self.assertEqual(client.load_table_from_file.call_count, 1)
        client.query.assert_not_called()

    def test_concurrent_run_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "lock"
            with run_lock(path), self.assertRaisesRegex(ValueError, "Another manual refresh"):
                with run_lock(path):
                    self.fail("Second run entered")


if __name__ == "__main__":
    unittest.main()
