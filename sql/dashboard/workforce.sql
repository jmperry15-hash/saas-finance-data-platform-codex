SELECT w.month, w.department_id, w.department_name AS department, d.department_function AS `function`,
       w.headcount, w.fte_basis_points, w.base_pay_cents, w.bonus_cents,
       w.benefits_cents, w.personnel_cost_cents
FROM `saas-finance-learning-512616.finance.rpt_workforce_monthly` w
JOIN `saas-finance-learning-512616.staging.stg_departments` d USING (department_id)
ORDER BY month, department_id
