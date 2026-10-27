{{ config(schema='finance') }}

with months as (
    -- Use the reporting calendar from snapshots, so a no-booking month remains visible.
    select distinct month from {{ ref('stg_customer_monthly') }} c
), bookings as (
    -- Aggregate events BEFORE joining the calendar (one row per month on each side).
    select
        month,
        count(*) as booking_count,
        countif(booking_type = 'New business') as new_booking_count,
        countif(booking_type = 'Renewal') as renewal_booking_count,
        sum(booked_value_cents) as total_bookings_cents,
        sum(if(booking_type = 'New business', booked_value_cents, 0)) as new_bookings_cents,
        sum(if(booking_type = 'Renewal', booked_value_cents, 0)) as renewal_bookings_cents
    from {{ ref('stg_bookings') }} b
    group by month
)
select
    m.month,
    coalesce(b.booking_count, 0) as booking_count,
    coalesce(b.new_booking_count, 0) as new_booking_count,
    coalesce(b.renewal_booking_count, 0) as renewal_booking_count,
    coalesce(b.total_bookings_cents, 0) as total_bookings_cents,
    coalesce(b.new_bookings_cents, 0) as new_bookings_cents,
    coalesce(b.renewal_bookings_cents, 0) as renewal_bookings_cents
from months m
left join bookings b on m.month = b.month
