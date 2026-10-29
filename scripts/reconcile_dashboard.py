"""Compare the existing local dashboard snapshot with bounded BigQuery reads.

Default: inspect local snapshot only. --check-cloud: compare every field/row.
Never changes raw data, the dashboard snapshot, or the published website.
"""

import argparse
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

KEYS = {
    "finance": ("month", "department_id", "account_id"),
    "saas": ("month", "customer_id"),
    "workforce": ("month", "department_id"),
    "bookings": ("booking_id",),
}
MAX_BYTES = 50 * 1024 * 1024


def normalize(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        if value != value.to_integral_value():
            raise ValueError("Unexpected fractional value; amounts must remain integer cents.")
        return int(value)
    return value


def index_rows(rows, keys):
    if not rows:
        raise ValueError("Empty dataset cannot establish reconciliation.")
    indexed = {}
    columns = set(rows[0])
    for row in rows:
        if set(row) != columns:
            raise ValueError("Inconsistent columns within dataset.")
        normalized = {k: normalize(v) for k, v in row.items()}
        key = tuple(normalized[k] for k in keys)
        if any(v is None for v in key) or key in indexed:
            raise ValueError(f"Missing or duplicate key: {key}")
        indexed[key] = normalized
    return indexed


def compare_rows(local, cloud, keys):
    """Exact comparison: no rounding, dropped columns, or row-count-only success."""
    left, right = index_rows(local, keys), index_rows(cloud, keys)
    if left.keys() != right.keys():
        raise ValueError(f"Row keys differ: {len(left.keys() - right.keys())} local-only; "
                         f"{len(right.keys() - left.keys())} cloud-only.")
    for key, expected in left.items():
        actual = right[key]
        if expected.keys() != actual.keys():
            raise ValueError(f"Columns differ at {key}.")
        different = [field for field in expected if expected[field] != actual[field]]
        if different:
            raise ValueError(f"Values differ at {key}: {', '.join(different)}.")
    return len(left)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-cloud", action="store_true")
    parser.add_argument("--snapshot", type=Path, default=ROOT / "dashboard-site/src/data.json")
    parser.add_argument("--receipt", type=Path, default=ROOT / "data/local/dashboard_reconciliation.json")
    args = parser.parse_args()
    snapshot_bytes = args.snapshot.read_bytes()
    snapshot = json.loads(snapshot_bytes)
    for name, keys in KEYS.items():
        rows = snapshot["queries"][name]["rows"]
        index_rows(rows, keys)
        print(f"LOCAL {name}: {len(rows):,} rows", flush=True)
    if not args.check_cloud:
        print("Local structure checked. Add --check-cloud to reconcile with BigQuery.")
        return

    from scripts.dbt_lesson import LOCATION, PROJECT, unbilled_credentials
    from google.cloud import bigquery

    receipt_path = args.receipt
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "status": "RUNNING", "started_at": datetime.now(timezone.utc).isoformat(),
        "project": PROJECT, "location": LOCATION,
        "snapshot_sha256": hashlib.sha256(snapshot_bytes).hexdigest(),
        "snapshot_generated_at": snapshot.get("generatedAt"),
        "maximum_bytes_billed_per_query": MAX_BYTES, "datasets": {},
        "scope": "Local dashboard snapshot versus live dbt outputs; no website refresh or raw-source reload.",
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    try:
        credentials = unbilled_credentials()
        print("Billing disabled; running four read-only reconciliation queries.", flush=True)
        with bigquery.Client(project=PROJECT, credentials=credentials, location=LOCATION) as client:
            for name, keys in KEYS.items():
                sql = (ROOT / "sql/dashboard" / f"{name}.sql").read_text()
                config = bigquery.QueryJobConfig(maximum_bytes_billed=MAX_BYTES)
                dry = client.query(sql, job_config=bigquery.QueryJobConfig(
                    dry_run=True, use_query_cache=False, maximum_bytes_billed=MAX_BYTES
                ), timeout=30)
                if dry.total_bytes_processed is None or dry.total_bytes_processed > MAX_BYTES:
                    raise ValueError(f"{name}: query estimate exceeds 50 MiB or is unavailable.")
                job = client.query(sql, job_config=config, timeout=30, job_retry=None)
                rows = [dict(row) for row in job.result(timeout=120)]
                entry = {"job_id": job.job_id, "sql": sql,
                         "estimated_bytes": dry.total_bytes_processed,
                         "processed_bytes": job.total_bytes_processed,
                         "cloud_rows": rows, "status": "CHECKING"}
                receipt["datasets"][name] = entry
                count = compare_rows(snapshot["queries"][name]["rows"], rows, keys)
                entry.update(status="PASS", matched_rows=count)
                print(f"PASS {name}: {count:,} rows; every field matches.", flush=True)
        receipt["status"] = "PASS"
    except Exception as error:
        receipt.update(status="FAIL", error=str(error))
        raise
    finally:
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        receipt_path.write_text(json.dumps(receipt, indent=2, default=normalize) + "\n")
        print(f"Receipt: {receipt_path}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(f"Stopped: {error}") from error
