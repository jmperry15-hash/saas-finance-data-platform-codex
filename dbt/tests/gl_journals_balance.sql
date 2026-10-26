-- Every journal must balance, not just the grand total.
select journal_id
from {{ ref('stg_gl_lines') }}
group by journal_id
having sum(debit_cents) != sum(credit_cents)
    or count(distinct month) != 1
