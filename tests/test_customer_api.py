"""Local HTTP integration and failure tests; no cloud or vendor calls."""

import contextlib
import io
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from src.ingestion import extract_customers as extractor
from src.ingestion.mock_api import create_server, source_customers
from src.synthetic.generate import ROOT, generate, load_config, write_tables


def response(status, body=b'{}'):
    result = requests.Response()
    result.status_code = status
    result._content = body
    result._content_consumed = True
    result.url = "http://127.0.0.1:8765/customers"
    return result


class CustomerAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.source = Path(cls.temp.name) / "source"
        config = load_config(ROOT / "config/scenario.json")
        write_tables(generate(config), cls.source, config)

    @contextlib.contextmanager
    def server(self, fail_page=None):
        server = create_server(0, self.source, fail_page=fail_page)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        try:
            yield server.server_port
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    def test_live_http_six_pages_and_repeat_match_original_csv(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()) as log, self.server() as port:
            output = Path(folder) / "customers.csv"
            records = extractor.extract(port, output=output)
            first = output.read_bytes()
            extractor.extract(port, output=output)
            self.assertEqual(len(records), 130)
            self.assertEqual(first, (self.source / "salesforce/customers.csv").read_bytes())
            self.assertEqual(output.read_bytes(), first)
            self.assertIn("PAGE 6: 5 customers (130/130)", log.getvalue())

    def test_failed_page_does_not_publish_partial_or_destroy_previous_extract(self):
        for previous in (None, b"previous complete snapshot"):
            with self.subTest(previous=previous), tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()), self.server(fail_page=3) as port, patch.object(extractor.time, "sleep"):
                output = Path(folder) / "customers.csv"
                if previous is not None:
                    output.write_bytes(previous)
                with self.assertRaises(requests.HTTPError):
                    extractor.extract(port, output=output)
                if previous is None:
                    self.assertFalse(output.exists())
                else:
                    self.assertEqual(output.read_bytes(), previous)

    def test_server_returns_400_for_invalid_page_and_404_for_unknown_route(self):
        with contextlib.redirect_stdout(io.StringIO()), self.server() as port, requests.Session() as session:
            session.trust_env = False
            for path, expected in [("/customers?page=0", 400), ("/customers?page_size=101", 400), ("/customers?page=2&page=3", 400), ("/unknown", 404)]:
                result = session.get(f"http://127.0.0.1:{port}{path}", timeout=3)
                self.assertEqual(result.status_code, expected)

    def test_transient_error_retries_and_recovers(self):
        session = Mock()
        session.get.side_effect = [response(503), response(200, b'{"ok": true}')]
        with contextlib.redirect_stdout(io.StringIO()), patch.object(extractor.time, "sleep") as sleep:
            result = extractor.fetch_page(session, "http://127.0.0.1:8765/customers", 1, 25)
        self.assertEqual(result, {"ok": True})
        self.assertEqual(session.get.call_count, 2)
        sleep.assert_called_once_with(0.25)

    def test_timeouts_stop_after_three_attempts(self):
        session = Mock()
        session.get.side_effect = requests.Timeout("test timeout")
        with contextlib.redirect_stdout(io.StringIO()), patch.object(extractor.time, "sleep") as sleep, self.assertRaises(requests.Timeout):
            extractor.fetch_page(session, "http://127.0.0.1:8765/customers", 1, 25)
        self.assertEqual(session.get.call_count, 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [0.25, 0.5])

    def test_bad_request_and_invalid_json_are_not_retried(self):
        for result in [response(400), response(200, b'not JSON'), response(302)]:
            with self.subTest(status=result.status_code):
                session = Mock()
                session.get.return_value = result
                with self.assertRaises((ValueError, requests.HTTPError)):
                    extractor.fetch_page(session, "http://127.0.0.1:8765/customers", 1, 25)
                self.assertEqual(session.get.call_count, 1)

    def batches(self):
        records, digest = source_customers(self.source)
        return [{"data": records[i:i+25], "page": i//25+1, "page_size": 25,
                 "total": 130, "snapshot": digest, "next_page": i//25+2 if i+25 < 130 else None}
                for i in range(0, 130, 25)]

    def test_bad_pagination_and_mixed_snapshots_never_publish(self):
        for fault in ("loop", "truncated", "snapshot", "duplicate", "content"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as folder:
                batches = self.batches()
                if fault == "loop":
                    batches[0]["next_page"] = 1
                elif fault == "truncated":
                    batches[0]["data"].pop()
                elif fault == "snapshot":
                    batches[1]["snapshot"] = "0" * 64
                elif fault == "duplicate":
                    batches[1]["data"][0]["customer_id"] = batches[0]["data"][0]["customer_id"]
                else:
                    batches[0]["data"][0]["customer_name"] = "Changed content"
                output = Path(folder) / "customers.csv"
                with patch.object(extractor, "fetch_page", side_effect=batches), contextlib.redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
                    extractor.extract(output=output)
                self.assertFalse(output.exists())

    def test_schema_and_invalid_dates_rejected(self):
        records, _ = source_customers(self.source)
        for field, value in [("customer_name", ""), ("customer_id", None), ("acquired_date", "2026-02-30")]:
            with self.subTest(field=field):
                row = dict(records[0], **{field: value})
                with self.assertRaises(ValueError):
                    extractor.validate_records([row])
