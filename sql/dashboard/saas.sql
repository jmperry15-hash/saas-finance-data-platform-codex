SELECT m.month, m.customer_id, c.customer_name AS customer, c.segment, c.region,
       m.mrr_cents, m.arr_cents, IF(m.mrr_cents > 0, 1, 0) AS active_customers
FROM `saas-finance-learning-512616.staging.stg_customer_monthly` m
JOIN `saas-finance-learning-512616.raw_salesforce.customers` c USING (customer_id)
ORDER BY month, customer_id
