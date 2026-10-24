-- One output row = month + department. Only expense accounts count as spend.
-- Change the month, then try adding AND d.department_name = 'Engineering'.
SELECT g.month,
       d.department_name,
       SUM(g.debit_cents - g.credit_cents) / 100.0 AS expense_usd
FROM netsuite_gl_lines AS g
JOIN shared_departments AS d ON g.department_id = d.department_id
JOIN netsuite_accounts AS a ON g.account_id = a.account_id
WHERE a.account_type = 'Expense'
  AND g.month = '2026-09-01'
GROUP BY g.month, d.department_id, d.department_name
ORDER BY expense_usd DESC;
