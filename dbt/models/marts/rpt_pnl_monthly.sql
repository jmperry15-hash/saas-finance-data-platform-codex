{{ config(schema='finance') }}

-- Grain: one row per month with GL activity, including months with zero P&L activity.
-- The account key must be unique and every GL account must be mapped (tested upstream).
with monthly as (
    select
        gl.month,
        sum(case when accounts.account_type = 'Revenue'
            then gl.credit_cents - gl.debit_cents else 0 end) as revenue_cents,
        sum(case when accounts.account_type = 'Expense'
            then gl.debit_cents - gl.credit_cents else 0 end) as expense_cents
    from {{ ref('stg_gl_lines') }} as gl
    join {{ ref('stg_accounts') }} as accounts on gl.account_id = accounts.account_id
    group by gl.month
)
select
    month,
    revenue_cents,
    expense_cents,
    revenue_cents - expense_cents as operating_profit_cents
from monthly
