with months as (
    select distinct month from {{ source('netsuite', 'gl_lines') }}
), expected as (
    select e.employee_id, m.month, e.department_id, e.fte_basis_points
    from {{ source('workday', 'employees') }} e
    cross join months m
    where e.hire_date <= m.month
      and (e.termination_date is null or m.month <= e.termination_date)
), actual as (
    select employee_id, month, department_id, fte_basis_points
    from {{ ref('stg_employee_monthly') }}
), missing as (
    select * from expected except distinct select * from actual
), unexpected as (
    select * from actual except distinct select * from expected
)
select * from missing
union all
select * from unexpected
