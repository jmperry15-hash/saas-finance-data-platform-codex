# Final walkthrough: trace one finance metric

The hosted dashboard now uses the verified BigQuery export. This exercise connects
what you see on screen with the pipeline you built. It makes no cloud changes.

1. Open [Juniper Cloud Finance](https://juniper-finance-jack-2026.jmperry41.chatgpt.site)
   and sign in with the owner account if prompted.
2. On **Financial performance**, select January–December 2025 and Department All.
   Revenue should display **$5.81M**; the P&L detail shows **$5,812,406** rounded
   to whole dollars. Operating profit should display **-$8.51M**.
3. Click Revenue's **⋯ → View data source**. In Overview, find the reporting
   period, definitions, BigQuery tables and **October 28, 2026, 6:31 PM** query
   time (Denver). The reporting period and extraction time mean different things.
4. Open **SQL query**. Match it to `sql/dashboard/finance.sql` in this repository.
   This query reads the dbt views; it does not create the raw GL transactions.
5. Read `dbt/models/marts/fct_pnl_monthly.sql` and follow its `ref()` calls.
   Revenue is credits minus debits on revenue accounts; expenses use the reverse
   sign. Money stays in integer cents until display.
6. Switch to **ARR & bookings**, through September 2026: ending ARR is **$7.57M**
   and active customers are **100**. ARR uses the ending month, not a sum across
   months. On **Workforce**, ending headcount is **88**, while FTE is **87**.

## Explain the architecture in your own words

- Python creates and validates synthetic source data, then loads BigQuery.
- BigQuery stores data and executes the SQL.
- dbt manages SQL dependencies and tests, producing finance reporting views.
- Python exports those views and reconciles them to independent local calculations.
- The dashboard displays that saved export. Clicking filters does not query BigQuery.
- GitHub stores code; GitHub Actions tests reproducibility. The private Site hosts
  the dashboard. A GitHub push alone does not update the Site.

## Optional final practice

Follow [manual_refresh.md](manual_refresh.md) to run the full refresh yourself
and inspect its saved receipt. It updates the local dashboard; hosted publication
is separate. One full live refresh has passed so far. A second full run can
illustrate idempotency, but it is not needed just to view or trace the metrics.

The main prototype is implemented. Scheduling, API-to-BigQuery integration,
forecast selection, headcount-plan comparisons and retention/ARR bridges remain
optional extensions; they are not claimed as completed.
