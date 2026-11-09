-- 每个 电厂 × 节点 × 网络 × 日期 的时段数，必须等于那天的 periods_in_day（普通日 48，夏令时结束日 50，开始日 46）。
-- 返回的每一行都是时段数对不上的组合：少了 = 有时段是空值被丢掉（数据缺口），多了 = 日历对不上。
with per_key as (

    select plant_code, node_id, network_code, trading_date, count(*) as actual_periods
    from {{ ref('stg_generation') }}
    group by plant_code, node_id, network_code, trading_date

),

calendar as (

    select date_key, max(periods_in_day) as periods_in_day
    from {{ ref('dim_trading_period') }}
    group by date_key

)

select k.plant_code, k.node_id, k.network_code, k.trading_date, k.actual_periods, c.periods_in_day
from per_key as k
left join calendar as c on c.date_key = {{ nz_date_key('k.trading_date') }}
where c.periods_in_day is null or k.actual_periods <> c.periods_in_day
