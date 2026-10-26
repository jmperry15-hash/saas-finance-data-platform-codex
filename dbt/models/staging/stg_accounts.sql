select
    trim(account_id) as account_id,
    trim(account_name) as account_name,
    trim(account_type) as account_type
from {{ source('netsuite', 'accounts') }}
