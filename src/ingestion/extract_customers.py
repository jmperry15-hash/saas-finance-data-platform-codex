"""Collect every page from the local mock API and publish a complete CSV snapshot."""

import argparse
import csv
import hashlib
import io
import re
import tempfile
import time
from datetime import date
from pathlib import Path

import requests

from src.ingestion.mock_api import DEFAULT_PORT
from src.ingestion.validate_gl import ROOT
from src.synthetic.schema import SCHEMAS

OUTPUT = ROOT / "data/local/api/customers.csv"
RETRYABLE = {429, 500, 502, 503, 504}


def fetch_page(session, url, page, size):
    """Retry a read-only GET at most three times, with short exponential backoff."""
    for attempt in range(3):
        try:
            with session.get(url, params={"page": page, "page_size": size},
                             timeout=(3, 5), allow_redirects=False) as response:
                if response.status_code in RETRYABLE and attempt < 2:
                    print(f"RETRY page {page}: HTTP {response.status_code}; attempt {attempt+2}/3", flush=True)
                else:
                    response.raise_for_status()
                    if response.status_code != 200:
                        raise ValueError("Expected HTTP 200; redirects are not followed.")
                    return response.json()
        except (requests.Timeout, requests.ConnectionError):
            if attempt == 2:
                raise
            print(f"RETRY page {page}: connection/timeout; attempt {attempt+2}/3", flush=True)
        time.sleep(0.25 * 2**attempt)
    raise RuntimeError("Retry limit reached")


def validate_records(records):
    columns = set(SCHEMAS["salesforce/customers"])
    seen = set()
    for row in records:
        if not isinstance(row, dict) or set(row) != columns or not all(isinstance(v, str) for v in row.values()):
            raise ValueError("Customer schema differs from the contract.")
        if any(not row[c].strip() for c in columns - {"acquired_date"}):
            raise ValueError("Required customer fields cannot be blank.")
        if row["customer_id"] in seen:
            raise ValueError("Duplicate customer_id across API pages.")
        seen.add(row["customer_id"])
        if row["acquired_date"]:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["acquired_date"]):
                raise ValueError("Expected ISO acquired_date.")
            date.fromisoformat(row["acquired_date"])


def extract(port=DEFAULT_PORT, page_size=25, output=OUTPUT):
    if not 1 <= port <= 65535 or not 1 <= page_size <= 100:
        raise ValueError("Use port 1-65535 and page_size 1-100.")
    records, total, snapshot = [], None, None
    with requests.Session() as session:
        # This lesson contacts only loopback, without proxy/.netrc authentication.
        session.trust_env = False
        for page in range(1, 1001):
            batch = fetch_page(session, f"http://127.0.0.1:{port}/customers", page, page_size)
            if not isinstance(batch, dict) or set(batch) != {"data", "page", "page_size", "total", "snapshot", "next_page"}:
                raise ValueError("Unexpected API response fields.")
            if type(batch["page"]) is not int or batch["page"] != page or type(batch["page_size"]) is not int or batch["page_size"] != page_size:
                raise ValueError("API returned the wrong page or page size.")
            if type(batch["total"]) is not int or not 0 <= batch["total"] <= 10000 or not isinstance(batch["snapshot"], str) or not re.fullmatch(r"[0-9a-f]{64}", batch["snapshot"]):
                raise ValueError("Invalid API total or snapshot.")
            if page == 1:
                total, snapshot = batch["total"], batch["snapshot"]
            elif (total, snapshot) != (batch["total"], batch["snapshot"]):
                raise ValueError("API snapshot changed between pages. Restart extraction.")
            expected_count = min(page_size, total - len(records))
            if not isinstance(batch["data"], list) or len(batch["data"]) != expected_count:
                raise ValueError("Incomplete or oversized API page.")
            records.extend(batch["data"])
            more = len(records) < total
            if (more and (type(batch["next_page"]) is not int or batch["next_page"] != page+1)) or (not more and batch["next_page"] is not None):
                raise ValueError("Invalid next_page; refusing to publish a partial extract.")
            print(f"PAGE {page}: {len(batch['data'])} customers ({len(records)}/{total})", flush=True)
            if not more:
                break
        else:
            raise ValueError("Exceeded the exercise's 1,000-page limit.")
    validate_records(records)
    # Only publish after ALL pages and controls succeed. Keep an older CSV on error.
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=SCHEMAS["salesforce/customers"])
    writer.writeheader()
    writer.writerows(records)
    content = text.getvalue().encode("utf-8")
    if hashlib.sha256(content).hexdigest() != snapshot:
        raise ValueError("Extract differs from the mock API source snapshot.")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        temporary.replace(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(f"PASS: {len(records)} unique customers across {page} pages; snapshot matches source.")
    print(f"Saved: {output}")
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--page-size", type=int, default=25)
    args = parser.parse_args()
    try:
        extract(args.port, args.page_size)
    except (ValueError, OSError, requests.RequestException) as exc:
        parser.exit(1, f"Stopped: {exc}\nNo new customer snapshot was published.\n")


if __name__ == "__main__":
    main()
