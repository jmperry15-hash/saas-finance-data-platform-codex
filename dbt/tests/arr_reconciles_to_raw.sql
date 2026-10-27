with expected as (
    select month,
        sum(mrr_cents) as mrr_cents,
        sum(arr_cents) as arr_cents,
        count(distinct if(mrr_cents > 0, customer_id, null)) as active_customers
    from {{ source('salesforce', 'customer_monthly') }}
    group by month
), actual as (
    select month, mrr_cents, arr_cents, active_customers
    from {{ ref('rpt_arr_monthly') }}
), missing as (
    select * from expected except distinct select * from actual
), unexpected as (
    select * from actual except distinct select * from expected
)
select * from missing
union all
select * from unexpected
