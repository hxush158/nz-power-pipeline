-- 长表的键：电厂 × 节点 × 网络 × 日期 × 时段 必须唯一。返回的每一行都是重复的键。
-- （同一电厂在同一节点同一天可有两行，区别只在 Nwk_Code，所以网络必须在键里。）
select plant_code, node_id, network_code, trading_date, trading_period, count(*) as n
from {{ ref('stg_generation') }}
group by plant_code, node_id, network_code, trading_date, trading_period
having count(*) > 1
