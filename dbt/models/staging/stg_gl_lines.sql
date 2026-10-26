-- Preserve the journal-line grain and accounting signs, including balance sheet lines.
select
    line_id,
    journal_id,
    month,
    account_id,
    department_id,
    customer_id,
    employee_id,
    vendor_id,
    source_type,
    source_id,
    debit_cents,
    credit_cents,
    memo
from {{ source('netsuite', 'gl_lines') }}
