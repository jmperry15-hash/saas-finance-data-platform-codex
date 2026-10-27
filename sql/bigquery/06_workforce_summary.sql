-- Headcount and FTE are monthly balances; personnel expense is a monthly flow.
select
    month,
    sum(headcount) as headcount,
    cast(sum(fte_basis_points) as numeric) / 10000 as fte,
    cast(sum(base_pay_cents) as numeric) / 100 as base_pay_usd,
    cast(sum(bonus_cents) as numeric) / 100 as bonus_usd,
    cast(sum(benefits_cents) as numeric) / 100 as benefits_usd,
    cast(sum(personnel_cost_cents) as numeric) / 100 as personnel_cost_usd
from `saas-finance-learning-512616.finance.rpt_workforce_monthly`
group by month
order by month;
