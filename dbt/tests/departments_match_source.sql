-- A data test passes when its SELECT returns zero failing rows.
-- ref() tells dbt this test depends on the staging model.
with expected as (
    select
        trim(department_id) as department_id,
        trim(department_name) as department_name,
        trim(`function`) as department_function
    from {{ source('shared', 'departments') }}
), actual as (
    select department_id, department_name, department_function
    from {{ ref('stg_departments') }}
), missing as (
    select * from expected
    except distinct
    select * from actual
), unexpected as (
    select * from actual
    except distinct
    select * from expected
)
select * from missing
union all
select * from unexpected
