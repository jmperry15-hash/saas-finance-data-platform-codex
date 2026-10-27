-- This generator supplies every master customer in every month, even when inactive.
-- Enforce that contract so missing months cannot make LAG compare non-adjacent months.
with bounds as (
    select min(month) as first_month, max(month) as last_month
    from {{ ref('stg_customer_monthly') }}
), expected as (
    select c.customer_id, month
    from {{ source('salesforce', 'customers') }} c
    cross join bounds b
    cross join unnest(generate_date_array(b.first_month, b.last_month, interval 1 month)) month
)
select e.customer_id, e.month
from expected e
left join {{ ref('stg_customer_monthly') }} s
  on e.customer_id = s.customer_id and e.month = s.month
where s.customer_id is null
