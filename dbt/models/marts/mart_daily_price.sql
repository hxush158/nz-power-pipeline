-- mart_daily_price: 每个交易日 × 节点一行的日汇总，基于 mart_current_price。
--   所有时段都是 30 分钟，简单平均等于时间加权。
--   avg_price 四舍五入保留 2 位，恰好在中间时远离零进位；用整数"分"运算（macro nz_avg_price_2dp），
--   DuckDB 与 Snowflake 逐行一致。
--   interim_period_count = 当天用临时价的时段数，用来判断日均价是否已定稿。

-- 对外暴露的三张表之一：放在 MART schema（ChemQ 只读用户可见），其余 dim/fact 在 CORE。
{{ config(schema='MART') }}

select
    trading_date,
    node_key,
    node_id,
    {{ nz_avg_price_2dp('price_nzd_per_mwh') }} as avg_price,
    min(price_nzd_per_mwh) as min_price,
    max(price_nzd_per_mwh) as max_price,
    count(*) as period_count,
    {{ nz_count_if("price_version = 'interim'") }} as interim_period_count
from {{ ref('mart_current_price') }}
group by trading_date, node_key, node_id
order by trading_date, node_id
