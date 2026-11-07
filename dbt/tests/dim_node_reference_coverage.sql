-- 每个节点都要在参考数据里有岛；分区为空的节点必须恰好是已知缺口 KAW2201。
-- 出现别的节点 = 价格数据里来了新节点，需要重新运行 src/nzpower/node_reference.py 更新 seed。
select node_id, 'missing_island' as problem
from {{ ref('dim_node') }}
where island is null
union all
select node_id, 'unexpected_null_zone'
from {{ ref('dim_node') }}
where zone is null and node_id <> 'KAW2201'
