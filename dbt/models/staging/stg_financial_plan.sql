-- Keep versions separate. Amounts already use positive revenue/expense convention.
select version_id, month, department_id, account_id, amount_cents
from {{ source('pigment', 'financial_plan') }}
