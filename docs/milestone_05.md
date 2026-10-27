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

This completed the first component. Lesson 2 adds accounting staging and a monthly
operating P&L; lesson 3 adds the BUD2025 comparison; lesson 4 adds ARR and active
customer snapshots; lesson 5 adds bookings; lesson 6 adds workforce reporting.
Detailed P&L classifications, retention/movement analysis and headcount-plan
comparisons remain later components of this milestone.

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

## Lesson 3: compare 2025 actuals with budget

The user's version query confirmed that **BUD2025** is a Budget covering January
through December 2025. FC2025H2 is a separate July–December forecast. This lesson
deliberately fixes BUD2025 in the model; selecting a different version is future work.

### What we built and where

The SQL lives locally in `dbt/models/`. dbt sends that SQL to BigQuery, where the
views run. Local Git tracks the changes; there is still no GitHub remote.

| Model | Purpose |
| --- | --- |
| `staging.stg_plan_versions` | Preserve the version list and covered dates |
| `staging.stg_financial_plan` | Preserve budget/forecast amounts and version IDs |
| `finance.fct_pnl_monthly` | Aggregate GL actuals to month × department × account |
| `finance.fct_budget_vs_actual` | Compare the two sides at that same grain for BUD2025 |

`rpt_pnl_monthly` from lesson 2 is the company-wide monthly summary. The new
`fct_pnl_monthly` retains account and department detail needed for the budget join.

### Read the main SQL model

Open `dbt/models/marts/fct_budget_vs_actual.sql` and follow its named sections:

1. `selected_version` chooses BUD2025 and its date range.
2. `actual` limits the aggregated GL to those dates.
3. `budget` selects only that budget's records.
4. `combined` uses a **FULL OUTER JOIN** on month, department and account. It keeps
   rows found on only one side. `COALESCE` supplies zero for the missing amount,
   while `coverage` records whether the row is Both, Actual only or Budget only.
5. The final SELECT calculates the variances and adds account descriptions.

Aggregating actuals before joining avoids repeating a monthly budget against every
individual journal line. Both input keys are controlled through tests.

| Measure | Definition |
| --- | --- |
| `variance_cents` | Actual minus budget, for both revenue and expense |
| `variance_ratio` | Variance / budget; NULL when budget is zero |
| `favorable_variance_cents` | Revenue: actual minus budget. Expense: budget minus actual |

A positive favorable variance means favorable; negative means unfavorable. The
ratio is not additive: when summarizing rows, divide summed variance by summed
budget rather than summing or averaging the row ratios. Do not combine revenue
and expenses as though their dollar variances have the same favorable sign.

### Your next action

Paste the query from `sql/bigquery/03_budget_vs_actual.sql` into BigQuery. It returns
24 summary rows: 12 months × Revenue/Expense. January 2025 should show:

| Type | Actual | Budget | Actual minus budget | Favorable variance |
| --- | ---: | ---: | ---: | ---: |
| Revenue | $396,952.35 | $262,500.00 | $134,452.35 | $134,452.35 |
| Expense | $1,142,351.17 | $1,040,500.00 | $101,851.17 | -$101,851.17 |

Explain why both dollar variances are positive, but only one is favorable. Then
inspect one department/account row to connect a detailed variance with the summary.

### Rebuild and test

```bash
cd /Users/jackperry/Documents/Codex/saas-finance-data-platform
.venv-dbt/bin/python scripts/dbt_lesson.py --lesson budget
```

The helper keeps the existing billing, region, expiration and 50 MiB per-query
controls. It selects `+fct_budget_vs_actual`, including upstream models. Cautious
test selection includes tests only when all their inputs belong to this build,
so this lesson does not depend on the earlier report already existing.

Data tests check real keys, plan scope and raw-to-report amounts. A dbt **unit test**
uses small invented examples to check actual-only rows, budget-only rows, zero
budgets, date boundaries, forecast exclusion and favorable/unfavorable signs.
These examples are test inputs, not extra records uploaded into the raw tables.
The current generated 2025 data has 300 comparison rows, all with Both coverage;
the unit test exercises missing-side cases that these data do not contain.

The final live build passed **44 steps: six views, 37 data tests and one unit test**.
The six views include two existing accounting dependencies and four new models.
An initial validation-query syntax error was corrected before the successful build;
dbt blocked the dependent comparison until the check passed.
An independent Python aggregation of the original CSVs matched all 300 live rows,
including coverage, favorable variance and rounded variance ratios. The summary
query also returned the expected 24 rows. All four new views were verified in
`us-south1` with 59-day expiration. Local evidence is saved in the ignored
`data/local/budget_reconciliation.json` file.

Reference: [dbt unit tests](https://docs.getdbt.com/docs/build/unit-tests).

## Lesson 4: ARR and active customers

The user completed the budget comparison lesson. We now use the synthetic
Salesforce snapshots to report MRR, ARR and active customers for each month.

### What we built

```text
raw_salesforce.customer_monthly
    → staging.stg_customer_monthly
    → finance.rpt_arr_monthly
```

The first view keeps one row per customer per month, including zero balances.
The second summarizes those rows into one company-wide monthly snapshot.
Both definitions are local SQL files run by dbt; both views live in BigQuery.

Read `dbt/models/marts/rpt_arr_monthly.sql` in this order:

1. `GROUP BY month` adds customer MRR and ARR **within each month**.
2. `COUNTIF(mrr_cents > 0)` counts active customers. A record in the customer
   master is not necessarily a paying customer; the master also includes prospects.
3. `LAG(arr_cents) OVER (ORDER BY month)` looks at the previous month's ARR.
   This is a **window function**: it compares rows without collapsing the report
   into a single total. It runs after the customer data is aggregated to one row per month.
4. Subtract previous ARR to get the change; divide by previous ARR for growth.
   The first row has no observed previous month, so change/growth are NULL.
   A zero prior ARR also produces NULL growth instead of a divide-by-zero error.

The `month` date labels the period using its first day. These are monthly snapshot
balances, not transaction amounts. For this generator, contract changes occur on
month boundaries, so balances are constant within each month.

**ARR and active customer counts are not additive across months.** To report
year-end ARR, select December's balance. Do not sum twelve monthly ARR values.
Monthly revenue in the P&L, by contrast, can be summed to annual revenue.

### Your next action

Copy `sql/bigquery/04_arr_trend.sql` into the BigQuery SQL editor and run it.
Expect 24 rows, October 2024 through September 2026, with these endpoints:

| Month | Active customers | MRR | ARR | ARR growth |
| --- | ---: | ---: | ---: | ---: |
| October 2024 | 55 | $330,477.00 | $3,965,724.00 | NULL |
| September 2026 | 100 | $631,037.80 | $7,572,453.60 | -1.92% |

Find `LAG` in the model and explain why the first month's change is blank. Then
check that one month's ARR equals MRR × 12. This distinguishes the annualized
recurring balance from that month's recognized revenue.

### Rebuild and test

```bash
cd /Users/jackperry/Documents/Codex/saas-finance-data-platform
.venv-dbt/bin/python scripts/dbt_lesson.py --lesson arr
```

The live build passed **16 steps: two views, 13 data tests and one unit test**.
Controls check unique customer/month keys, required values, nonnegative MRR/ARR,
ARR = MRR × 12, master-customer references and a complete monthly grid. Grid
completeness matters because otherwise LAG could compare January with March
as if they were consecutive months. The source master is explicitly included
in this lesson's test selection, without creating another model for it.

The unit test covers inactive customers, the first-month NULLs, a fall to zero
ARR and recovery from zero. A separate Python calculation from local **contract
start/end dates and amounts** checks all 24 reported months independently of the
snapshot aggregation. Money remains integer cents until display.
That independent comparison passed for all 24 months, including customer counts
and growth. MRR also matched the monthly GL revenue in every period. This equality
is specific to our synthetic, purely recurring subscription scenario; it should
not be assumed for a company with services, usage charges or different revenue rules.
Both views were verified in `us-south1` with 59-day expiration. Local evidence is
in the ignored `data/local/arr_reconciliation.json` file. Billing remains disabled
and the existing 50 MiB per-query limit is unchanged.

The ARR model does not itself report bookings, an ARR movement bridge, GRR or NRR.
Lesson 5 handles booking events separately. Net ARR growth alone does not explain
new business versus expansion or churn; retention needs customer-cohort rules.

## Lesson 5: bookings versus revenue and ARR

The user completed the ARR report. We now summarize signed contract bookings by
month and compare them with revenue and ARR from the earlier lessons.

### Why the measures differ

For a $12,000 annual subscription signed and starting in January in this scenario:

| Measure | January amount | Meaning |
| --- | ---: | --- |
| Bookings | $12,000 | Full signed contract value recorded when the deal closes |
| Recognized revenue | $1,000 | One month's service delivered |
| ARR | $12,000 | Annualized recurring subscription balance |

A flat renewal can create $12,000 of renewal bookings with **zero increase in ARR**.
Total bookings therefore includes new business and renewals separately. It is not
net new ARR. Monthly bookings and revenue are flows and can be summed across months;
ARR is a balance and cannot. These definitions are specific to this project's
12-month, fixed-price contracts with signing and service starting in the same month.

### What dbt built

- `staging.stg_bookings`: one row per signed contract booking.
- `finance.rpt_bookings_monthly`: monthly event counts and booked value, split
  into New business and Renewal, with total bookings.

The model reuses `staging.stg_customer_monthly` for the reporting months. In
`dbt/models/marts/rpt_bookings_monthly.sql`, read the steps:

1. `months` selects each reporting month once, even though there are many customers.
2. `bookings` groups events by month and calculates new/renewal subtotals.
3. A `LEFT JOIN` from the months list keeps months without bookings. `COALESCE`
   fills those missing values with zero. This prevents blank months disappearing
   from a trend chart and prevents customer rows multiplying booking values.

`booking_count` counts contract events, not active customers. Bookings before the
reporting window are excluded even if their contracts still generate revenue.

### Your next action

Open **`sql/bigquery/05_bookings_revenue_arr.sql`**, copy its SQL into BigQuery and
run it. The query joins three reports that each have one row per month, so their
join does not multiply amounts. It requires the P&L and ARR lessons to be built.
Expect 24 rows with new bookings, renewal bookings, total bookings, revenue and ARR.

For January 2025, expect six bookings: one new contract and five renewals.

| New bookings | Renewal bookings | Total bookings |
| ---: | ---: | ---: |
| $125,520.00 | $355,206.00 | $480,726.00 |

Compare this with January's $396,952.35 recognized revenue. The amounts differ
because bookings capture whole contracts signed that month; revenue includes
monthly service from both newly signed and earlier active contracts.

### Rebuild and validation

```bash
cd /Users/jackperry/Documents/Codex/saas-finance-data-platform
.venv-dbt/bin/python scripts/dbt_lesson.py --lesson bookings
```

The live build passed **34 steps: three views, 30 data tests and one unit test**.
The views include the existing customer-month dependency and the two new models.
Tests check unique booking/contract IDs, allowed types, customer references and
the full in-window contract population. Each booking must match its contract and
Closed Won opportunity in customer, amount, date and new/renewal classification.

The unit test includes a month with no bookings and multiple customer rows for
one calendar month. It verifies zeros are retained, amounts are not multiplied,
and a renewal contributes its full contract value to the renewal subtotal.
The existing billing, region, expiration and 50 MiB query limits remain in place.

An independent Python calculation from local contracts/opportunities matched all
24 months, 183 events and the new/renewal splits. Total bookings across the window
are $13,760,862.00. The comparison query returned 24 rows with complete revenue/ARR
matches. Both new views were verified in `us-south1` with 59-day expiration.
Local evidence is saved in the ignored `data/local/bookings_reconciliation.json`.

## Lesson 6: headcount, FTE and personnel costs

We now connect the synthetic Workday data to the financial reports. The new views
are `staging.stg_employee_monthly` (one employee per month) and
`finance.rpt_workforce_monthly` (one department per month).

### Definitions first

| Measure | Definition in this project |
| --- | --- |
| Headcount | Number of employees represented on that month's payroll |
| FTE | Sum of capacity: full time = 1.0; an 80% employee = 0.8 |
| Personnel cost | Base pay + bonus + employer benefits/payroll taxes |

Hires start on the first of a month, and termination dates are the last paid day
at month end. The termination month is included; the following month is excluded.
We do not model mid-month proration or daily headcount movements. A real company's
headcount reporting policy must specify its exact effective-date convention.

FTE is stored in **basis points**: 10,000 = 1.0 FTE, 8,000 = 0.8 FTE. This keeps
the source numeric representation exact, just as integer cents do for money.
We divide by 10,000 for display. Two people working 100% and 80% give **2 headcount
and 1.8 FTE**.

### Read the model

Open `dbt/models/marts/rpt_workforce_monthly.sql`:

1. `months` gets the distinct finance reporting periods from the GL.
2. `workforce` groups employee rows by month and department. `COUNT(*)` counts
   people, while `SUM(fte_basis_points)` measures capacity. Tests enforce one row
   per employee/month so headcount cannot be inflated by duplicate payroll rows.
3. `CROSS JOIN` creates every month/department combination. Here, 24 months × six
   departments = 144 rows. Unlike an accidental many-to-many join, this is an
   intentional grid used to preserve empty departments.
4. `LEFT JOIN` attaches the aggregated payroll. Missing combinations display zero.

Headcount and FTE can be summed across departments **within one month**. Do not
sum them across months and call the result annual headcount. Personnel expenses
are monthly flows and can be summed across months.

### Your next action

Copy **`sql/bigquery/06_workforce_summary.sql`** into BigQuery and run it.
This summarizes the departmental view into 24 company-wide monthly rows.

| Month | Headcount | FTE | Personnel expense |
| --- | ---: | ---: | ---: |
| October 2024 | 75 | 74.0 | $933,404.26 |
| September 2026 | 88 | 87.0 | $1,201,872.52 |

Then inspect the departmental breakdown for one month:

```sql
SELECT
  department_name,
  headcount,
  CAST(fte_basis_points AS NUMERIC) / 10000 AS fte,
  CAST(personnel_cost_cents AS NUMERIC) / 100 AS personnel_cost_usd
FROM `saas-finance-learning-512616.finance.rpt_workforce_monthly`
WHERE month = DATE '2026-09-01'
ORDER BY department_name;
```

Explain why September has 88 people but 87.0 FTE. Both are correct: the difference
comes from employees working less than full time.

### Reconcile, do not double-count

Workday personnel costs explain amounts that are **already in the GL**:

| Workday component | GL account |
| --- | --- |
| Base pay | 6000 |
| Bonus / variable compensation | 6010 |
| Employer benefits and payroll taxes | 6020 |

Adding Workday costs to GL expenses would count payroll twice. We test equality
at employee × month × department × account, then use the personnel data for
headcount/capacity explanations and drilldowns.

### Rebuild and validation

```bash
cd /Users/jackperry/Documents/Codex/saas-finance-data-platform
.venv-dbt/bin/python scripts/dbt_lesson.py --lesson workforce
```

The live build passed **29 steps: three views, 25 data tests and one unit test**.
One view is the reused department model. Tests cover roster membership and dates,
unique employee/month keys, FTE ranges, component totals, department references,
report completeness and exact GL reconciliation. The unit test covers two people
with 1.8 combined FTE, duplicate calendar input rows and empty departments.
An independent local calculation from the employee roster and GL matched all
144 department/month rows, including every cost component and FTE. The display
query returned 24 monthly rows. Both new views were verified in `us-south1` with
59-day expiration; billing remains disabled and the 50 MiB query cap is unchanged.
Evidence is saved locally in the ignored `data/local/workforce_reconciliation.json`.

Headcount budgets, hiring/attrition bridges and personnel variance drivers are
later exercises. This lesson reports actual workforce and personnel expenses.
