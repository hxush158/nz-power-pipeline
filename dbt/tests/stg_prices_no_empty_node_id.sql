-- stg_prices 里不能有空字符串或全是空格的 node_id。
-- YAML 里的 not_null 只抓 NULL；空串和空格会被 dim_node 排除、被事实表丢弃，
-- 所以要在这里单独拦下，返回的每一行都是问题数据。
select trading_date, trading_period, node_id, source_file
from {{ ref('stg_prices') }}
where trim(node_id) = ''
