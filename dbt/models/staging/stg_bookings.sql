-- Grain: one signed contract booking, including full-value renewals.
select
    booking_id,
    opportunity_id,
    contract_id,
    customer_id,
    month,
    booking_type,
    booked_value_cents
from {{ source('salesforce', 'bookings') }}
