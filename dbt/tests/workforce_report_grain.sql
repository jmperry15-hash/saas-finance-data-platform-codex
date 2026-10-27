select month, department_id
from {{ ref('rpt_workforce_monthly') }}
group by month, department_id
having count(*) != 1 or month is null or department_id is null
