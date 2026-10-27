-- All three views have one row per month: join AFTER aggregation to avoid duplication.
-- Bookings and revenue are period flows; ARR is a snapshot and must not be summed over time.
select
    b.month,
    b.booking_count,
    cast(b.new_bookings_cents as numeric) / 100 as new_bookings_usd,
    cast(b.renewal_bookings_cents as numeric) / 100 as renewal_bookings_usd,
    cast(b.total_bookings_cents as numeric) / 100 as total_bookings_usd,
    cast(p.revenue_cents as numeric) / 100 as revenue_usd,
    cast(a.arr_cents as numeric) / 100 as arr_usd
from `saas-finance-learning-512616.finance.rpt_bookings_monthly` b
left join `saas-finance-learning-512616.finance.rpt_pnl_monthly` p on b.month = p.month
left join `saas-finance-learning-512616.finance.rpt_arr_monthly` a on b.month = a.month
order by b.month;
