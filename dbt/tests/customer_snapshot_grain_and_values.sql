select customer_id, month
from {{ ref('stg_customer_monthly') }}
group by customer_id, month
having count(*) != 1
union all
select customer_id, month
from {{ ref('stg_customer_monthly') }}
where mrr_cents < 0 or arr_cents < 0 or arr_cents != mrr_cents * 12
   or month != date_trunc(month, month)
