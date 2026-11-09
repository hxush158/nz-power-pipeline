-- dim_plant: 每个 电厂 × 节点 × 网络 一行（同一电厂可在多个节点或在输电网 / 配电网两侧出现）。
--   plant_key = hash(plant_code|node_id|network_code)，与 dim_node 同一套哈希 macro，整表重建时键不变。
--   燃料代码有两套写法（Hydro / HYD 等），按 seed fuel_map 映射成统一的 fuel；映射不到时 fuel 为 NULL，
--   由 _marts.yml 里的 not_null 测试报错（行不丢）。
--   island / zone 通过 node_id 取自 dim_node；发电节点不在价格节点里时为 NULL，is_price_node = false。
--   用 select distinct 展开全部属性：同一键下属性不一致会产生重复键，由 unique 测试发现，不静默取其一。

with plants as (

    select distinct
        plant_code,
        node_id,
        network_code,
        site_code,
        fuel_code,
        tech_code
    from {{ ref('stg_generation') }}

)

select
    {{ nz_hash_key("p.plant_code || '|' || p.node_id || '|' || p.network_code") }} as plant_key,
    p.plant_code,
    p.node_id,
    p.network_code,
    p.site_code,
    p.fuel_code,
    p.tech_code,
    f.fuel,
    n.island,
    n.zone,
    n.node_id is not null as is_price_node
from plants as p
left join {{ ref('fuel_map') }} as f on f.fuel_code = p.fuel_code
left join {{ ref('dim_node') }} as n on n.node_id = p.node_id
order by p.plant_code, p.node_id, p.network_code
