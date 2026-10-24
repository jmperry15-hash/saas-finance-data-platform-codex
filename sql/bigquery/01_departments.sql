-- Replace YOUR_PROJECT_ID with the actual unbilled Sandbox project ID.
-- Run only after uploading the departments CSV to raw_shared.departments.
-- Inspect the query's estimated bytes before clicking Run.
SELECT department_id, department_name, function
FROM `YOUR_PROJECT_ID.raw_shared.departments`
ORDER BY department_name;
