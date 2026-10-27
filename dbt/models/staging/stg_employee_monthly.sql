-- One employee/month row. Money stays in cents; 10,000 basis points = 1 FTE.
select
    employee_id,
    month,
    department_id,
    fte_basis_points,
    base_pay_cents,
    bonus_cents,
    benefits_cents,
    personnel_cost_cents
from {{ source('workday', 'employee_monthly') }}
