{{ config(schema='finance') }}

-- Add customer balances WITHIN each month, never across months.
with monthly as (
    select
        month,
        sum(mrr_cents) as mrr_cents,
        sum(arr_cents) as arr_cents,
        countif(mrr_cents > 0) as active_customers
    from {{ ref('stg_customer_monthly') }} c
    group by month
), with_prior_month as (
    select
        *,
        lag(arr_cents) over (order by month) as previous_arr_cents
    from monthly
)
select
    month,
    mrr_cents,
    arr_cents,
    active_customers,
    previous_arr_cents,
    arr_cents - previous_arr_cents as arr_change_cents,
    safe_divide(cast(arr_cents - previous_arr_cents as numeric),
                cast(previous_arr_cents as numeric)) as arr_growth_ratio
from with_prior_month
-- First month has no observed prior month: change and growth remain NULL.
