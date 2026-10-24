-- Select ONE version. Aggregate actuals to the plan grain before comparing.
-- UNION + LEFT JOIN keeps both budget-only and actual-only combinations.
WITH actual AS (
    SELECT g.month, g.department_id, g.account_id,
           SUM(CASE WHEN a.account_type = 'Revenue'
                    THEN g.credit_cents - g.debit_cents
                    ELSE g.debit_cents - g.credit_cents END) AS actual_cents
    FROM netsuite_gl_lines AS g
    JOIN netsuite_accounts AS a ON g.account_id = a.account_id
    WHERE a.account_type IN ('Revenue', 'Expense')
      AND g.month BETWEEN '2026-01-01' AND '2026-09-01'
    GROUP BY g.month, g.department_id, g.account_id
), plan AS (
    SELECT month, department_id, account_id, amount_cents AS plan_cents
    FROM pigment_financial_plan
    WHERE version_id = 'BUD2026'
      AND month BETWEEN '2026-01-01' AND '2026-09-01'
), keys AS (
    SELECT month, department_id, account_id FROM actual
    UNION
    SELECT month, department_id, account_id FROM plan
)
SELECT k.month, k.department_id, k.account_id,
       a.account_name, a.account_type,
       COALESCE(x.actual_cents, 0) / 100.0 AS actual_usd,
       COALESCE(p.plan_cents, 0) / 100.0 AS budget_usd,
       (COALESCE(x.actual_cents, 0) - COALESCE(p.plan_cents, 0)) / 100.0 AS variance_usd,
       ROUND(100.0 * (COALESCE(x.actual_cents, 0) - p.plan_cents)
             / NULLIF(p.plan_cents, 0), 2) AS variance_pct,
       CASE WHEN x.actual_cents IS NULL THEN 'Plan only'
            WHEN p.plan_cents IS NULL THEN 'Actual only'
            ELSE 'Both' END AS coverage
FROM keys AS k
JOIN netsuite_accounts AS a ON k.account_id = a.account_id
LEFT JOIN actual AS x
  ON k.month = x.month AND k.department_id = x.department_id AND k.account_id = x.account_id
LEFT JOIN plan AS p
  ON k.month = p.month AND k.department_id = p.department_id AND k.account_id = p.account_id
ORDER BY k.month, k.department_id, k.account_id;
