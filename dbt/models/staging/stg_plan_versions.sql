select version_id, scenario, as_of_date, start_month, end_month
from {{ source('pigment', 'versions') }}
