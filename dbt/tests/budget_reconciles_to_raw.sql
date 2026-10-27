-- Independent raw aggregation; check every key and amount, not just net totals.
with entries as (
    select g.month, g.department_id, g.account_id,
        if(a.account_type = 'Revenue', g.credit_cents - g.debit_cents,
           g.debit_cents - g.credit_cents) as actual_cents,
        0 as budget_cents
    from {{ source('netsuite', 'gl_lines') }} g
    join {{ source('netsuite', 'accounts') }} a on g.account_id = a.account_id
    where a.account_type in ('Revenue', 'Expense')
      and g.month between date '2025-01-01' and date '2025-12-01'
    union all
    select month, department_id, account_id, 0, amount_cents
    from {{ source('pigment', 'financial_plan') }}
    where version_id = 'BUD2025'
), expected as (
    select month, department_id, account_id,
           sum(actual_cents) as actual_cents, sum(budget_cents) as budget_cents
    from entries
    group by month, department_id, account_id
), actual as (
    select month, department_id, account_id, actual_cents, budget_cents
    from {{ ref('fct_budget_vs_actual') }}
), missing as (
    select * from expected except distinct select * from actual
), unexpected as (
    select * from actual except distinct select * from expected
)
select * from missing
union all
select * from unexpected
