-- CASE applies different signs to revenue and expense.
-- This is operating profit for our simplified scenario, not GAAP net income.
SELECT g.month,
       SUM(CASE WHEN a.account_type = 'Revenue'
                THEN g.credit_cents - g.debit_cents ELSE 0 END) / 100.0 AS revenue_usd,
       SUM(CASE WHEN a.account_type = 'Expense'
                THEN g.debit_cents - g.credit_cents ELSE 0 END) / 100.0 AS expense_usd,
       SUM(g.credit_cents - g.debit_cents) / 100.0 AS operating_profit_usd
FROM netsuite_gl_lines AS g
JOIN netsuite_accounts AS a ON g.account_id = a.account_id
WHERE a.account_type IN ('Revenue', 'Expense')
GROUP BY g.month
ORDER BY g.month;
