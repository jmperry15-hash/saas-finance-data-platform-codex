{% macro generate_schema_name(custom_schema_name, node) -%}
    {# One local learning target: use finance directly instead of staging_finance. #}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
