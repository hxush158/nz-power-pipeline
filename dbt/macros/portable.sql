{#
  portable.sql: 跨引擎差异集中在这里。模型只调用 nz_* macro，不直接写引擎专用语法。
  实现：duckdb__（本地开发）、snowflake__（云上）。每个 macro 的 DuckDB 与 Snowflake 写法紧挨着放；
  差异的原因记在 docs/snowflake_porting_notes.md。
  没有对应实现的引擎会报"找不到 macro"，不会悄悄用错语法。
  约定：Snowflake 上"绝对时刻"用 TIMESTAMP_NTZ 存 UTC 墙上时钟（不用 LTZ，避免受账号时区影响）；
  DuckDB 上用 TIMESTAMPTZ。两边表示的是同一个时刻。
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

{# Snowflake 没有 generate_series：用 generator 按天数生成连续整数再加到起始日。rowcount 必须是常量，所以在 Jinja 里算好。 #}
{% macro snowflake__nz_date_spine(start_date, end_date) %}
    {%- set n_days = (modules.datetime.date.fromisoformat(end_date) - modules.datetime.date.fromisoformat(start_date)).days + 1 -%}
    select dateadd(day, row_number() over (order by seq4()) - 1, date '{{ start_date }}') as trading_date
    from table(generator(rowcount => {{ n_days }}))
{% endmacro %}

{# ---- 日期 → YYYYMMDD 整数 ---- #}
{% macro nz_date_key(date_expr) %}
    {{ return(adapter.dispatch('nz_date_key', 'nz_power')(date_expr)) }}
{% endmacro %}

{% macro duckdb__nz_date_key(date_expr) %}cast(strftime({{ date_expr }}, '%Y%m%d') as integer){% endmacro %}
{% macro snowflake__nz_date_key(date_expr) %}cast(to_char({{ date_expr }}, 'YYYYMMDD') as integer){% endmacro %}

{# ---- ISO 星期，周一 = 1，周日 = 7 ---- #}
{% macro nz_iso_dow(date_expr) %}
    {{ return(adapter.dispatch('nz_iso_dow', 'nz_power')(date_expr)) }}
{% endmacro %}

{% macro duckdb__nz_iso_dow(date_expr) %}isodow({{ date_expr }}){% endmacro %}
{% macro snowflake__nz_iso_dow(date_expr) %}dayofweekiso({{ date_expr }}){% endmacro %}

{# ---- 节点代理键：hash 右移 1 位转 BIGINT。同一引擎内同一 node_id 永远同一个键；不同引擎的键值不同 ---- #}
{% macro nz_hash_key(expr) %}
    {{ return(adapter.dispatch('nz_hash_key', 'nz_power')(expr)) }}
{% endmacro %}

{% macro duckdb__nz_hash_key(expr) %}cast(hash({{ expr }}) >> 1 as bigint){% endmacro %}
{# DuckDB 的 hash 是无符号 64 位，右移 1 位才装得进 BIGINT；Snowflake 的 HASH 本来就是有符号 64 位，不需要移位。 #}
{% macro snowflake__nz_hash_key(expr) %}cast(hash({{ expr }}) as bigint){% endmacro %}

{# ---- 新西兰当地时间（不带时区的墙上时钟）→ 绝对时刻 ---- #}
{% macro nz_local_to_utc(ts_expr) %}
    {{ return(adapter.dispatch('nz_local_to_utc', 'nz_power')(ts_expr)) }}
{% endmacro %}

{% macro duckdb__nz_local_to_utc(ts_expr) %}{{ ts_expr }} at time zone 'Pacific/Auckland'{% endmacro %}
{# 输入是不带时区的当地墙上时钟（TIMESTAMP_NTZ）；输出是 UTC 墙上时钟（TIMESTAMP_NTZ）。 #}
{% macro snowflake__nz_local_to_utc(ts_expr) %}convert_timezone('Pacific/Auckland', 'UTC', {{ ts_expr }}){% endmacro %}

{# ---- 绝对时刻 → 新西兰当地墙上时钟（不带时区） ---- #}
{% macro nz_utc_to_local(ts_expr) %}
    {{ return(adapter.dispatch('nz_utc_to_local', 'nz_power')(ts_expr)) }}
{% endmacro %}

{% macro duckdb__nz_utc_to_local(ts_expr) %}{{ ts_expr }} at time zone 'Pacific/Auckland'{% endmacro %}
{% macro snowflake__nz_utc_to_local(ts_expr) %}convert_timezone('UTC', 'Pacific/Auckland', {{ ts_expr }}){% endmacro %}

{# ---- 绝对时刻 → Unix 秒 ---- #}
{% macro nz_epoch_seconds(ts_expr) %}
    {{ return(adapter.dispatch('nz_epoch_seconds', 'nz_power')(ts_expr)) }}
{% endmacro %}

{% macro duckdb__nz_epoch_seconds(ts_expr) %}epoch({{ ts_expr }}){% endmacro %}
{# 输入按 UTC 墙上时钟理解 #}
{% macro snowflake__nz_epoch_seconds(ts_expr) %}date_part(epoch_second, {{ ts_expr }}){% endmacro %}

{# ---- 时刻加 N 分钟 ---- #}
{% macro nz_add_minutes(ts_expr, minutes_expr) %}
    {{ return(adapter.dispatch('nz_add_minutes', 'nz_power')(ts_expr, minutes_expr)) }}
{% endmacro %}

{% macro duckdb__nz_add_minutes(ts_expr, minutes_expr) %}{{ ts_expr }} + to_minutes({{ minutes_expr }}){% endmacro %}
{% macro snowflake__nz_add_minutes(ts_expr, minutes_expr) %}dateadd(minute, {{ minutes_expr }}, {{ ts_expr }}){% endmacro %}

{# ---- 时段编号 1..50 的数字表，别名 p，列名 trading_period ---- #}
{% macro nz_period_numbers() %}
    {{ return(adapter.dispatch('nz_period_numbers', 'nz_power')()) }}
{% endmacro %}

{% macro duckdb__nz_period_numbers() %}range(1, 51) as p(trading_period){% endmacro %}
{% macro snowflake__nz_period_numbers() %}(select row_number() over (order by seq4()) as trading_period from table(generator(rowcount => 50))) as p{% endmacro %}

{# ---- 满足条件的行数 ---- #}
{% macro nz_count_if(condition) %}
    {{ return(adapter.dispatch('nz_count_if', 'nz_power')(condition)) }}
{% endmacro %}

{% macro duckdb__nz_count_if(condition) %}count(*) filter (where {{ condition }}){% endmacro %}
{% macro snowflake__nz_count_if(condition) %}count_if({{ condition }}){% endmacro %}

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

{# Snowflake：数据已经由 COPY INTO 装进 RAW 表（sql/snowflake/03_copy_into.sql），source_file 是装载时写入的文件名。
   RAW 表四列都是字符串，和 DuckDB 的 read_csv(PointOfConnection 读成 VARCHAR) 等价；类型转换在 stg_prices 里做。 #}
{% macro snowflake__nz_raw_prices() %}
    select
        TRADINGDATE as TradingDate,
        TRADINGPERIOD as TradingPeriod,
        POINTOFCONNECTION as PointOfConnection,
        DOLLARSPERMEGAWATTHOUR as DollarsPerMegawattHour,
        SOURCE_FILE as source_file
    from {{ source('raw', 'prices_raw') }}
{% endmacro %}

{# ---- 从文件名取价格版本（final / interim） ---- #}
{% macro nz_price_version(file_expr) %}
    {{ return(adapter.dispatch('nz_price_version', 'nz_power')(file_expr)) }}
{% endmacro %}

{% macro duckdb__nz_price_version(file_expr) %}regexp_extract({{ file_expr }}, '^[0-9]{8}_(final|interim)\.csv$', 1){% endmacro %}
{# Snowflake 的字符串里反斜杠是转义符，所以用 [.] 代替 \. ；'e' 表示提取，最后的 1 是第 1 个括号组 #}
{% macro snowflake__nz_price_version(file_expr) %}regexp_substr({{ file_expr }}, '^[0-9]{8}_(final|interim)[.]csv$', 1, 1, 'e', 1){% endmacro %}

{# ---- 文件名是否符合 YYYYMMDD_final.csv / YYYYMMDD_interim.csv ---- #}
{% macro nz_is_price_file(file_expr) %}
    {{ return(adapter.dispatch('nz_is_price_file', 'nz_power')(file_expr)) }}
{% endmacro %}

{% macro duckdb__nz_is_price_file(file_expr) %}regexp_matches({{ file_expr }}, '^[0-9]{8}_(final|interim)\.csv$'){% endmacro %}
{% macro snowflake__nz_is_price_file(file_expr) %}regexp_like({{ file_expr }}, '^[0-9]{8}_(final|interim)[.]csv$'){% endmacro %}

{# ---- 以下两个 macro 是为移植测试新增的 ---- #}

{# ---- 两个日期相差的天数（to - from） ---- #}
{% macro nz_date_diff_days(from_expr, to_expr) %}
    {{ return(adapter.dispatch('nz_date_diff_days', 'nz_power')(from_expr, to_expr)) }}
{% endmacro %}

{% macro duckdb__nz_date_diff_days(from_expr, to_expr) %}date_diff('day', {{ from_expr }}, {{ to_expr }}){% endmacro %}
{% macro snowflake__nz_date_diff_days(from_expr, to_expr) %}datediff(day, {{ from_expr }}, {{ to_expr }}){% endmacro %}

{# ---- UTC 时刻的字面量，参数形如 '2026-10-12 11:00:00'（UTC） ---- #}
{% macro nz_utc_literal(text) %}
    {{ return(adapter.dispatch('nz_utc_literal', 'nz_power')(text)) }}
{% endmacro %}

{% macro duckdb__nz_utc_literal(text) %}timestamptz '{{ text }}+00'{% endmacro %}
{% macro snowflake__nz_utc_literal(text) %}to_timestamp_ntz('{{ text }}'){% endmacro %}

{# ---- 价格的平均值，四舍五入到 2 位小数（decimal(18,2)），全程精确运算，两个引擎结果逐行一致 ----
   规则：四舍五入，恰好在中间时远离零进位（0.005 → 0.01，-0.005 → -0.01），与 Snowflake 的 ROUND 相同。
   做法：价格先换成整数"分"求和，平均数的舍入用整数运算：
        分数 = sign(S) * floor((2*|S| + n) / (2*n))      S = 分的总和，n = 行数
   为什么不用 round(avg(x), 2)：DuckDB 对 DECIMAL 求 avg 返回 DOUBLE，x.xx5 在二进制里不精确，进位不稳定。
   为什么 DuckDB 用 //：DuckDB 里 / 是浮点除法，// 才是整数除法。Snowflake 的 / 对整数给出精确小数，floor 后等价
   （商的小数部分与整数的距离至少 1/(2n)，远大于小数位截断的误差）。
   最后先转 bigint 再乘 0.01：避免 hugeint 乘 decimal 超过 38 位后悄悄变成 DOUBLE。
   只能放在 group by 的聚合查询里（里面用了 sum / count）。 #}
{% macro nz_avg_price_2dp(price_expr) %}
    {{ return(adapter.dispatch('nz_avg_price_2dp', 'nz_power')(price_expr)) }}
{% endmacro %}

{% macro duckdb__nz_avg_price_2dp(price_expr) -%}
cast(
    cast(
        sign(sum(cast({{ price_expr }} * 100 as bigint)))
        * ((2 * abs(sum(cast({{ price_expr }} * 100 as bigint))) + count(*)) // (2 * count(*)))
    as bigint) * 0.01
as decimal(18, 2))
{%- endmacro %}

{% macro snowflake__nz_avg_price_2dp(price_expr) -%}
cast(
    cast(
        sign(sum(cast({{ price_expr }} * 100 as bigint)))
        * floor((2 * abs(sum(cast({{ price_expr }} * 100 as bigint))) + count(*)) / (2 * count(*)))
    as bigint) * 0.01
as decimal(18, 2))
{%- endmacro %}


{# ---- 原始发电文件（EMI Generation_MD，宽表）：返回一条 select，产出小写列名
        site_code, poc_code, nwk_code, gen_code, fuel_code, tech_code, trading_date, tp1..tp50, source_file；全部是字符串。 ---- #}
{% macro nz_raw_generation() %}
    {{ return(adapter.dispatch('nz_raw_generation', 'nz_power')()) }}
{% endmacro %}

{% macro duckdb__nz_raw_generation() %}
    select
        Site_Code as site_code, POC_Code as poc_code, Nwk_Code as nwk_code, Gen_Code as gen_code,
        Fuel_Code as fuel_code, Tech_Code as tech_code, Trading_Date as trading_date,
        {% for i in range(1, 51) -%}
        TP{{ i }} as tp{{ i }},
        {% endfor -%}
        regexp_extract(filename, '([^/\\]+)$', 1) as source_file
    from read_csv(
        '{{ var("raw_generation_glob") }}',
        header = true,
        filename = true,
        all_varchar = true
    )
{% endmacro %}

{% macro snowflake__nz_raw_generation() %}
    select
        SITE_CODE as site_code, POC_CODE as poc_code, NWK_CODE as nwk_code, GEN_CODE as gen_code,
        FUEL_CODE as fuel_code, TECH_CODE as tech_code, TRADING_DATE as trading_date,
        TP1 as tp1,
        TP2 as tp2,
        TP3 as tp3,
        TP4 as tp4,
        TP5 as tp5,
        TP6 as tp6,
        TP7 as tp7,
        TP8 as tp8,
        TP9 as tp9,
        TP10 as tp10,
        TP11 as tp11,
        TP12 as tp12,
        TP13 as tp13,
        TP14 as tp14,
        TP15 as tp15,
        TP16 as tp16,
        TP17 as tp17,
        TP18 as tp18,
        TP19 as tp19,
        TP20 as tp20,
        TP21 as tp21,
        TP22 as tp22,
        TP23 as tp23,
        TP24 as tp24,
        TP25 as tp25,
        TP26 as tp26,
        TP27 as tp27,
        TP28 as tp28,
        TP29 as tp29,
        TP30 as tp30,
        TP31 as tp31,
        TP32 as tp32,
        TP33 as tp33,
        TP34 as tp34,
        TP35 as tp35,
        TP36 as tp36,
        TP37 as tp37,
        TP38 as tp38,
        TP39 as tp39,
        TP40 as tp40,
        TP41 as tp41,
        TP42 as tp42,
        TP43 as tp43,
        TP44 as tp44,
        TP45 as tp45,
        TP46 as tp46,
        TP47 as tp47,
        TP48 as tp48,
        TP49 as tp49,
        TP50 as tp50,
        SOURCE_FILE as source_file
    from {{ source('raw', 'generation_raw') }}
{% endmacro %}

{% macro nz_is_generation_file(file_expr) %}
    {{ return(adapter.dispatch('nz_is_generation_file', 'nz_power')(file_expr)) }}
{% endmacro %}

{% macro duckdb__nz_is_generation_file(file_expr) %}regexp_matches({{ file_expr }}, '^[0-9]{6}_Generation_MD\.csv$'){% endmacro %}
{% macro snowflake__nz_is_generation_file(file_expr) %}regexp_like({{ file_expr }}, '^[0-9]{6}_Generation_MD[.]csv$'){% endmacro %}
