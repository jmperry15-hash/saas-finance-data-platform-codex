{{ config(schema='finance') }}

-- Grain: month x department x account. Aggregate BEFORE joining to a budget.
select
    gl.month,
    gl.department_id,
    gl.account_id,
    sum(case when a.account_type = 'Revenue'
        then gl.credit_cents - gl.debit_cents
        else gl.debit_cents - gl.credit_cents end) as actual_cents
from {{ ref('stg_gl_lines') }} gl
join {{ ref('stg_accounts') }} a on gl.account_id = a.account_id
where a.account_type in ('Revenue', 'Expense')
group by gl.month, gl.department_id, gl.account_id
