"""Upload the bundled synthetic sources using Cloud Shell's gcloud and bq tools.

No third-party Python packages or downloaded credential files are required.
Run without --upload for a local-only preview. No billing or API enabling occurs.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def command(args, as_json=False):
    result = subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE)
    return json.loads(result.stdout) if as_json else result.stdout


def check_billing(project):
    info = command(["gcloud", "billing", "projects", "describe", project,
                    "--format=json", "--quiet"], as_json=True)
    if info.get("billingEnabled") is not False or info.get("billingAccountName"):
        raise ValueError("Stop: project must have billing disabled and no linked billing account.")


def validate_bundle(root):
    manifest = json.loads((root / "upload_manifest.json").read_text())
    for item in manifest["tables"]:
        for field, hash_field in [("file", "sha256"), ("schema", "schema_sha256")]:
            path = (root / item[field]).resolve()
            if root.resolve() not in path.parents:
                raise ValueError("Invalid bundle path")
            if hashlib.sha256(path.read_bytes()).hexdigest() != item[hash_field]:
                raise ValueError("Bundle file changed: " + item[field])
    return manifest


def schema_matches(actual, expected):
    def normalized(fields):
        return [(f["name"], {"INT64": "INTEGER"}.get(f["type"], f["type"]),
                 f.get("mode", "NULLABLE")) for f in fields]
    return normalized(actual) == normalized(expected)


def upload(project, root=ROOT):
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", project):
        raise ValueError("Use your Google Cloud project ID, not its display name.")
    manifest = validate_bundle(root)
    for executable in ("gcloud", "bq"):
        if not shutil.which(executable):
            raise ValueError("Run this script inside Google Cloud Shell; missing " + executable)
    check_billing(project)  # Failure or uncertain status stops all cloud writes.
    bq = ["bq", "--project_id=" + project, "--location=US", "--format=prettyjson"]
    datasets = command(bq + ["ls", "--max_results=10000", project + ":"], as_json=True)
    dataset_ids = {d["datasetReference"]["datasetId"] for d in (datasets or [])}
    desired = sorted({i["dataset"] for i in manifest["tables"]})
    existing = {}
    # Inspect every existing target before creating datasets or uploading files.
    for dataset in desired:
        if dataset not in dataset_ids:
            continue
        info = command(bq + ["show", project + ":" + dataset], as_json=True)
        if info.get("location", "").upper() != "US":
            raise ValueError(dataset + " is not in US. Stop and review locations before uploading.")
        tables = command(bq + ["ls", "--max_results=10000", project + ":" + dataset], as_json=True)
        for entry in tables or []:
            existing[dataset, entry["tableReference"]["tableId"]] = True
    skipped = set()
    for item in manifest["tables"]:
        key = (item["dataset"], item["table"])
        if key not in existing:
            continue
        target = project + ":" + ".".join(key)
        info = command(bq + ["show", target], as_json=True)
        schema = json.loads((root / item["schema"]).read_text())
        if info.get("type") != "TABLE" or not schema_matches(info.get("schema", {}).get("fields", []), schema) or int(info.get("numRows", -1)) != item["rows"]:
            raise ValueError(target + " already exists with a different schema or row count. No tables were changed. Review it before retrying.")
        skipped.add(key)
    for dataset in desired:
        if dataset not in dataset_ids:
            command(bq + ["mk", "--dataset", "--default_table_expiration=5184000", project + ":" + dataset])
    for item in manifest["tables"]:
        key = (item["dataset"], item["table"])
        target = project + ":" + ".".join(key)
        if key in skipped:
            print("SKIP existing (schema and count match): " + target, flush=True)
            continue
        print("LOAD " + target, flush=True)
        # Each destination was absent in preflight. Run only one uploader at a time.
        # No automatic retry: a failed job stops here, rather than risking duplicates.
        command(bq + ["load", "--source_format=CSV", "--skip_leading_rows=1",
                      "--max_bad_records=0", target, str(root / item["file"]),
                      str(root / item["schema"])])
        info = command(bq + ["show", target], as_json=True)
        if int(info.get("numRows", -1)) != item["rows"]:
            raise ValueError("Loaded row count mismatch: " + target)
        print("OK " + str(item["rows"]) + " rows", flush=True)
    print("Finished: all 14 tables have matching schemas/row counts. Finance SQL reconciliation is the next step.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--upload", action="store_true", help="Check billing and run cloud uploads")
    args = parser.parse_args()
    try:
        manifest = validate_bundle(ROOT)
        if not args.upload:
            for item in manifest["tables"]:
                print(f"{args.project}.{item['dataset']}.{item['table']}: {item['rows']} rows")
            print("Preview only. Add --upload to check billing and upload in Cloud Shell.")
            return
        upload(args.project)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Stopped: {exc}\nDo not enable billing or APIs to bypass an error; share the error text for review.\n")


if __name__ == "__main__":
    main()
