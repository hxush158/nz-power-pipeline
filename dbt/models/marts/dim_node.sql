-- dim_node: 每个价格节点一行，从 stg_prices 取不重复的 node_id。
--   节点身份按大写比较，node_id 存大写；只折叠大小写，不做 trim 等修正。
--   NULL、空串、全空格的 node_id 直接排除（stg_prices 上另有检查）。
--   node_key = hash(大写 node_id) 右移 1 位转 BIGINT，同一个 node_id 永远同一个键。
--   事实表加载必须用同一个表达式。
--   node_name / island / zone / region 来自 seed node_reference（EMI Network Supply Points 快照，
--   由 src/nzpower/node_reference.py 生成）。按大写 node_id 左连接；seed 里没有的节点这些列为 NULL，
--   由 tests/dim_node_reference_coverage.sql 拦下。mapping_source 说明来源：nsp / derived_from_site / unmatched。

with nodes as (

    select distinct upper(node_id) as node_id
    from {{ ref('stg_prices') }}
    where node_id is not null and trim(node_id) <> ''

)

select
    {{ nz_hash_key('n.node_id') }} as node_key,
    n.node_id,
    r.node_name,
    r.island,
    r.zone,
    r.region,
    r.mapping_source
from nodes as n
left join {{ ref('node_reference') }} as r on upper(r.node_id) = n.node_id
order by n.node_id
