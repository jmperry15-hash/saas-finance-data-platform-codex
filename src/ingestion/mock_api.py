"""Read-only local customer API for learning pagination; not a real Salesforce API."""

import argparse
import csv
import hashlib
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from src.ingestion.validate_gl import ROOT
from src.synthetic.schema import SCHEMAS

DEFAULT_PORT = 8765


def source_customers(folder=ROOT / "data/generated"):
    manifest = json.loads((folder / "manifest.json").read_text())
    payload = (folder / "salesforce/customers.csv").read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    expected = manifest["files"]["salesforce/customers"]
    if manifest.get("synthetic_only") is not True or digest != expected["sha256"]:
        raise ValueError("Expected unchanged synthetic customers from the generator.")
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8")))
    if reader.fieldnames != list(SCHEMAS["salesforce/customers"]):
        raise ValueError("Unexpected customer columns.")
    records = list(reader)
    if len(records) != expected["rows"]:
        raise ValueError("Customer row count differs from the manifest.")
    return records, digest


def create_server(port=DEFAULT_PORT, folder=ROOT / "data/generated", fail_page=None):
    # Hold a fixed snapshot for all pages so files changing on disk cannot mix batches.
    records, digest = source_customers(folder)

    class CustomerHandler(BaseHTTPRequestHandler):
        def respond(self, status, content):
            payload = json.dumps(content).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path != "/customers":
                self.respond(404, {"error": "Use /customers?page=1&page_size=25"})
                return
            try:
                params = parse_qs(url.query, keep_blank_values=True)
                if set(params) - {"page", "page_size"} or any(len(v) != 1 for v in params.values()):
                    raise ValueError()
                page = int(params.get("page", ["1"])[0])
                size = int(params.get("page_size", ["25"])[0])
                if page < 1 or not 1 <= size <= 100:
                    raise ValueError()
            except ValueError:
                self.respond(400, {"error": "page must be positive; page_size must be 1-100"})
                return
            if page == fail_page:
                self.respond(503, {"error": "Intentional practice failure on this page"})
                return
            start = (page - 1) * size
            if page > max(1, (len(records) + size - 1) // size):
                self.respond(400, {"error": "Page is beyond this snapshot"})
                return
            self.respond(200, {"data": records[start:start+size], "page": page,
                "page_size": size, "total": len(records), "snapshot": digest,
                "next_page": page + 1 if start + size < len(records) else None})

        def log_message(self, format, *args):
            # Status only; don't print request headers or customer records.
            print("API: " + format % args, flush=True)

    return ThreadingHTTPServer(("127.0.0.1", port), CustomerHandler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--fail-page", type=int, help="Return HTTP 503 on this page for the failure exercise")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or (args.fail_page is not None and args.fail_page < 1):
        parser.error("Use port 1-65535 and a positive fail-page.")
    try:
        with create_server(args.port, fail_page=args.fail_page) as server:
            print(f"Mock API running: http://127.0.0.1:{server.server_port}/customers?page=1&page_size=25", flush=True)
            print("Leave this Terminal open. Press Ctrl+C to stop. Synthetic data only.", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        print("\nMock API stopped.")
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Stopped: {exc}\n")


if __name__ == "__main__":
    main()
