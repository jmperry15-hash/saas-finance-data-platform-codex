-- Intentionally WRONG calculation alongside the correct one.
-- Each employee-month matches several expense GL lines in that department-month.
-- Payroll is therefore repeated once for each matching GL line.
SELECT
    (SELECT SUM(personnel_cost_cents) / 100.0
     FROM workday_employee_monthly
     WHERE department_id = 'D02' AND month = '2026-09-01') AS correct_payroll_usd,
    SUM(p.personnel_cost_cents) / 100.0 AS WRONG_joined_payroll_usd,
    COUNT(*) AS joined_rows,
    COUNT(DISTINCT p.employee_id) AS distinct_employees
FROM workday_employee_monthly AS p
JOIN netsuite_gl_lines AS g
  ON p.department_id = g.department_id AND p.month = g.month
JOIN netsuite_accounts AS a ON g.account_id = a.account_id
WHERE p.department_id = 'D02'
  AND p.month = '2026-09-01'
  AND a.account_type = 'Expense';
