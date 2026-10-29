"""Manual, fixed-project refresh. Default is local preview; --run performs loads.

Validated CSVs -> BigQuery raw -> dbt -> reconciled dashboard snapshot -> local build.
No source regeneration, paid services, schedule, or website publication.
"""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.database.load import load_database
from src.ingestion.refresh_sources import freeze_sources, preflight, refresh
from scripts.reconcile_dashboard import KEYS, compare_rows, normalize


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, default=normalize) + "\n")
    os.replace(temporary, path)


@contextmanager
def run_lock(path):
    with path.open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another manual refresh is running. Wait for it to finish.") from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def dashboard_candidate(template, expected, reconciliation):
    if reconciliation["status"] != "PASS" or not template.get("id"):
        raise ValueError("A passed reconciliation and existing dashboard identity are required.")
    candidate = json.loads(json.dumps(template))
    candidate.update(generatedAt=reconciliation["finished_at"], status="reviewed", buildStatus="complete")
    for name, keys in KEYS.items():
        result = reconciliation["datasets"][name]
        if result["status"] != "PASS":
            raise ValueError(f"Unverified dashboard query: {name}")
        compare_rows(expected["queries"][name]["rows"], result["cloud_rows"], keys)
        source = json.loads(json.dumps(expected["queries"][name]["source"]))
        source.update(type="bigquery", sql=result["sql"],
                      tables=re.findall(r"`(saas-finance-learning-512616\.[^`]+)`", result["sql"]),
                      executedAt=reconciliation["finished_at"],
                      caveats=["All company and person records are fictional. USD; money is stored in integer cents.",
                               "Snapshot exported from BigQuery after manual refresh; no live query or automatic refresh."],
                      evidenceFlow=[
                          {"title": "Validated inputs", "detail": "All fourteen raw tables matched the frozen CSV batch field-for-field."},
                          {"title": "dbt build and tests", "detail": "The complete dbt build succeeded before export."},
                          {"title": "Warehouse query", "detail": f"Job {result['job_id']}; every result field matched independent SQLite calculations."},
                      ])
        source.pop("files", None)
        candidate["queries"][name] = {"rows": result["cloud_rows"], "source": source}
    return candidate


def promote(candidate, snapshot_path, dist, backup, build):
    """Keep the previous source and compiled app if the local build fails."""
    original = snapshot_path.read_bytes()
    (backup / "previous-snapshot.json").write_bytes(original)
    had_dist = dist.exists()
    if had_dist:
        shutil.copytree(dist, backup / "previous-dist")
    try:
        write_json(snapshot_path, candidate)
        build()
    except BaseException:
        snapshot_path.write_bytes(original)
        if dist.exists():
            shutil.rmtree(dist)
        if had_dist:
            shutil.copytree(backup / "previous-dist", dist)
        raise


def run(source, node, builder):
    from google.cloud import bigquery
    from scripts.dbt_lesson import LOCATION, PROJECT, unbilled_credentials
    snapshot_path = ROOT / "dashboard-site/src/data.json"
    if not snapshot_path.is_file() or not json.loads(snapshot_path.read_text()).get("id"):
        raise ValueError("Initialize a local dashboard snapshot first; see docs/portfolio_validation.md. No cloud changes made.")
    local = ROOT / "data/local"
    local.mkdir(parents=True, exist_ok=True)
    with run_lock(local / "refresh.lock"):
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
        folder = local / "refresh-runs" / run_id
        folder.mkdir(parents=True)
        receipt = {"run_id": run_id, "status": "RUNNING", "stage": "validate", "tables": {},
                   "started_at": datetime.now(timezone.utc).isoformat(), "project": PROJECT,
                   "location": LOCATION, "published": False}
        save = lambda: write_json(folder / "receipt.json", receipt)
        save()

        def step(name, command):
            receipt["stage"] = name
            save()
            print(f"STEP {name}", flush=True)
            log = folder / f"{name}.log"
            with log.open("w") as handle:
                result = subprocess.run(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT, timeout=900)
            if result.returncode:
                print("\n".join(log.read_text().splitlines()[-15:]), flush=True)
                raise ValueError(f"{name} failed. See {log}")

        try:
            payloads, tables, report, manifest = freeze_sources(source, folder / "sources")
            receipt.update(source_checks=report["checks_passed"], source_files=manifest["files"],
                           source_config=manifest["config"])
            load_database(folder / "sources", folder / "finance.sqlite")
            step("local_expectations", [sys.executable, str(ROOT / "scripts/build_dashboard_snapshot.py"),
                 str(folder / "expected.json"), "--source", str(folder / "sources"),
                 "--database", str(folder / "finance.sqlite"), "--receipt", str(folder / "local-validation.json")])
            with sqlite3.connect(f"file:{folder / 'finance.sqlite'}?mode=ro", uri=True) as conn:
                conn.row_factory = sqlite3.Row
                pnl = [dict(row) for row in conn.execute("""SELECT month,
                    SUM(CASE WHEN account_id='4000' THEN credit_cents-debit_cents ELSE 0 END) revenue_cents,
                    SUM(CASE WHEN a.account_type='Expense' THEN debit_cents-credit_cents ELSE 0 END) expense_cents
                    FROM netsuite_gl_lines g JOIN netsuite_accounts a USING(account_id) GROUP BY month ORDER BY month""")]
            for row in pnl:
                row["operating_profit_cents"] = row["revenue_cents"] - row["expense_cents"]
            write_json(folder / "pnl_expected.json", pnl)
            step("local_dashboard_tests", [node, "tests/test_dashboard_model.mjs", str(folder / "expected.json"), str(folder / "pnl_expected.json")])
            credentials = unbilled_credentials()
            receipt.update(stage="raw_refresh", billing_disabled=True)
            save()
            with bigquery.Client(project=PROJECT, credentials=credentials, location=LOCATION) as client:
                originals = preflight(client)
                refresh(client, payloads, tables, originals, receipt, save)
            step("dbt", [sys.executable, "scripts/dbt_lesson.py", "--lesson", "all"])
            results = json.loads((ROOT / "dbt/target/run_results.json").read_text())
            if not results["results"] or any(r["status"] not in ("pass", "success") for r in results["results"]):
                raise ValueError("dbt did not pass every model and test.")
            receipt["dbt_successful_steps"] = len(results["results"])
            write_json(folder / "dbt-results.json", results)
            step("reconcile", [sys.executable, "scripts/reconcile_dashboard.py", "--check-cloud",
                 "--snapshot", str(folder / "expected.json"), "--receipt", str(folder / "reconciliation.json")])
            reconciliation = json.loads((folder / "reconciliation.json").read_text())
            expected = json.loads((folder / "expected.json").read_text())
            candidate = dashboard_candidate(json.loads(snapshot_path.read_text()), expected, reconciliation)
            write_json(folder / "candidate.json", candidate)
            step("dashboard_tests", [node, "tests/test_dashboard_model.mjs", str(folder / "candidate.json"), str(folder / "pnl_expected.json")])
            promote(candidate, snapshot_path, ROOT / "dashboard-site/dist", folder,
                    lambda: step("dashboard_build", [node, builder, "build", "--project-dir", str(ROOT / "dashboard-site"), "--separate-data"]))
            receipt.update(status="PASS", stage="complete", dashboard_rows=sum(len(q["rows"]) for q in candidate["queries"].values()),
                           snapshot_sha256=hashlib.sha256(snapshot_path.read_bytes()).hexdigest())
        except BaseException as error:
            receipt.update(status="FAIL", error=str(error))
            raise
        finally:
            receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
            save()
            print(f"Receipt: {folder / 'receipt.json'}", flush=True)
        print("PASS: fourteen sources refreshed; dbt passed; warehouse dashboard snapshot built locally.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--source", type=Path, default=ROOT / "data/generated")
    parser.add_argument("--node", default=str(Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"))
    parser.add_argument("--data-app-cli", type=Path)
    args = parser.parse_args()
    if not args.run:
        with tempfile.TemporaryDirectory() as temporary:
            _, _, report, _ = freeze_sources(args.source, Path(temporary) / "sources")
        print(f"PREVIEW PASS: {report['checks_passed']} controls; 14 tables; {sum(report['rows'].values()):,} rows.")
        print("Add --run to replace the fixed project's raw tables, build/test dbt, and update the local dashboard. No publication.")
        return
    builder = args.data_app_cli
    if builder is None:
        candidates = list((Path.home() / ".codex/plugins/cache/openai-curated-remote/data-analytics").glob("*/scripts/data-app.mjs"))
        if len(candidates) != 1:
            raise ValueError("Specify --data-app-cli for the installed Data plugin's scripts/data-app.mjs.")
        builder = candidates[0]
    if not Path(args.node).is_file() or not builder.is_file():
        raise ValueError("Local dashboard tools missing; specify --node and --data-app-cli before refreshing.")
    run(args.source, args.node, str(builder))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(f"Stopped: {error}. Review the saved job IDs before rerunning after a cloud timeout.") from error
