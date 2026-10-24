-- WITH names intermediate results (common table expressions, or CTEs).
-- Aggregate BOTH sides to the same grain before joining.
WITH payroll AS (
    SELECT month, department_id, SUM(personnel_cost_cents) AS payroll_cents
    FROM workday_employee_monthly
    GROUP BY month, department_id
), gl AS (
    SELECT month, department_id, SUM(debit_cents - credit_cents) AS payroll_gl_cents
    FROM netsuite_gl_lines
    WHERE account_id IN ('6000', '6010', '6020')
    GROUP BY month, department_id
), keys AS (
    -- UNION retains a key even if it occurs on only one side.
    SELECT month, department_id FROM payroll
    UNION
    SELECT month, department_id FROM gl
)
SELECT k.month, k.department_id,
       p.payroll_cents / 100.0 AS payroll_usd,
       g.payroll_gl_cents / 100.0 AS payroll_gl_usd,
       (COALESCE(p.payroll_cents, 0) - COALESCE(g.payroll_gl_cents, 0)) / 100.0 AS difference_usd
FROM keys AS k
LEFT JOIN payroll AS p ON k.month = p.month AND k.department_id = p.department_id
LEFT JOIN gl AS g ON k.month = g.month AND k.department_id = g.department_id
ORDER BY k.month, k.department_id;
