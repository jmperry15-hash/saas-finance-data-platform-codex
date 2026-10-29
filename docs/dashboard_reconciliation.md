# Dashboard-to-warehouse reconciliation

This checkpoint connects two parts of the project: the dashboard's saved local
snapshot and the SQL reporting layer in BigQuery. A dashboard can look correct
while reading old or different data, so we compare every field at the original
reporting grain—not only headline totals.

## What the commands do

Run from the project folder:

```bash
cd /Users/jackperry/Documents/Codex/saas-finance-data-platform
.venv-dbt/bin/python scripts/dbt_lesson.py --lesson all
.venv-dbt/bin/python scripts/reconcile_dashboard.py --check-cloud
```

1. **Build and test:** dbt rebuilds the 14 SQL views in dependency order and runs
   104 data tests plus four unit tests. Source tables are not reloaded. The
   helper verifies billing is disabled, source locations/counts, and reporting
   dataset expiration settings before building.
2. **Reconcile:** Python reads the existing dashboard snapshot, then runs four
   read-only SQL queries against BigQuery. Dates are normalized to ISO strings;
   monetary amounts stay in integer cents. Duplicate keys, missing rows,
   changed fields, and null-versus-zero differences fail the comparison.
3. **Save evidence:** an ignored local receipt records the snapshot SHA-256,
   execution timestamps, exact SQL, job IDs, returned rows, byte estimates,
   and comparison results in `data/local/dashboard_reconciliation.json`.

The reconciliation checks billing separately, dry-runs each query, and caps
each at 50 MiB. It uses your existing local Google login; it needs no new key.
A structural preview makes no cloud calls:

```bash
.venv/bin/python scripts/reconcile_dashboard.py
```

## The four connections

| Dashboard data | BigQuery sources | Grain |
| --- | --- | --- |
| Finance | `fct_pnl_monthly`, `fct_budget_vs_actual`, staging departments/accounts | Month × department × account |
| SaaS | `stg_customer_monthly`, raw customer names/segments | Month × customer |
| Workforce | `rpt_workforce_monthly`, staging departments | Month × department |
| Bookings | `stg_bookings`, raw customer names/segments | Booking ID |

Read the queries in `sql/dashboard/`. These queries select existing dbt outputs;
dbt's own model SQL remains in `dbt/models/`. Customer names and segments come
from the raw customer master because there is no separate customer-master dbt
model yet.

ARR, headcount, and FTE are ending balances. Revenue, bookings, and personnel
costs sum over a period. The only budget selected is BUD2025; budget is null
outside 2025. None of these definitions changes in this checkpoint.

## Verified result and limits

**Verified October 28, 2026:** the full dbt run passed all 122 steps (14 views,
104 data tests and four unit tests). All 4,047 snapshot rows matched every field:
600 finance, 3,120 SaaS, 144 workforce, 183 bookings. The four queries processed
975,041 bytes in total. Billing was disabled with no linked account. The local
Python suite passed 64 tests and the dashboard model passed 186 comparisons
plus coverage/plan assertions.

A successful reconciliation is a point-in-time match of the local dashboard
data with the warehouse. It does not reload synthetic raw sources, change the
dashboard file, republish the website, verify the current hosted site payload,
or add automatic refresh. The next implementation step is a repeatable local
refresh pipeline, with validation before publication. Scheduling can wait.
