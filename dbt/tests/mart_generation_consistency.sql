-- 两张发电 MART 与事实表的一致性。返回的每一行都是对不上的指标。
--   1. mart_daily_generation 的 kWh 总和 = fact_generation 的 kWh 总和（只是分组，不丢发电）
--   2. mart_daily_generation_weighted_price 的 kWh 总和 <= mart_daily_generation（它只含有价格的部分）
--   3. 加权价与同一天同一燃料的最低、最高节点价之间合理：不低于当天最低价，不高于当天最高价
with fact_total as (
    select sum(generation_kwh) as kwh from {{ ref('fact_generation') }}
),
mart_total as (
    select sum(generation_kwh) as kwh from {{ ref('mart_daily_generation') }}
),
priced_total as (
    select sum(generation_kwh) as kwh from {{ ref('mart_daily_generation_weighted_price') }}
),
price_range as (
    select trading_date, min(min_price) as lo, max(max_price) as hi
    from {{ ref('mart_daily_price') }}
    group by trading_date
)
select 'mart_total_not_equal_fact_total' as problem, f.kwh as value_a, m.kwh as value_b
from fact_total as f cross join mart_total as m where f.kwh <> m.kwh
union all
select 'priced_total_exceeds_mart_total', p.kwh, m.kwh
from priced_total as p cross join mart_total as m where p.kwh > m.kwh
union all
select 'weighted_price_outside_daily_price_range', w.weighted_avg_price, r.lo
from {{ ref('mart_daily_generation_weighted_price') }} as w
inner join price_range as r on r.trading_date = w.trading_date
where w.weighted_avg_price is not null
  and (w.weighted_avg_price < r.lo or w.weighted_avg_price > r.hi)
