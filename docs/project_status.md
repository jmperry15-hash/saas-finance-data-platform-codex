# Project status — October 26, 2026

The data and reporting foundation is built. Automation and the user-facing
dashboard are the main remaining milestones. This is a learning prototype,
not yet a fully automated platform.

## Completed and learned

| Area | Implemented and verified | Capabilities practiced |
| --- | --- | --- |
| Synthetic sources | 14 related tables, 24 months, shared IDs, balanced GL and cross-system controls | Python functions, reproducibility, data types, monetary cents, data validation |
| Local relational database | SQLite loader and SQL exercises; user queried the data | Tables, keys, joins, aggregation, reporting grain |
| Cloud warehouse | All 14 raw tables uploaded to BigQuery; schemas/counts and GL totals verified | Datasets, explicit schemas, batch loads, regions, table expiration |
| Python ingestion | Pandas GL validation and repeatable GL replacement load; two successful user runs | DataFrames, authentication, idempotency, logging, checks before and after loading |
| Mock API | 130 customers extracted across six pages; automated failure tests | HTTP/JSON, pagination, bounded retries, atomic file output |
| dbt | 14 SQL models covering staging, P&L, BUD2025 comparison, ARR/customers, bookings and workforce | `source`, `ref`, dependency ordering, SQL views, data and unit tests, reconciliations |
| Version control/security | Local Git commits; ignored credentials and generated data; guarded cloud helpers | Git history, environments, ADC login, least privilege and cost controls |

The dbt project contains 104 data tests and four unit tests. Each lesson's
selected models/tests has passed; a single complete end-to-end build is still
part of the final verification. Those counts should not be confused with the
separate Python suite or with sums of overlapping lesson runs.

Evidence includes prior successful build logs, independent CSV reconciliations,
and the user's upload/query screenshots. This document is not a fresh live
verification of cloud freshness or account settings.

## Started now

[Milestone 6, lesson 1](milestone_06.md): a manual GitHub Actions workflow for
synthetic generation, saved-file validation and the Python tests. The workflow
is local; a hosted run and GitHub remote connection remain pending.

## Remaining core work

1. **Complete refresh pipeline:** refresh all necessary raw sources consistently,
   then rebuild/test reporting models. Check reruns, failures and recovery from
   expired sandbox tables. Only the GL has a dedicated Python refresh today.
2. **GitHub automation:** connect/push the repository, verify CI, demonstrate
   failure handling, and establish a free manual refresh path. A schedule is
   optional and comes after a successful manual run.
3. **Streamlit dashboard:** P&L/BvA, revenue/ARR/bookings/customer trends,
   headcount/personnel, department spending and variance explanations. Add
   period/comparison filters, metric definitions, caching and freshness labels.
   Start locally so hosting is not required.
4. **End-to-end acceptance:** regenerate/load/build/test and reconcile dashboard
   values to the reporting datasets; document setup, limits and recovery.

There are **two main named milestones left (6 and 7)** plus end-to-end acceptance.
The complete refresh work is included in milestone 6. These are substantial
steps, so counting completed milestones does not translate into a reliable
percentage of effort remaining.

## Boundaries and optional enhancements

- The budget comparison currently selects BUD2025. Other budgets/forecasts and
  headcount-plan comparisons are future enhancements.
- ARR bridges and retention metrics such as GRR/NRR are not built.
- Detailed department/account actuals exist; the spending dashboard is unbuilt.
- The mock-API extractor saves a local file; API-to-BigQuery integration is
  deferred. No real vendor integrations are used.
- The manual API failure exercise was explicitly skipped. Automated failure
  tests are present; do not describe the skipped exercise as completed.
- Some advanced SQL practice, explicit query-cost review and customer-level
  cloud revenue reconciliation remain open. Monthly revenue/ARR and detailed
  payroll reconciliation have passed.
- BigQuery billing remains disabled per the last verified runs. Sandbox table
  expiration still requires a reliable reload process. No paid services should
  be enabled to finish the project.
