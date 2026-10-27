-- A monthly snapshot report: do not SUM arr_usd across months.
select
    month,
    active_customers,
    cast(mrr_cents as numeric) / 100 as mrr_usd,
    cast(arr_cents as numeric) / 100 as arr_usd,
    cast(arr_change_cents as numeric) / 100 as arr_change_usd,
    round(arr_growth_ratio * 100, 2) as arr_growth_pct
from `saas-finance-learning-512616.finance.rpt_arr_monthly`
order by month;
