SELECT b.*, c.customer_name AS customer, c.segment, c.region
FROM `saas-finance-learning-512616.staging.stg_bookings` b
JOIN `saas-finance-learning-512616.raw_salesforce.customers` c USING (customer_id)
ORDER BY month, booking_id
