-- First aggregate customer ARR to one company-month; never sum ARR across months.
-- LAG looks at the previous row after ordering months chronologically.
WITH monthly AS (
    SELECT month, SUM(arr_cents) AS arr_cents,
           SUM(CASE WHEN mrr_cents > 0 THEN 1 ELSE 0 END) AS paying_customers
    FROM salesforce_customer_monthly
    GROUP BY month
), trend AS (
    SELECT month, arr_cents, paying_customers,
           LAG(arr_cents) OVER (ORDER BY month) AS previous_arr_cents
    FROM monthly
)
SELECT month, paying_customers, arr_cents / 100.0 AS arr_usd,
       (arr_cents - previous_arr_cents) / 100.0 AS arr_change_usd,
       ROUND(100.0 * (arr_cents - previous_arr_cents)
             / NULLIF(previous_arr_cents, 0), 2) AS arr_growth_pct
FROM trend
ORDER BY month;
