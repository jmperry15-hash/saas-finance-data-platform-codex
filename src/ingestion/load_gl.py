"""Lesson: validate, batch-replace one existing BigQuery table, then reconcile.

No flag: local preview. --check: cloud metadata only. --upload: replace GL rows.
"""

import argparse
import hashlib
import io
import json
import uuid
from datetime import datetime, timedelta, timezone

import google.auth
from google.auth.transport.requests import AuthorizedSession
from google.cloud import bigquery

from src.ingestion.validate_gl import ROOT, OPTIONAL_COLUMNS, read_gl
from src.synthetic.schema import SCHEMAS
from src.synthetic.validate import read_tables, validate

PROJECT = "saas-finance-learning-512616"
DATASET = PROJECT + ".raw_netsuite"
TARGET = DATASET + ".gl_lines"
LOCATION = "us-south1"
SOURCE = ROOT / "data/generated"
MAX_BYTES = 25 * 1024 * 1024
QUERY_LIMIT = 10 * 1024 * 1024


def gl_schema():
    return [bigquery.SchemaField(
        name, "INTEGER" if name.endswith("_cents") else "DATE" if name == "month" else "STRING",
        mode="NULLABLE" if name in OPTIONAL_COLUMNS else "REQUIRED",
    ) for name in SCHEMAS["netsuite/gl_lines"]]


def prepare_source(folder=SOURCE):
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest.get("synthetic_only") is not True:
        raise ValueError("Expected the synthetic generator's manifest.")
    path = folder / "netsuite/gl_lines.csv"
    with path.open("rb") as handle:
        payload = handle.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("GL CSV exceeds the 25 MiB exercise limit.")
    digest = hashlib.sha256(payload).hexdigest()
    if digest != manifest["files"]["netsuite/gl_lines"]["sha256"]:
        raise ValueError("GL CSV differs from its generated manifest. Regenerate and validate the sources first.")
    frame = read_gl(io.BytesIO(payload))
    # Reuse the full source controls so a balanced but incomplete GL cannot pass.
    report = validate(read_tables(folder), manifest["config"])
    expected = {"rows": len(frame), "debits": int(frame.debit_cents.sum()), "credits": int(frame.credit_cents.sum())}
    if expected != {"rows": report["rows"]["netsuite/gl_lines"], "debits": report["control_totals"]["gl_debits_cents"], "credits": report["control_totals"]["gl_credits_cents"]}:
        raise ValueError("GL changed during validation. Run again after source generation finishes.")
    return payload, expected, digest


def require_unbilled(info):
    if info.get("billingEnabled") is not False or info.get("billingAccountName"):
        raise ValueError("Billing must be confirmed disabled with no linked account. No upload performed.")


def check_billing(credentials):
    # Use the same ADC identity as the BigQuery client, not a separate CLI login.
    with AuthorizedSession(credentials) as session:
        response = session.get(f"https://cloudbilling.googleapis.com/v1/projects/{PROJECT}/billingInfo", timeout=30)
        response.raise_for_status()
        require_unbilled(response.json())


def schema_signature(fields):
    return [(f.name, {"INT64": "INTEGER"}.get(f.field_type, f.field_type), f.mode) for f in fields]


def check_destination(client):
    dataset = client.get_dataset(DATASET, timeout=30)
    table = client.get_table(TARGET, timeout=30)
    if dataset.location != LOCATION or table.location != LOCATION:
        raise ValueError("Expected the existing us-south1 dataset and table.")
    for expiry in (dataset.default_table_expiration_ms, dataset.default_partition_expiration_ms):
        if expiry is None or not 0 < expiry < 60 * 86400000:
            raise ValueError("Dataset must retain Sandbox-compatible expiration defaults.")
    if table.table_type != "TABLE" or table.time_partitioning or table.range_partitioning:
        raise ValueError("This lesson expects the existing unpartitioned GL table.")
    if table.table_constraints or table.clustering_fields:
        raise ValueError("This simple refresh does not manage constraints or clustering.")
    if schema_signature(table.schema) != schema_signature(gl_schema()):
        raise ValueError("Existing GL schema differs; review before replacing data.")
    now = datetime.now(timezone.utc)
    if table.expires is None or not now < table.expires <= now + timedelta(days=60):
        raise ValueError("Existing table must have a future expiration within 60 days.")
    return table


def refresh(client, payload, expected, original):
    job_id = "finance_gl_" + uuid.uuid4().hex
    print(f"LOAD {TARGET}; replacing rows; job_id={job_id}", flush=True)
    config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        schema=gl_schema(), skip_leading_rows=1, max_bad_records=0,
        autodetect=False, ignore_unknown_values=False,
        create_disposition=bigquery.CreateDisposition.CREATE_NEVER,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    # Upload the exact bytes validated above. Do not reopen a changing source file.
    # Keep the job ID if a timeout occurs; don't automatically submit another job.
    job = client.load_table_from_file(io.BytesIO(payload), TARGET, size=len(payload),
        job_config=config, job_id=job_id, location=LOCATION, num_retries=0, timeout=60)
    job.result(timeout=120)
    table = client.get_table(TARGET, timeout=30)
    if table.num_rows != expected["rows"] or schema_signature(table.schema) != schema_signature(gl_schema()):
        raise ValueError("Load finished but row count/schema verification failed. Inspect the job before rerunning.")
    if table.expires != original.expires:
        raise ValueError("Load finished but table expiration changed. Review before rerunning.")
    # Bound the verification query; compare cents without float rounding.
    sql = f"SELECT COUNT(*) AS `rows`, SUM(debit_cents) AS debits, SUM(credit_cents) AS credits FROM `{TARGET}`"
    query = client.query(sql, location=LOCATION, timeout=30,
        job_config=bigquery.QueryJobConfig(maximum_bytes_billed=QUERY_LIMIT, use_query_cache=False))
    actual = dict(next(iter(query.result(timeout=60))))
    if actual != expected:
        raise ValueError("Loaded finance totals differ from the local source. Review before rerunning.")
    print(f"PASS: {actual['rows']:,} rows; debits ${actual['debits']/100:,.2f}; credits ${actual['credits']/100:,.2f}")
    print("Verified row count, schema, expiration, and GL totals. Other tables were not refreshed.")


def run(mode="preview"):
    payload, expected, digest = prepare_source()
    print(f"LOCAL PASS: {expected['rows']:,} rows; {len(payload):,} CSV bytes; SHA256 {digest}")
    print(f"Destination: {TARGET}; location: {LOCATION}; mode: {mode}")
    if mode == "preview":
        print("Preview only. Use --check for cloud metadata or --upload to replace this table's rows.")
        return
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    check_billing(credentials)
    with bigquery.Client(project=PROJECT, credentials=credentials, location=LOCATION) as client:
        original = check_destination(client)
        print(f"CLOUD CHECK PASS: billing disabled; existing GL has {original.num_rows:,} rows.")
        if mode == "upload":
            refresh(client, payload, expected, original)
        else:
            print("Check only: no tables changed and no SQL queries run.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true")
    group.add_argument("--upload", action="store_true")
    args = parser.parse_args()
    try:
        run("upload" if args.upload else "check" if args.check else "preview")
    except Exception as exc:
        # CLI boundary: report the error without credentials or an unreadable traceback.
        parser.exit(1, f"Stopped ({type(exc).__name__}): {exc}\nIf a job ID was printed, inspect that job before rerunning.\n")


if __name__ == "__main__":
    main()
