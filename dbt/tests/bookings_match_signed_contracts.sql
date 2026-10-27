-- One booking per in-window contract, matching the Closed Won opportunity.
with bounds as (
    select min(month) as first_month, max(month) as last_month
    from {{ ref('stg_customer_monthly') }}
), contracts as (
    select c.*
    from {{ source('salesforce', 'contracts') }} c
    cross join bounds w
    where c.start_date between w.first_month and w.last_month
)
select coalesce(b.contract_id, c.contract_id) as contract_id
from {{ ref('stg_bookings') }} b
full outer join contracts c on b.contract_id = c.contract_id
left join {{ source('salesforce', 'opportunities') }} o on c.opportunity_id = o.opportunity_id
where b.contract_id is null or c.contract_id is null or o.opportunity_id is null
   or b.customer_id != c.customer_id or b.customer_id != o.customer_id
   or b.opportunity_id != c.opportunity_id
   or b.month != c.start_date or b.month != o.close_date
   or b.booked_value_cents != c.contract_value_cents
   or b.booked_value_cents != o.annual_value_cents
   or b.booked_value_cents <= 0 or b.month != date_trunc(b.month, month)
   or o.stage != 'Closed Won' or b.booking_type != o.opportunity_type
