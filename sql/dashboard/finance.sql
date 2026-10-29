-- Same grain as the dashboard: month x department x account, integer USD cents.
-- Read the dbt outputs; BUD2025 remains unavailable outside 2025.
WITH combined AS (
    SELECT
        COALESCE(a.month, b.month) AS month,
        COALESCE(a.department_id, b.department_id) AS department_id,
        COALESCE(a.account_id, b.account_id) AS account_id,
        COALESCE(a.actual_cents, b.actual_cents, 0) AS actual_cents,
        b.budget_cents
    FROM `saas-finance-learning-512616.finance.fct_pnl_monthly` a
    FULL OUTER JOIN `saas-finance-learning-512616.finance.fct_budget_vs_actual` b
        USING (month, department_id, account_id)
)
SELECT c.month, c.department_id, c.account_id,
       d.department_name AS department, d.department_function AS `function`,
       a.account_name AS account, a.account_type,
       c.actual_cents, c.budget_cents
FROM combined c
JOIN `saas-finance-learning-512616.staging.stg_departments` d USING (department_id)
JOIN `saas-finance-learning-512616.staging.stg_accounts` a USING (account_id)
ORDER BY month, department_id, account_id
