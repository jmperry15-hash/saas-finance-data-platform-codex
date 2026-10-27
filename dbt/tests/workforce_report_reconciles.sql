with months as (
    select distinct month from {{ source('netsuite', 'gl_lines') }}
), raw_totals as (
    select month, department_id, count(*) as headcount,
        sum(fte_basis_points) as fte_basis_points,
        sum(base_pay_cents) as base_pay_cents, sum(bonus_cents) as bonus_cents,
        sum(benefits_cents) as benefits_cents, sum(personnel_cost_cents) as personnel_cost_cents
    from {{ source('workday', 'employee_monthly') }}
    group by month, department_id
), expected as (
    select m.month, d.department_id,
        coalesce(r.headcount, 0) as headcount,
        coalesce(r.fte_basis_points, 0) as fte_basis_points,
        coalesce(r.base_pay_cents, 0) as base_pay_cents,
        coalesce(r.bonus_cents, 0) as bonus_cents,
        coalesce(r.benefits_cents, 0) as benefits_cents,
        coalesce(r.personnel_cost_cents, 0) as personnel_cost_cents
    from months m cross join {{ source('shared', 'departments') }} d
    left join raw_totals r on m.month = r.month and d.department_id = r.department_id
), actual as (
    select month, department_id, headcount, fte_basis_points, base_pay_cents,
           bonus_cents, benefits_cents, personnel_cost_cents
    from {{ ref('rpt_workforce_monthly') }}
), missing as (
    select * from expected except distinct select * from actual
), unexpected as (
    select * from actual except distinct select * from expected
)
select * from missing
union all
select * from unexpected
