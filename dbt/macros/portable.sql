{#
  portable.sql: 跨引擎差异集中在这里。模型只调用 nz_* macro，不直接写引擎专用语法。
  目前只有 duckdb__ 实现；加 Snowflake 时补 snowflake__ 实现。
  没有对应实现的引擎会报"找不到 macro"，不会悄悄用错语法。
#}

{# ---- 日期序列：返回一条 select，产出一列 trading_date ---- #}
{% macro nz_date_spine(start_date, end_date) %}
    {{ return(adapter.dispatch('nz_date_spine', 'nz_power')(start_date, end_date)) }}
{% endmacro %}

{% macro duckdb__nz_date_spine(start_date, end_date) %}
    select cast(d as date) as trading_date
    from generate_series(
        date '{{ start_date }}', date '{{ end_date }}', interval 1 day
    ) as t(d)
{% endmacro %}

{# ---- 日期 → YYYYMMDD 整数 ---- #}
{% macro nz_date_key(date_expr) %}
    {{ return(adapter.dispatch('nz_date_key', 'nz_power')(date_expr)) }}
{% endmacro %}

{% macro duckdb__nz_date_key(date_expr) %}cast(strftime({{ date_expr }}, '%Y%m%d') as integer){% endmacro %}

{# ---- ISO 星期，周一 = 1，周日 = 7 ---- #}
{% macro nz_iso_dow(date_expr) %}
    {{ return(adapter.dispatch('nz_iso_dow', 'nz_power')(date_expr)) }}
{% endmacro %}

{% macro duckdb__nz_iso_dow(date_expr) %}isodow({{ date_expr }}){% endmacro %}

{# ---- 节点代理键：hash 右移 1 位转 BIGINT。同一引擎内同一 node_id 永远同一个键；不同引擎的键值不同 ---- #}
{% macro nz_hash_key(expr) %}
    {{ return(adapter.dispatch('nz_hash_key', 'nz_power')(expr)) }}
{% endmacro %}

{% macro duckdb__nz_hash_key(expr) %}cast(hash({{ expr }}) >> 1 as bigint){% endmacro %}

{# ---- 新西兰当地时间（不带时区的墙上时钟）→ 绝对时刻 ---- #}
{% macro nz_local_to_utc(ts_expr) %}
    {{ return(adapter.dispatch('nz_local_to_utc', 'nz_power')(ts_expr)) }}
{% endmacro %}

{% macro duckdb__nz_local_to_utc(ts_expr) %}{{ ts_expr }} at time zone 'Pacific/Auckland'{% endmacro %}

{# ---- 绝对时刻 → 新西兰当地墙上时钟（不带时区） ---- #}
{% macro nz_utc_to_local(ts_expr) %}
    {{ return(adapter.dispatch('nz_utc_to_local', 'nz_power')(ts_expr)) }}
{% endmacro %}

{% macro duckdb__nz_utc_to_local(ts_expr) %}{{ ts_expr }} at time zone 'Pacific/Auckland'{% endmacro %}

{# ---- 绝对时刻 → Unix 秒 ---- #}
{% macro nz_epoch_seconds(ts_expr) %}
    {{ return(adapter.dispatch('nz_epoch_seconds', 'nz_power')(ts_expr)) }}
{% endmacro %}

{% macro duckdb__nz_epoch_seconds(ts_expr) %}epoch({{ ts_expr }}){% endmacro %}

{# ---- 时刻加 N 分钟 ---- #}
{% macro nz_add_minutes(ts_expr, minutes_expr) %}
    {{ return(adapter.dispatch('nz_add_minutes', 'nz_power')(ts_expr, minutes_expr)) }}
{% endmacro %}

{% macro duckdb__nz_add_minutes(ts_expr, minutes_expr) %}{{ ts_expr }} + to_minutes({{ minutes_expr }}){% endmacro %}

{# ---- 时段编号 1..50 的数字表，别名 p，列名 trading_period ---- #}
{% macro nz_period_numbers() %}
    {{ return(adapter.dispatch('nz_period_numbers', 'nz_power')()) }}
{% endmacro %}

{% macro duckdb__nz_period_numbers() %}range(1, 51) as p(trading_period){% endmacro %}

{# ---- 满足条件的行数 ---- #}
{% macro nz_count_if(condition) %}
    {{ return(adapter.dispatch('nz_count_if', 'nz_power')(condition)) }}
{% endmacro %}

{% macro duckdb__nz_count_if(condition) %}count(*) filter (where {{ condition }}){% endmacro %}

{# ---- 原始价格文件：返回一条 select，产出 CSV 的原始列 + source_file（文件名，不含目录） ---- #}
{% macro nz_raw_prices() %}
    {{ return(adapter.dispatch('nz_raw_prices', 'nz_power')()) }}
{% endmacro %}

{% macro duckdb__nz_raw_prices() %}
    select
        *,
        regexp_extract(filename, '([^/\\]+)$', 1) as source_file
    from read_csv(
        '{{ var("raw_prices_glob") }}',
        header = true,
        filename = true,
        types = {'PointOfConnection': 'VARCHAR'}
    )
{% endmacro %}

{# ---- 从文件名取价格版本（final / interim） ---- #}
{% macro nz_price_version(file_expr) %}
    {{ return(adapter.dispatch('nz_price_version', 'nz_power')(file_expr)) }}
{% endmacro %}

{% macro duckdb__nz_price_version(file_expr) %}regexp_extract({{ file_expr }}, '^[0-9]{8}_(final|interim)\.csv$', 1){% endmacro %}

{# ---- 文件名是否符合 YYYYMMDD_final.csv / YYYYMMDD_interim.csv ---- #}
{% macro nz_is_price_file(file_expr) %}
    {{ return(adapter.dispatch('nz_is_price_file', 'nz_power')(file_expr)) }}
{% endmacro %}

{% macro duckdb__nz_is_price_file(file_expr) %}regexp_matches({{ file_expr }}, '^[0-9]{8}_(final|interim)\.csv$'){% endmacro %}
