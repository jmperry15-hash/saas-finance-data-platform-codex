select employee_id, month
from {{ ref('stg_employee_monthly') }}
group by employee_id, month
having count(*) != 1
union all
select employee_id, month
from {{ ref('stg_employee_monthly') }}
where month != date_trunc(month, month)
   or fte_basis_points <= 0 or fte_basis_points > 10000
   or base_pay_cents < 0 or bonus_cents < 0 or benefits_cents < 0
   or personnel_cost_cents != base_pay_cents + bonus_cents + benefits_cents
