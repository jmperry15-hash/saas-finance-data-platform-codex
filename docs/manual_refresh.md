# Milestone 6, lesson 2: one manual refresh

The refresh joins the tools you have learned into a single ordered pipeline:

**Synthetic CSVs → Python validation/load → BigQuery → dbt → verified dashboard export → local preview.**

It uses the current 24-month synthetic scenario. Running it again does not
invent new months or change the source files. It reloads the saved inputs and
recomputes their reporting outputs.

**Verified October 28, 2026:** run `20261029T002826Z_7974e978` passed in about
three minutes. All 14 tables / 23,794 source rows matched field-for-field, all
122 dbt steps passed, all 4,047 dashboard rows reconciled, and the dashboard
model passed 186 comparisons plus coverage/plan assertions. The Python suite
passed 73 tests. Browser review confirmed all three tabs render and source
inspection shows BigQuery SQL and the new extraction time. Billing was disabled.
Missing-table recovery, timeout handling and failed-build rollback were tested
offline with mocks/temporary files, not by deleting live cloud data. This was
one complete live run; a second full live rerun has not been exercised yet.

## Run it

In your Mac terminal, from the project folder:

```bash
cd /Users/jackperry/Documents/Codex/saas-finance-data-platform
.venv-dbt/bin/python scripts/refresh_project.py
```

This preview validates all inputs locally. It makes no cloud calls or dashboard
changes. To perform the complete refresh:

```bash
.venv-dbt/bin/python scripts/refresh_project.py --run
```

After `PASS`, reload [the local dashboard](http://127.0.0.1:60033/). Its Updated
date reflects extraction time; its reporting periods still end in September
2026. Source inspection now shows the executed BigQuery SQL. The private hosted
website updates only through a separate publication step.

## What happens, and why

| Step | Tool and purpose |
| --- | --- |
| Freeze and validate | Python checks file hashes, sizes, schemas and financial relationships, then works from a frozen copy. Changing an input mid-run cannot change the uploaded bytes. |
| Calculate expectations | SQLite independently calculates expected reporting rows from those same inputs. This gives us a reference for the warehouse calculations. |
| Preflight | Python checks billing is disabled and inspects every raw dataset/table before the first load. Regions, schemas and expiration settings must match. |
| Load all 14 sources | BigQuery CSV load jobs replace rows using `WRITE_TRUNCATE`. Repeating a run replaces the same data rather than appending duplicates. |
| Verify raw contents | Bounded SQL queries read all 23,794 raw rows and compare every field to the frozen sources. A matching row count alone is insufficient. |
| Build reporting | dbt builds the 14 views in dependency order and runs all 104 data tests and four unit tests. |
| Export and reconcile | Four BigQuery queries return 4,047 dashboard rows. Every field must match the independent SQLite calculations. |
| Validate and build dashboard | JavaScript checks the dashboard calculations; the tested warehouse snapshot replaces the local data file and the Data plugin rebuilds the app. |

The dashboard keeps its identity, title, filters, styling and metric definitions.
Only its reviewed data and source provenance are refreshed. ARR, headcount and
FTE remain ending balances, while revenue, bookings and personnel costs sum over
the selected period. BUD2025 remains the selected budget.

## Logs and recovery

Each run creates an ignored local folder under `data/local/refresh-runs/` with:

- `receipt.json`: stage, success/failure, source hashes and load/verification job IDs.
- `sources/`: the exact synthetic inputs used, plus a manifest.
- `dbt.log` and `dbt-results.json`: warehouse model/test results.
- `reconciliation.json`: executed reporting SQL, query results and comparisons.
- `previous-snapshot.json` and `previous-dist/`: the dashboard version before a successful promotion attempt.

The helper prevents two copies of itself running together. Do not use separate
upload commands or edit dashboard content during a refresh; the lock does not
control other tools.

**Failure behavior:** it stops immediately and does not promote an unverified
dashboard. If the local app build fails, the previous snapshot and compiled app
are restored. A partial raw-table load is **not** rolled back across BigQuery:
load jobs are atomic per table, not across all fourteen. The receipt identifies
which loads completed. Finish recovery before querying raw tables for reporting.

For a timeout, inspect the recorded BigQuery job before starting another run;
the helper does not automatically submit a replacement load job. Once the prior
jobs have settled and the problem is corrected, rerun the same command.

Missing/expired **tables** are recreated with explicit schemas and the existing
dataset's expiration defaults. Existing table expirations are preserved, not
extended. Missing datasets, wrong regions, or unexpected schemas stop the run
for review; the command does not delete datasets or enable billing.

## Scope and limits

- All sources are synthetic; API-to-warehouse extraction remains a separate optional exercise.
- Credentials use your local Google login and remain outside the repository.
- CSV input is capped at 25 MiB. Each verification/report query is capped at
  50 MiB; dbt retains its existing 50 MiB per-query cap. Sandbox quotas still apply.
- No schedule, remote authentication, paid service, or public publication is added.
- Browser inspection is a human/agent checkpoint after the command; a successful
  build alone does not prove charts render.
- The command uses the installed Data plugin and bundled Node runtime. If they
  move, specify `--node /absolute/path/to/node` and
  `--data-app-cli /absolute/path/to/data-app.mjs` rather than installing extra tools.
- This is a small learning pipeline with sequential full-table replacements,
  not a production transaction across the warehouse.

Read `scripts/refresh_project.py` for orchestration and
`src/ingestion/refresh_sources.py` for loading. The SQL business logic remains
in `dbt/models/`; `sql/dashboard/` selects the reporting data for export.
