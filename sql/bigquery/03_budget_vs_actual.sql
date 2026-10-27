-- Run in BigQuery. Summarize the 2025 budget comparison by month and account type.
-- Positive favorable_variance_usd means favorable for both revenue and expenses.
select
    month,
    account_type,
    cast(sum(actual_cents) as numeric) / 100 as actual_usd,
    cast(sum(budget_cents) as numeric) / 100 as budget_usd,
    cast(sum(variance_cents) as numeric) / 100 as variance_usd,
    cast(sum(favorable_variance_cents) as numeric) / 100 as favorable_variance_usd
from `saas-finance-learning-512616.finance.fct_budget_vs_actual`
group by month, account_type
order by month, account_type;
