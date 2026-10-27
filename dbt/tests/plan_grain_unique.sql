select version_id, month, department_id, account_id
from {{ ref('stg_financial_plan') }}
group by version_id, month, department_id, account_id
having count(*) != 1
