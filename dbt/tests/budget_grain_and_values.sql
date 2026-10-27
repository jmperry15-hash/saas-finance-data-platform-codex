select month, department_id, account_id
from {{ ref('fct_budget_vs_actual') }}
group by month, department_id, account_id
having count(*) != 1
union all
select month, department_id, account_id
from {{ ref('fct_budget_vs_actual') }}
where month is null or department_id is null or account_id is null
   or month not between date '2025-01-01' and date '2025-12-01'
   or actual_cents is null or budget_cents is null or variance_cents is null
   or favorable_variance_cents is null or coverage is null
   or variance_cents != actual_cents - budget_cents
   or (budget_cents = 0 and variance_ratio is not null)
   or (budget_cents != 0 and variance_ratio is null)
