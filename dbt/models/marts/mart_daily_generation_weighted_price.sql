-- mart_daily_generation_weighted_price: 每个交易日 × 岛 × 燃料 一行，按发电量加权的平均价。
--   含义：某类燃料的电平均卖在什么价（权重 = 该时段该电厂的发电量）。
--   它不是需求侧的价格（用户实际付的平均价）：我们没有需求量数据，两者不能混用。
--   价格用 mart_current_price（final 优先，没有才用 interim），按 period_key + node_id 关联。
--   同一节点同一时段的多个电厂 / 网络各自带着自己的发电量，共用该节点的价格。
--   inner join：没有价格的节点（如 WPG0331）或没有价格的时段，发电不进入这张表；
--   generation_kwh 因此是"有价格的那部分发电量"，与 mart_daily_generation 的总量会有小差距。
--   interim_generation_kwh = 其中用临时价定价的发电量，用来判断加权价是否已定稿。
--   权重之和为 0（当天全是 0 kWh）时，weighted_avg_price 为 NULL。
--   加权价用整数"分"运算（macro nz_weighted_avg_2dp），四舍五入远离零进位，两个引擎逐行一致。

-- 对外暴露的表：放在 MART schema（ChemQ 只读用户可见），其余 dim/fact 在 CORE。
{{ config(schema='MART') }}

select
    d.trading_date,
    pl.island,
    pl.fuel,
    sum(f.generation_kwh) as generation_kwh,
    sum(case when m.price_version = 'interim' then f.generation_kwh else 0 end) as interim_generation_kwh,
    {{ nz_weighted_avg_2dp(
        'sum(f.generation_kwh * cast(m.price_nzd_per_mwh * 100 as bigint))',
        'sum(f.generation_kwh)'
    ) }} as weighted_avg_price
from {{ ref('fact_generation') }} as f
inner join {{ ref('dim_plant') }} as pl on pl.plant_key = f.plant_key
inner join {{ ref('dim_trading_period') }} as p on p.period_key = f.period_key
inner join {{ ref('dim_date') }} as d on d.date_key = p.date_key
inner join {{ ref('mart_current_price') }} as m
    on m.period_key = f.period_key
    and m.node_id = pl.node_id
group by d.trading_date, pl.island, pl.fuel
order by d.trading_date, pl.island, pl.fuel
