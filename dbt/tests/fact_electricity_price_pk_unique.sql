-- 事实表主键 (period_key, node_key, price_version) 必须唯一。
-- 返回的每一行都是一个重复的键，有行返回即测试失败。
select period_key, node_key, price_version, count(*) as n
from {{ ref('fact_electricity_price') }}
group by period_key, node_key, price_version
having count(*) > 1
