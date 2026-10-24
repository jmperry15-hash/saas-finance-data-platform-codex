-- WHERE selects rows; ORDER BY sorts; LIMIT keeps the result small.
-- A blank termination date in the CSV becomes SQL NULL, not an empty string.
SELECT employee_id, employee_name, department_id,
       annual_base_cents / 100.0 AS reference_salary_usd
FROM workday_employees
WHERE department_id = 'D02'
  AND termination_date IS NULL
ORDER BY annual_base_cents DESC, employee_id
LIMIT 5;
