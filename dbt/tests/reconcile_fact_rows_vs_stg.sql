-- 对账：stg_prices 行数必须等于 fact_electricity_price 行数。
-- 事实表用 inner join 建成，关联不上的行（空 node_id、不存在的时段、日期不在
-- dim_date 范围内）会被静默丢掉；两边行数不同就说明丢了数据。
-- 返回一行（含两边行数）即测试失败。
with stg as (

    select count(*) as stg_rows from {{ ref('stg_prices') }}

),

fact as (

    select count(*) as fact_rows from {{ ref('fact_electricity_price') }}

)

select stg.stg_rows, fact.fact_rows
from stg
cross join fact
where stg.stg_rows <> fact.fact_rows
