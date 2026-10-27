-- Grain: one row per customer per month, including inactive customers with zero MRR.
select
    customer_id,
    month,
    contract_id,
    mrr_cents,
    arr_cents,
    movement,
    mrr_change_cents
from {{ source('salesforce', 'customer_monthly') }}
