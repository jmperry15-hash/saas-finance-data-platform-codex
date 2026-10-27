-- Reconcile each employee/month/department/account, not only company totals.
with payroll as (
    select employee_id, month, department_id, '6000' as account_id, base_pay_cents as amount
    from {{ ref('stg_employee_monthly') }}
    union all
    select employee_id, month, department_id, '6010', bonus_cents
    from {{ ref('stg_employee_monthly') }}
    union all
    select employee_id, month, department_id, '6020', benefits_cents
    from {{ ref('stg_employee_monthly') }}
), gl as (
    select employee_id, month, department_id, account_id,
           sum(debit_cents - credit_cents) as amount
    from {{ source('netsuite', 'gl_lines') }}
    where account_id in ('6000', '6010', '6020')
    group by employee_id, month, department_id, account_id
)
select coalesce(p.employee_id, g.employee_id) as employee_id,
       coalesce(p.month, g.month) as month, coalesce(p.account_id, g.account_id) as account_id
from payroll p
full outer join gl g on p.employee_id = g.employee_id and p.month = g.month
    and p.department_id = g.department_id and p.account_id = g.account_id
where coalesce(p.amount, 0) != coalesce(g.amount, 0)
