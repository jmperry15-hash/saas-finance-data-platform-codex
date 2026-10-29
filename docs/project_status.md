# Project status — October 28, 2026

The manual refresh pipeline now connects all fourteen synthetic sources to
BigQuery, dbt, and the local Data + Sites dashboard. The first complete live run
passed on October 28 in about three minutes. The dashboard reads a saved
warehouse export; it does not issue live warehouse queries while you browse.
See [the manual refresh lesson](manual_refresh.md) and [dashboard documentation](dashboard.md).

## Completed and learned

| Area | Implemented and verified | Capabilities practiced |
| --- | --- | --- |
| Synthetic sources | 14 related tables, 24 months, shared IDs, balanced GL and cross-system controls | Python functions, reproducibility, data types, monetary cents, data validation |
| Local relational database | SQLite loader and SQL exercises; user queried the data | Tables, keys, joins, aggregation, reporting grain |
| Cloud warehouse | All 14 raw tables uploaded to BigQuery; schemas/counts and GL totals verified | Datasets, explicit schemas, batch loads, regions, table expiration |
| Python ingestion | Pandas GL exercise plus complete 14-table refresh; every uploaded field verified | DataFrames, authentication, idempotency, logging, checks before and after loading |
| Mock API | 130 customers extracted across six pages; automated failure tests | HTTP/JSON, pagination, bounded retries, atomic file output |
| dbt | 14 SQL models covering staging, P&L, BUD2025 comparison, ARR/customers, bookings and workforce | `source`, `ref`, dependency ordering, SQL views, data and unit tests, reconciliations |
| Version control/security | Local Git history published to the user-approved public portfolio; ignored credentials and generated data; guarded cloud helpers | Git history, environments, ADC login, least privilege and cost controls |
| GitHub Actions | Expanded hosted validation succeeded on application commit `614edb6`, including dashboard checks | Fresh runner, YAML steps, dependencies, logs and automated tests |
| Dashboard | Data + Sites implementation; verified BigQuery export, model checks and browser review pass | Filters, reporting periods, ending balances versus flows, drilldowns and provenance |

The complete October 28 dbt build passed: **14 views, 104 data tests, four unit
tests; 122 successful steps, zero warnings/errors/skips**. Invocation:
`63b83a9f-1714-4eba-9b73-7f00de8eb4fe` was the earlier complete build; another
complete build passed inside refresh run `20261029T002826Z_7974e978`. The local
Python suite now passes 73 tests, including reconciliation and refresh failure controls. The JavaScript dashboard model passed
186 numerical comparisons plus coverage/plan assertions. These are distinct
suites and should not be summed as an accuracy percentage.

The full refresh verified all 23,794 raw rows and matched 600 finance, 3,120
customer-month, 144 workforce and 183 booking rows against independent SQLite
calculations. Evidence is in the ignored folder
`data/local/refresh-runs/20261029T002826Z_7974e978/`: the receipt, exact frozen
inputs, job IDs, dbt logs/results, executed SQL and returned reporting rows.
Billing was checked live: disabled, with no linked account.

All three local dashboard tabs rendered after refresh. Source inspection showed
BigQuery SQL and the new query time. The private hosted website retains the
October 27 snapshot; it was not republished. The portfolio synchronization checkpoint includes the dashboard and pipeline
source plus reproducible offline dashboard checks. Its clean staged copy passed
764 source controls, 73 Python tests and 186 dashboard comparisons on October 28,
with Google credential paths disabled. The expanded [hosted workflow](https://github.com/jmperry15-hash/saas-finance-data-platform-codex/actions/runs/40796000119)
then passed on application commit `614edb6`, including dependency installation
on Ubuntu, all 73 Python tests and all dashboard comparisons.

## Current learning step

Follow [reproducible portfolio validation](portfolio_validation.md): inspect
the successful GitHub workflow and find the dashboard comparison result.
This tests the committed code without Google credentials. The manual cloud
refresh and hosted dashboard publication are separate operations.

## Remaining core work

1. **Hosted dashboard update:** publish the verified warehouse-backed snapshot
   to the same private Site and verify delivery.
2. **Final learning acceptance:** have the user run the refresh, inspect its
   receipt and trace one metric. A second full live run can demonstrate
   idempotency; only one complete live run has been exercised so far.

Missing-table recreation, timeout behavior, concurrent-run rejection and
failed-build rollback passed offline tests. Live recovery was not tested by
deleting warehouse tables. A failed batch can leave partially refreshed raw
tables: loads are atomic per table, while dashboard promotion waits for all
checks. The lesson explains recovery and preserves the last good dashboard.

Remote cloud authentication, scheduling, and deliberate failure exercises on
GitHub remain optional. They need not block completing this learning prototype.

## Boundaries and optional enhancements

- The budget comparison currently selects BUD2025. Other budgets/forecasts and
  headcount-plan comparisons are future enhancements.
- ARR bridges and retention metrics such as GRR/NRR are not built.
- Detailed department/account actuals and dashboard spending views are implemented.
- The mock-API extractor saves a local file; API-to-BigQuery integration is
  deferred. No real vendor integrations are used.
- The manual API failure exercise was explicitly skipped. Automated failure
  tests are present; do not describe the skipped exercise as completed.
- Advanced SQL practice remains optional. This checkpoint dry-ran four bounded
  queries and matched all customer-month MRR/ARR fields; monthly revenue and
  detailed payroll reconciliation also passed in the full dbt build.
- BigQuery billing was verified disabled on October 28. Sandbox table
  expiration is handled by reloading missing tables; missing datasets still
  require review. No paid services should be enabled to finish the project.
