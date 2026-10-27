-- Fail before the comparison is built if the selected lesson version is absent/changed.
with version_count as (
    select count(*) as n from {{ ref('stg_plan_versions') }}
    where version_id = 'BUD2025' and scenario = 'Budget'
      and start_month = date '2025-01-01' and end_month = date '2025-12-01'
), month_count as (
    select count(distinct month) as n from {{ ref('stg_financial_plan') }}
    where version_id = 'BUD2025'
)
select 'Expected one full-year 2025 budget' as error
from version_count where n != 1
union all
select 'Expected 12 months of BUD2025 budget rows'
from month_count where n != 12
