# Milestone 5 — dbt transformations

## First lesson: one department view

Python moves and validates source data. dbt runs saved SQL transformations inside
BigQuery and tests their results. A **model** is a SQL SELECT saved in a file;
dbt turns this first model into a **view**, a reusable saved query.

```text
raw_shared.departments → staging.stg_departments → future financial reports
```

The first model trims surrounding spaces and renames `function` to
`department_function`. It retains one row per department. The original table
stays unchanged. More substantial financial calculations come after this lesson.

## What is already verified

On October 26, 2026, dbt Core 1.12.6 and dbt-bigquery 1.12.1 were installed into
the separate `.venv-dbt` environment. The build created the view in `us-south1`
and passed all five data tests:

- Department IDs are unique.
- Department IDs, names and functions are non-null (three tests).
- The model contains exactly the expected transformed source records.

The source metadata confirmed six rows. The build reported `PASS=6`: one view
creation plus five tests. Live metadata confirms the result is a VIEW with the
three expected columns and a 59-day expiration. Billing was confirmed disabled
with no linked account before creating the staging dataset or running dbt.

This completes the first component, not the whole dbt milestone. Other staging
models, P&L, budget comparisons, ARR/bookings and workforce reporting remain unbuilt.

## Your next action: query the view

In the BigQuery SQL editor, paste and run:

```sql
SELECT *
FROM `saas-finance-learning-512616.staging.stg_departments`
ORDER BY department_id;
```

Expect **six rows**, D01 through D06, with columns `department_id`,
`department_name`, and `department_function`.

Then open `dbt/models/staging/stg_departments.sql`. Compare its SELECT with
your query. The model defines how data is transformed; your query reads the result.

## Files to understand

| File | Role |
| --- | --- |
| `dbt/dbt_project.yml` | Project name and default view materialization |
| `dbt/models/staging/sources.yml` | Maps `source('shared', 'departments')` to the raw table |
| `dbt/models/staging/stg_departments.sql` | The transformation itself |
| `dbt/models/staging/schema.yml` | Column descriptions and four standard tests |
| `dbt/tests/departments_match_source.sql` | Reconciliation test; `ref()` identifies the model dependency |
| `config/dbt/profiles.example.yml` | Connection settings without credentials |
| `scripts/dbt_lesson.py` | Checks billing/settings, prepares staging if absent, runs this lesson |

A data test returns rows that violate a rule. **Zero failing rows means pass.**
`source()` names existing raw inputs; `ref()` names another dbt model and lets
dbt establish execution order. Later financial models will reuse these references.

## Rebuild this lesson when needed

From your Mac Terminal:

```bash
cd /Users/jackperry/Documents/Codex/saas-finance-data-platform
.venv-dbt/bin/python scripts/dbt_lesson.py
```

The helper builds only `stg_departments` and its tests. It stops if billing is
enabled or unknown, or if the local profile differs from this lesson's fixed
project, region, dataset and query limits. Each query has a 10 MiB maximum bytes
billed limit. Repeated runs still consume Sandbox allowances. No schedule exists.

The ignored local `config/dbt/profiles.yml` uses OAuth and your existing ADC login.
No service account key or dbt Cloud account is needed. dbt may print an optional
State authentication notice; the verified local build succeeds without it.
Generated dbt logs, compiled SQL, local profile and virtual environment are ignored
by Git. Source SQL, configuration template and documentation are tracked.

For a fresh checkout with Python 3.13 and Google ADC configured:

```bash
python3.13 -m venv .venv-dbt
.venv-dbt/bin/python -m pip install -r requirements-dbt.txt
.venv-dbt/bin/python scripts/dbt_lesson.py
```

The helper creates staging with both expiration defaults set to 59 days, if absent.
Raw tables must already be loaded. Expired raw inputs must be reloaded before
rebuilding dependent views. We use SQL views here, without incremental DML or seeds.

References: [dbt BigQuery connection settings](https://docs.getdbt.com/docs/local/connect-data-platform/bigquery-setup?version=1.12),
[dbt data tests](https://docs.getdbt.com/docs/build/data-tests?version=1.12).
