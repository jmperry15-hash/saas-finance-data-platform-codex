{{ config(schema='finance') }}

with months as (
    -- Use the finance reporting periods, including months/departments with no payroll.
    select distinct month from {{ source('netsuite', 'gl_lines') }} g
), workforce as (
    select
        month,
        department_id,
        count(*) as headcount,
        sum(fte_basis_points) as fte_basis_points,
        sum(base_pay_cents) as base_pay_cents,
        sum(bonus_cents) as bonus_cents,
        sum(benefits_cents) as benefits_cents,
        sum(personnel_cost_cents) as personnel_cost_cents
    from {{ ref('stg_employee_monthly') }} e
    group by month, department_id
)
select
    m.month,
    d.department_id,
    d.department_name,
    coalesce(w.headcount, 0) as headcount,
    coalesce(w.fte_basis_points, 0) as fte_basis_points,
    coalesce(w.base_pay_cents, 0) as base_pay_cents,
    coalesce(w.bonus_cents, 0) as bonus_cents,
    coalesce(w.benefits_cents, 0) as benefits_cents,
    coalesce(w.personnel_cost_cents, 0) as personnel_cost_cents
from months m
cross join {{ ref('stg_departments') }} d
left join workforce w on m.month = w.month and d.department_id = w.department_id
