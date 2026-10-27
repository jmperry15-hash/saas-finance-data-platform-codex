{{ config(schema='finance') }}

-- Lesson 3 deliberately selects one full-year budget, never sums versions.
with selected_version as (
    select version_id, start_month, end_month
    from {{ ref('stg_plan_versions') }} v
    where v.version_id = 'BUD2025' and v.scenario = 'Budget'
), actual as (
    select a.*
    from {{ ref('fct_pnl_monthly') }} a
    cross join selected_version v
    where a.month between v.start_month and v.end_month
), budget as (
    select p.month, p.department_id, p.account_id, p.amount_cents
    from {{ ref('stg_financial_plan') }} p
    join selected_version v on p.version_id = v.version_id
    where p.month between v.start_month and v.end_month
), combined as (
    -- FULL OUTER JOIN preserves unbudgeted actuals and unused budget lines.
    select
        coalesce(a.month, b.month) as month,
        coalesce(a.department_id, b.department_id) as department_id,
        coalesce(a.account_id, b.account_id) as account_id,
        coalesce(a.actual_cents, 0) as actual_cents,
        coalesce(b.amount_cents, 0) as budget_cents,
        case when a.month is null then 'Budget only'
             when b.month is null then 'Actual only'
             else 'Both' end as coverage
    from actual a
    full outer join budget b
      on a.month = b.month
     and a.department_id = b.department_id
     and a.account_id = b.account_id
)
select
    v.version_id,
    c.month,
    c.department_id,
    c.account_id,
    a.account_name,
    a.account_type,
    c.actual_cents,
    c.budget_cents,
    c.actual_cents - c.budget_cents as variance_cents,
    -- Ratio: multiply by 100 for a displayed percentage. Zero budget returns NULL.
    safe_divide(cast(c.actual_cents - c.budget_cents as numeric),
                cast(c.budget_cents as numeric)) as variance_ratio,
    -- Positive means favorable for either revenue or expense.
    case when a.account_type = 'Revenue' then c.actual_cents - c.budget_cents
         else c.budget_cents - c.actual_cents end as favorable_variance_cents,
    c.coverage
from combined c
join {{ ref('stg_accounts') }} a on c.account_id = a.account_id
cross join selected_version v
