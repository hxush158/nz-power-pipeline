-- 对账：事实表的行数和 kWh 总和必须等于 stg_generation（inner join 不能静默丢行）。
-- 返回的每一行都是对不上的指标。
with s as (
    select count(*) as n, sum(generation_kwh) as kwh from {{ ref('stg_generation') }}
),
f as (
    select count(*) as n, sum(generation_kwh) as kwh from {{ ref('fact_generation') }}
)
select 'row_count_mismatch' as problem, s.n as stg_value, f.n as fact_value
from s cross join f where s.n <> f.n
union all
select 'kwh_sum_mismatch', s.kwh, f.kwh
from s cross join f where s.kwh <> f.kwh
