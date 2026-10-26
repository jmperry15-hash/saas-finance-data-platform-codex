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

This completed the first component. Lesson 2 below adds accounting staging and a
monthly operating P&L. Budget comparisons, detailed P&L classifications, ARR/bookings
and workforce reporting remain later components of this milestone.

## Lesson 1 practice: query the view

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

Without a lesson flag, the helper builds only `stg_departments` and its tests. It stops if billing is
enabled or unknown, or if the local profile differs from this lesson's fixed
project, region, dataset and query limits. Each query now has a 50 MiB maximum bytes
billed limit, increased from 10 MiB for lesson 2's multi-table joins. This is a
query ceiling, not a billing setting; billing stays disabled. Repeated runs still
consume Sandbox allowances. No schedule exists.

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

## Lesson 2: your first monthly P&L

Three new SQL models turn accounting entries into an operating summary:

```text
raw_netsuite.accounts → staging.stg_accounts ─┐
                                            ├→ finance.rpt_pnl_monthly
raw_netsuite.gl_lines → staging.stg_gl_lines ─┘
```

1. **Stage the inputs.** Accounts retain one row per account; the GL retains one
   row per journal line. All GL entries stay in staging, including balance sheet entries.
2. **Join by account ID.** The account type determines whether a line is revenue,
   expense, or a balance sheet movement. Unique account IDs and a relationship test
   prevent duplicate matches or silently dropping an unmapped GL account.
3. **Aggregate by month.** Revenue = credits minus debits; expenses = debits minus
   credits. Operating profit = revenue minus expenses. Balance sheet entries
   contribute zero, so capital contributions and customer cash receipts are not revenue.
4. **Reconcile.** Test journal balance, keys, nulls and monthly totals against the raw
   sources. Keep money in integer cents and convert to dollars only for presentation.

The report has one row per month with GL activity. It is a simplified operating
P&L, not a complete GAAP income statement. Total expenses include costs of revenue;
gross margin and functional expense breakdowns are not part of this first report.

### Your next action

Run this in the **BigQuery SQL editor**:

```sql
SELECT
  month,
  CAST(revenue_cents AS NUMERIC) / 100 AS revenue_usd,
  CAST(expense_cents AS NUMERIC) / 100 AS expense_usd,
  CAST(operating_profit_cents AS NUMERIC) / 100 AS operating_profit_usd
FROM `saas-finance-learning-512616.finance.rpt_pnl_monthly`
ORDER BY month;
```

Expect 24 rows, October 2024 through September 2026. October 2024 should show:

| Revenue | Total expenses | Operating profit / (loss) |
| ---: | ---: | ---: |
| $330,477.00 | $1,061,312.14 | -$730,835.14 |

Read `dbt/models/marts/rpt_pnl_monthly.sql` alongside the output. Find the two
`ref()` calls, the account-type `CASE` expressions, and `GROUP BY gl.month`.
Unlike manually pasting the entire transformation into the editor, querying this
view reuses the version-controlled definition in the repository.

### Rebuild lesson 2

```bash
cd /Users/jackperry/Documents/Codex/saas-finance-data-platform
.venv-dbt/bin/python scripts/dbt_lesson.py --lesson pnl
```

The `+rpt_pnl_monthly` selection tells dbt to build the report **and its upstream
models**, with their tests. The first live run passed 21 steps: three views and
18 data tests. The earlier department lesson's five tests are a separate selection.
An additional live SELECT matched all 24 monthly revenue, expense and profit values
to a separate Python calculation from the original CSV files, exactly in cents.
That verification processed 499,619 bytes. View metadata also confirmed the region
and 59-day expiration. Evidence is saved locally in the ignored
`data/local/pnl_reconciliation.json` file.

The helper creates `finance` with 59-day defaults if it is absent, checks existing
dataset settings, and retains the billing gate. All three new objects are views.
The `generate_schema_name` macro uses the explicit `finance` dataset instead of
dbt's usual `staging_finance` naming. This single-user learning setup has only one
target; separate developer/production targets would need isolated dataset names.

The profile template and this Mac's ignored profile were updated together to the
50 MiB limit. On another checkout with an old local profile, compare it with the
template and update that limit; the helper deliberately rejects a mismatched profile.

References: [dbt data test configuration](https://docs.getdbt.com/reference/resource-properties/data-tests),
[BigQuery model configuration](https://docs.getdbt.com/reference/resource-configs/bigquery-configs).
