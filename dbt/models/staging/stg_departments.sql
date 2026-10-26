-- A dbt model is a SELECT saved in a SQL file.
-- source() resolves the raw table using sources.yml.
select
    trim(department_id) as department_id,
    trim(department_name) as department_name,
    trim(`function`) as department_function
from {{ source('shared', 'departments') }}
