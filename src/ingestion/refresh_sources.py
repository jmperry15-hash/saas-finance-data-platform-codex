"""Small all-source refresh: freeze inputs, preflight all targets, replace, verify.

BigQuery loads are atomic per table, not across the fourteen-table batch.
Only the orchestrator promotes dashboard data after the entire run passes.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import uuid

from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from scripts.prepare_bigquery_bundle import source_schema
from scripts.reconcile_dashboard import compare_rows
from src.ingestion.load_gl import LOCATION, MAX_BYTES, PROJECT, schema_signature
from src.synthetic.schema import KEYS, SCHEMAS
from src.synthetic.validate import read_tables, validate

QUERY_LIMIT = 50 * 1024 * 1024


def target(name):
    system, table = name.split("/")
    return f"{PROJECT}.raw_{system}.{table}"


def schema(name):
    return [bigquery.SchemaField.from_api_repr(field) for field in source_schema(name)]


def freeze_sources(source, destination):
    """Bound reads and verify hashes, then validate the exact copied batch."""
    source, destination = Path(source), Path(destination)
    manifest_bytes = (source / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("synthetic_only") is not True or set(manifest["files"]) != set(SCHEMAS):
        raise ValueError("Expected the fourteen-table synthetic manifest.")
    payloads, total = {}, 0
    for name in SCHEMAS:
        with (source / f"{name}.csv").open("rb") as handle:
            payload = handle.read(MAX_BYTES + 1)
        total += len(payload)
        if total > MAX_BYTES:
            raise ValueError("Source batch exceeds 25 MiB.")
        if hashlib.sha256(payload).hexdigest() != manifest["files"][name]["sha256"]:
            raise ValueError(f"Source hash mismatch: {name}")
        payloads[name] = payload
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "manifest.json").write_bytes(manifest_bytes)
    for name, payload in payloads.items():
        path = destination / f"{name}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    tables = read_tables(destination)
    report = validate(tables, manifest["config"])
    if any(report["rows"][name] != manifest["files"][name]["rows"] for name in SCHEMAS):
        raise ValueError("Manifest row counts differ from validated files.")
    return payloads, tables, report, manifest


def check_table(table, name):
    if table.location != LOCATION or table.table_type != "TABLE":
        raise ValueError(f"Wrong location or object type: {target(name)}")
    if any((table.time_partitioning, table.range_partitioning,
            table.table_constraints, table.clustering_fields)):
        raise ValueError(f"Unexpected partitioning/constraints/clustering: {target(name)}")
    if schema_signature(table.schema) != schema_signature(schema(name)):
        raise ValueError(f"Schema mismatch: {target(name)}")
    now = datetime.now(timezone.utc)
    if table.expires is None or not now < table.expires <= now + timedelta(days=60):
        raise ValueError(f"Expected future expiration within 60 days: {target(name)}")


def preflight(client):
    """Inspect every destination before the first write. Missing tables may recover."""
    for system in sorted({name.split('/')[0] for name in SCHEMAS}):
        dataset = client.get_dataset(f"{PROJECT}.raw_{system}", timeout=30)
        if dataset.location != LOCATION or any(
            expiry is None or not 0 < expiry < 60 * 86400000
            for expiry in (dataset.default_table_expiration_ms, dataset.default_partition_expiration_ms)
        ):
            raise ValueError(f"Review raw_{system} location/expiration before refreshing.")
    originals = {}
    for name in SCHEMAS:
        try:
            table = client.get_table(target(name), timeout=30)
        except NotFound:
            originals[name] = None
        else:
            check_table(table, name)
            originals[name] = table
    return originals


def refresh(client, payloads, tables, originals, receipt, save):
    for name in SCHEMAS:
        original = originals[name]
        job_id = "finance_batch_" + uuid.uuid4().hex
        entry = {"target": target(name), "load_job_id": job_id, "status": "SUBMITTING",
                 "rows": len(tables[name]), "sha256": hashlib.sha256(payloads[name]).hexdigest(),
                 "recreating_missing_table": original is None}
        receipt["tables"][name] = entry
        save()
        config = bigquery.LoadJobConfig(
            source_format="CSV", schema=schema(name), skip_leading_rows=1,
            max_bad_records=0, autodetect=False, ignore_unknown_values=False,
            create_disposition="CREATE_IF_NEEDED" if original is None else "CREATE_NEVER",
            write_disposition="WRITE_TRUNCATE",
        )
        print(f"LOAD {target(name)} ({len(tables[name]):,} rows); job {job_id}", flush=True)
        job = client.load_table_from_file(
            io.BytesIO(payloads[name]), target(name), size=len(payloads[name]),
            job_config=config, job_id=job_id, location=LOCATION, num_retries=0, timeout=60,
        )
        job.result(timeout=120)
        table = client.get_table(target(name), timeout=30)
        check_table(table, name)
        if table.num_rows != len(tables[name]) or (original and table.expires != original.expires):
            raise ValueError(f"Post-load count/expiration mismatch: {target(name)}")
        sql = f"SELECT * FROM `{target(name)}`"
        dry = client.query(sql, timeout=30, job_config=bigquery.QueryJobConfig(
            dry_run=True, use_query_cache=False, maximum_bytes_billed=QUERY_LIMIT))
        if dry.total_bytes_processed is None or dry.total_bytes_processed > QUERY_LIMIT:
            raise ValueError(f"Raw verification exceeds 50 MiB: {name}")
        query = client.query(sql, timeout=30, job_retry=None,
                             job_config=bigquery.QueryJobConfig(maximum_bytes_billed=QUERY_LIMIT))
        entry.update(verification_job_id=query.job_id, verification_sql=sql)
        save()
        cloud = [dict(row) for row in query.result(timeout=120)]
        expected = [{key: None if value == "" else value for key, value in row.items()}
                    for row in tables[name]]
        compare_rows(expected, cloud, KEYS[name])
        entry.update(status="PASS", expires=table.expires.isoformat(),
                     processed_bytes=query.total_bytes_processed)
        save()
        print(f"PASS {name}: every uploaded field matches the frozen input.", flush=True)
