select p.version_id, p.month, p.account_id
from {{ ref('stg_financial_plan') }} p
join {{ ref('stg_plan_versions') }} v on p.version_id = v.version_id
join {{ ref('stg_accounts') }} a on p.account_id = a.account_id
where p.month not between v.start_month and v.end_month
   or a.account_type not in ('Revenue', 'Expense')
   or p.month != date_trunc(p.month, month)
