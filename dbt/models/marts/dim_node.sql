-- dim_node: 每个价格节点一行，从 stg_prices 取不重复的 node_id。
--   节点身份按大写比较，node_id 存大写；只折叠大小写，不做 trim 等修正。
--   NULL、空串、全空格的 node_id 直接排除（stg_prices 上另有检查）。
--   node_key = hash(大写 node_id) 右移 1 位转 BIGINT，同一个 node_id 永远同一个键。
--   事实表加载必须用同一个表达式。
--   node_name / island / region 目前为 NULL，之后由 dbt seed 补充。

with nodes as (

    select distinct upper(node_id) as node_id
    from {{ ref('stg_prices') }}
    where node_id is not null and trim(node_id) <> ''

)

select
    {{ nz_hash_key('node_id') }} as node_key,
    node_id,
    cast(null as varchar) as node_name,
    cast(null as varchar) as island,
    cast(null as varchar) as region
from nodes
order by node_id
