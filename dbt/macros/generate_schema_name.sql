{#
  默认的 dbt 行为是把 target.schema 和模型的 +schema 拼成 "STAGING_CORE" 这样的名字。
  这里改成：模型写了 +schema 就直接用它（STAGING / CORE / MART）；没写就用 target.schema。
  DuckDB 本地开发不分 schema，仍然全部放在 target.schema（main）里，保持原样。
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if target.type == 'snowflake' and custom_schema_name is not none -%}
        {{ custom_schema_name | trim | upper }}
    {%- else -%}
        {{ target.schema }}
    {%- endif -%}
{%- endmacro %}
