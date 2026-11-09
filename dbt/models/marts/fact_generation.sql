-- fact_generation: 交易日 × 时段 × 电厂 × 节点 × 网络 一行，值为 EMI 估算的发电量（kWh）。
--   整表重建（table），不做增量：数据量小；Generation_MD 是估算值、将来会被替换，增量的回看窗口暂无依据。
--   period_key 来自日期 + 时段，plant_key 来自 电厂 × 节点 × 网络（见 dim_plant）；都用 inner join，保证外键存在。
--   0 kWh 是真实值，保留。对账测试（tests/reconcile_fact_generation_vs_stg.sql）防止 inner join 静默丢行。

select
    p.period_key,
    pl.plant_key,
    cast(s.generation_kwh as bigint) as generation_kwh,
    s.source_file
from {{ ref('stg_generation') }} as s
inner join {{ ref('dim_date') }} as d
    on d.trading_date = s.trading_date
inner join {{ ref('dim_trading_period') }} as p
    on p.date_key = d.date_key
    and p.trading_period = s.trading_period
inner join {{ ref('dim_plant') }} as pl
    on pl.plant_code = s.plant_code
    and pl.node_id = s.node_id
    and pl.network_code = s.network_code
