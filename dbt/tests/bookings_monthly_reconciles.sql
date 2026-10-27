with expected as (
    select month, count(*) as booking_count,
           sum(booked_value_cents) as total_bookings_cents
    from {{ source('salesforce', 'bookings') }}
    group by month
)
select coalesce(e.month, r.month) as month
from expected e
full outer join {{ ref('rpt_bookings_monthly') }} r on e.month = r.month
where r.month is null
   or r.total_bookings_cents != coalesce(e.total_bookings_cents, 0)
   or r.booking_count != coalesce(e.booking_count, 0)
   or r.total_bookings_cents != r.new_bookings_cents + r.renewal_bookings_cents
   or r.booking_count != r.new_booking_count + r.renewal_booking_count
   or r.new_booking_count is null or r.renewal_booking_count is null
