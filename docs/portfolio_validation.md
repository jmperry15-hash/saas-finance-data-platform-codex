# Lesson 3: reproduce the project from GitHub

A successful local run can depend on files that were never committed. This
lesson makes a fresh copy regenerate the synthetic data and check the Python
pipeline and dashboard calculations. No Google login or warehouse access is
needed for these checks.

## What the workflow does

1. Checks out this commit on a fresh Ubuntu runner and installs Python dependencies.
2. Generates all 14 source tables and checks 764 validation controls.
3. Runs the Python suite, with cloud calls mocked.
4. Builds a temporary SQLite database and the four dashboard datasets.
5. Runs the JavaScript finance model against independent GL totals: 186 numeric
   comparisons plus coverage/plan assertions, and verifies snapshot identity is
   preserved when rebuilding.

This checks reproducibility and calculation logic. It does not refresh BigQuery,
run live dbt tests, inspect rendered charts, or publish the private dashboard.
The workflow remains manual; no Google credentials, caches or artifacts are uploaded.

## Try it from a fresh clone

Use Python 3.13 and Node.js 22 or newer. From a new clone:

```sh
python3.13 -m venv .venv-ingestion
source .venv-ingestion/bin/activate
python -m pip install -r requirements-ingestion.txt
python -m pip check
python -m src.synthetic.generate
python -m src.synthetic.validate
python -m unittest discover -s tests -v
python scripts/check_dashboard_offline.py
```

The final command uses temporary files and does not overwrite an existing
source directory, SQLite database or dashboard snapshot. The generator refuses
to overwrite an existing nonempty output directory.

## Optional: initialize the UI on a new clone

The public repository includes dashboard source code, but excludes generated
snapshots, builds, private Site settings, and credentials. Checking calculations
above requires neither the Data plugin nor a browser.

To initialize a new local dashboard, first load the local SQLite database
(only when it does not already exist), then generate a snapshot:

```sh
python -m src.database.load
python scripts/build_dashboard_snapshot.py dashboard-site/src/data.json
```

A new snapshot receives a new artifact ID; later rebuilds preserve that ID.
Its source inspector correctly labels these rows as local SQLite results.
Review the snapshot, mark `buildStatus` complete, and use the installed Data
plugin's supported build/preview commands in `dashboard-site/AGENTS.md`.
That plugin is required for the supported UI build/preview workflow. Do not
reuse another person's private hosting configuration. The complete cloud
refresh also requires the separate dbt environment, authenticated access to
the configured BigQuery project and the local Data plugin; see
[manual refresh](manual_refresh.md).

## Your GitHub exercise

Open **Actions → Validate synthetic finance data → Run workflow → main**.
Inspect the newest run's commit before interpreting its result. Expand
**Rebuild and verify dashboard calculations (no cloud calls)** and find the
186-comparison PASS line. A green older run does not validate newer code.

## Verification at this checkpoint

On October 28, a clean copy of the staged public files passed 764 source
controls, all 73 Python tests, 186 dashboard comparisons, identity preservation
and the local refresh preview. Credential paths pointed to nonexistent files.
The check reused the installed Python environment, whose dependency check
passed. [GitHub then passed the expanded workflow](https://github.com/jmperry15-hash/saas-finance-data-platform-codex/actions/runs/40796000119)
on application commit `614edb6`, verifying fresh installation and execution on
Ubuntu. Logs confirm 73 Python tests and 186 dashboard comparisons passed.
The staged files passed a common-secret-pattern and private-path scan.
