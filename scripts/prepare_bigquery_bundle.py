"""Create a small, allowlisted Cloud Shell upload ZIP from validated sources."""

import hashlib
import json
import zipfile
from pathlib import Path

from src.synthetic.schema import SCHEMAS
from src.synthetic.validate import INTEGER_FIELDS, read_tables, validate

ROOT = Path(__file__).resolve().parents[1]


def build_bundle():
    source = ROOT / "data/generated"
    cfg = json.loads((source / "manifest.json").read_text())["config"]
    report = validate(read_tables(source), cfg)
    nullable = {("salesforce/customers", "acquired_date"), ("workday/employees", "termination_date"), ("salesforce/customer_monthly", "contract_id")} | {("netsuite/gl_lines", name) for name in ("customer_id", "employee_id", "vendor_id")}
    payloads, tables = {}, []
    for name, columns in SCHEMAS.items():
        system, table = name.split("/")
        schema = []
        for col in columns:
            kind = "INTEGER" if col.endswith("_cents") or col in INTEGER_FIELDS else "DATE" if col.endswith("_date") or col in ("month", "start_month", "end_month") else "STRING"
            schema.append({"name": col, "type": kind, "mode": "NULLABLE" if (name, col) in nullable else "REQUIRED"})
        file, schema_path = "data/" + name + ".csv", "schemas/" + name + ".json"
        payloads[file] = (source / (name + ".csv")).read_bytes()
        payloads[schema_path] = (json.dumps(schema, indent=2) + "\n").encode()
        tables.append({"dataset": "raw_" + system, "table": table, "file": file,
                       "schema": schema_path, "rows": report["rows"][name],
                       "sha256": hashlib.sha256(payloads[file]).hexdigest(),
                       "schema_sha256": hashlib.sha256(payloads[schema_path]).hexdigest()})
    payloads["upload_manifest.json"] = (json.dumps({"synthetic_only": True, "tables": tables}, indent=2) + "\n").encode()
    payloads["cloud_shell_upload.py"] = (ROOT / "scripts/cloud_shell_upload.py").read_bytes()
    payloads["README.md"] = (ROOT / "docs/bigquery_bulk_upload.md").read_bytes()
    output = ROOT / "data/local/saas-finance-upload.zip"
    output.parent.mkdir(exist_ok=True, parents=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, content in payloads.items():
            archive.writestr("saas-finance-upload/" + path, content)
    print(f"Created {output}: {len(tables)} CSVs, {sum(i['rows'] for i in tables)} records, {output.stat().st_size:,} bytes.")
    return output


if __name__ == "__main__":
    build_bundle()
