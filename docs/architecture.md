# Architecture and implementation decisions

This is the target design, not a list of already deployed components. Sources
and constraints were checked October 24, 2026; recheck them at the cloud setup gate.

## Storage and transformation layers

1. **Local synthetic sources**: reproducible CSV files grouped by mock system.
   `shared/departments` is the deliberately common master-data mapping. In a real
   company, source-specific IDs would usually require a maintained crosswalk.
2. **BigQuery raw datasets**: `raw_shared`, `raw_netsuite`, `raw_salesforce`,
   `raw_workday`, `raw_pigment`. Keep source grain and names; ingestion adds a
   batch ID and load timestamp. Load explicit types rather than autodetecting IDs.
3. **`staging`**: dbt views type, rename, and standardize fields. Preserve source
   records, convert cents explicitly, and validate keys. No finance aggregation yet.
4. **`finance`**: reusable dimensions plus reporting facts. Aggregate each source
   to its intended grain before combining sources, avoiding join multiplication.
5. **Streamlit**: read reporting models with a read-only identity, apply filters,
   cache small results, and present definitions and the last successful refresh.

Use one BigQuery region (proposed: US) for all datasets. SQLite is a local SQL
learning lab, not an extra production service. BigQuery is an analytical warehouse;
its key declarations are not a substitute for integrity tests. No Postgres,
Supabase, Docker, Airflow, paid dbt platform, cloud object-storage bucket, or paid
LLM API is needed for this project.

## Proposed reporting models

| Model | Grain | Business rules and reconciliation |
| --- | --- | --- |
| `dim_month`, `dim_department`, `dim_account`, `dim_customer` | One row per dimension key | Unique keys; common dates and names |
| `fct_gl_line` | One journal line | Debit-positive accounting; journal/month debits equal credits |
| `fct_pnl_monthly` | Month × department × account | Revenue = credit minus debit; expenses = debit minus credit; exclude balance sheet accounts |
| `fct_plan_monthly` | Version × month × department × account | One selected version at a time; positive revenue and expense values |
| `fct_budget_vs_actual` | Selected version × month × department × account | Full outer join or complete key spine keeps budget-only and actual-only rows |
| `fct_customer_monthly` | Customer × month | MRR, ARR, acquisition, renewal, expansion/contraction/churn; zero-balance rows retained |
| `fct_bookings` | Signed contract booking | Full annual new or renewal contract value, counted only at signature |
| `fct_workforce_monthly` | Employee × month | Active roster, FTE, salary/variable/benefits; exact tie to personnel GL |
| `fct_department_spend` | Month × department × expense account | Aggregate once from GL; payroll detail provides explanation, not additional expense |

**P&L classifications:** hosting and Customer Success personnel are cost of
revenue. Engineering is R&D. Sales and Marketing are S&M. Finance and People are
G&A. Revenue is assigned to Sales for ownership; that does not make it S&M expense.
This supports gross profit and operating profit; tax, interest, D&A, and stock
compensation are omitted, so it is not a complete GAAP income statement.

**Metric discipline:** ARR is month-end MRR × 12, never a sum of monthly ARR.
Revenue is the service recognized during a period; bookings are the full contract
value signed during that period, including renewals. Active customers have MRR > 0.
Customer counts and headcount are month-end snapshots, not additive across months.
NRR/GRR will compare a fixed beginning customer cohort to its ending MRR, excluding
new customers, with unavailable percentages when starting MRR is zero.

**Variances:** dollar variance = actual minus selected plan. Revenue above plan
is favorable; expense above plan is unfavorable. Percentage variance uses plan
as denominator; a zero plan returns NULL and a clear label. H2 forecasts contain
July onward estimates only. A full-year outlook explicitly combines first-half
actuals with one H2 forecast; it must not sum Budget and Forecast together.

**Explanations:** rank measured department/account variances, headcount changes,
salary rate changes, customer movements, and labeled seasonal events. These are
rule-based explanations tied to data, not paid AI-generated causal claims.

## Free-only design

BigQuery Sandbox requires no credit card or billing account. The current limits
are 10 GiB of **lifetime** storage (deletion does not refund it), 1 TiB query
processing per month, and automatic expiration after 60 days for tables, views,
and partitions. Streaming, DML, and Data Transfer Service are unsupported.
[Google documentation](https://docs.cloud.google.com/bigquery/docs/sandbox).

Design consequences:

- Upload local files directly with batch load jobs; no Cloud Storage bucket.
- Prefer views for dbt staging and small full table builds only when needed.
  Do not use dbt incremental `MERGE`, snapshots that rely on DML, or DML seeds.
- Use batch replacement (`WRITE_TRUNCATE` load disposition) for raw refreshes,
  not the SQL `TRUNCATE` statement. Verify one small load/model on Sandbox first.
- Keep all source generation and dbt definitions in Git. Rebuild expired objects
  from local sources; do not claim 60-day expiration is a permanent warehouse.
- Track cumulative uploaded/materialized data and query bytes. Rebuilding or
  deleting tables does not reset the lifetime storage allowance. CSV file size
  is only a local scale indicator, not BigQuery storage accounting.
- Dry-run queries and set maximum bytes billed in the clients where supported;
  these are query guards, not permission to enable billing. Cache dashboard reads.
- Stop at a quota limit and continue locally. Never attach billing, accept a
  trial requiring payment setup, or upgrade without explicit user approval.

GitHub Actions standard runners are free for public repositories; private
repositories use account-shared allowances. GitHub Free currently includes
2,000 minutes/month and 500 MB of artifact storage. Larger runners are charged.
Before enabling Actions, verify the account's remaining allowance and configure
a stop-usage budget where available. Start with manual runs and short timeouts,
no artifact uploads/cache, and standard Ubuntu runners. If a zero-cost boundary
cannot be established, keep automation local.
[GitHub billing documentation](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

Run Streamlit locally first. Optional Community Cloud hosting is free, but
deployment and credential handling are later tasks.
[Streamlit documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud).

## Refresh, failure handling, and credentials

The future pipeline is: extract all pages/files → validate schemas and totals →
load a complete batch → run dbt and tests → allow reporting on the successful batch.
Retry transient network errors with bounded exponential backoff. Do not retry
bad credentials or invalid schemas indefinitely. Log table names, counts, batch
IDs, timings, and safe error details; never log credentials or full HTTP headers.

A multi-table refresh is not automatically atomic. Start with a manual maintenance
window and block dashboard refresh until all loads/tests succeed. Keep the last
known-good local extracts for recovery. Later, if worthwhile, stage batch tables
and publish only validated versions, while accounting for extra Sandbox storage.

For local BigQuery development, prefer application default credentials via the
Google CLI, stored outside the repo. For Actions, investigate OIDC/Workload Identity
Federation with a narrowly scoped service account, avoiding downloaded JSON keys.
Verify the no-billing setup works before committing to remote warehouse automation;
CI can always validate the synthetic data without cloud authentication.

Ingestion needs dataset-scoped write rights plus permission to run jobs. Reporting
needs read access to reporting datasets plus query-job permission. Avoid project
Owner/Editor, and give CI only `contents: read` unless a documented step needs more.
Do not expose credentials to untrusted pull requests. `.gitignore` is a guard,
not a secret scanner; review staged files before each push.

## Scope of the first milestone

The CSVs resemble business entities from the named tools; they are not exact
NetSuite, Salesforce, Workday, or Pigment API payloads. Local API practice will
wrap these synthetic records. No vendor sandbox subscriptions are required.
