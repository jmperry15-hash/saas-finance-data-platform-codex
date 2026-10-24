-- User confirmed these results in BigQuery on October 24, 2026.
-- Expected: 16,648 rows; $77,741,040.10 per side; $0 difference.
-- This is a grand-total control, not a complete P&L/payroll reconciliation.
SELECT
  COUNT(*) AS gl_line_count,
  SUM(debit_cents) / 100.0 AS total_debits,
  SUM(credit_cents) / 100.0 AS total_credits,
  SUM(debit_cents - credit_cents) / 100.0 AS difference
FROM `saas-finance-learning-512616.raw_netsuite.gl_lines`;
