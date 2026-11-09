-- mart_daily_generation: 每个交易日 × 岛 × 分区 × 燃料 一行的发电量汇总，基于 fact_generation。
--   generation_kwh 是 EMI 估算的发电量（kWh），不是电厂自己报的数。
--   plant_count 按 plant_code 去重：同一电厂在多个节点或两个网络出现，只算 1 个。
--   不在价格节点里的电厂（如 WPG0331）仍然计入，它们的 island 和 zone 为 NULL（来自 dim_plant）。
--   这张表不涉及价格；价格相关的指标在 mart_daily_generation_weighted_price。

-- 对外暴露的表：放在 MART schema（ChemQ 只读用户可见），其余 dim/fact 在 CORE。
{{ config(schema='MART') }}

select
    d.trading_date,
    pl.island,
    pl.zone,
    pl.fuel,
    sum(f.generation_kwh) as generation_kwh,
    count(distinct pl.plant_code) as plant_count
from {{ ref('fact_generation') }} as f
inner join {{ ref('dim_plant') }} as pl on pl.plant_key = f.plant_key
inner join {{ ref('dim_trading_period') }} as p on p.period_key = f.period_key
inner join {{ ref('dim_date') }} as d on d.date_key = p.date_key
group by d.trading_date, pl.island, pl.zone, pl.fuel
order by d.trading_date, pl.island, pl.zone, pl.fuel
