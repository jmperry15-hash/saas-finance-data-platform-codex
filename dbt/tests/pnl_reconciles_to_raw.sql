-- Compare each month to raw accounting totals, bypassing both staging models.
-- Separate aggregates preserve the full set of GL months and check both signs.
with raw_totals as (
    select
        gl.month,
        sum(if(a.account_type = 'Revenue', gl.credit_cents, 0))
          - sum(if(a.account_type = 'Revenue', gl.debit_cents, 0)) as revenue,
        sum(if(a.account_type = 'Expense', gl.debit_cents, 0))
          - sum(if(a.account_type = 'Expense', gl.credit_cents, 0)) as expense
    from {{ source('netsuite', 'gl_lines') }} gl
    join {{ source('netsuite', 'accounts') }} a on gl.account_id = a.account_id
    group by gl.month
)
select coalesce(raw.month, pnl.month) as month
from raw_totals raw
full outer join {{ ref('rpt_pnl_monthly') }} pnl on raw.month = pnl.month
where raw.month is null or pnl.month is null
   or pnl.revenue_cents != raw.revenue
   or pnl.expense_cents != raw.expense
   or pnl.operating_profit_cents != raw.revenue - raw.expense
