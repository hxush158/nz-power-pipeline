-- mart_daily_price: 每个交易日 × 节点一行的日汇总，基于 mart_current_price。
--   所有时段都是 30 分钟，简单平均等于时间加权。
--   avg_price 四舍五入保留 2 位。
--   interim_period_count = 当天用临时价的时段数，用来判断日均价是否已定稿。

select
    trading_date,
    node_key,
    node_id,
    cast(round(avg(price_nzd_per_mwh), 2) as decimal(18, 2)) as avg_price,
    min(price_nzd_per_mwh) as min_price,
    max(price_nzd_per_mwh) as max_price,
    count(*) as period_count,
    count(*) filter (where price_version = 'interim') as interim_period_count
from {{ ref('mart_current_price') }}
group by trading_date, node_key, node_id
order by trading_date, node_id
