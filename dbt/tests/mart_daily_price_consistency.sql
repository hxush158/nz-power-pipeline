-- mart_daily_price：同一天同一节点只能有一行；period_count 之和必须等于
-- mart_current_price 的行数（日汇总没有丢也没有重复计算时段）。
select 'duplicate_day_node' as problem, count(*) as detail
from (
    select trading_date, node_key
    from {{ ref('mart_daily_price') }}
    group by trading_date, node_key
    having count(*) > 1
)
having count(*) > 0

union all

select 'period_count_sum_mismatch', 1
where (select sum(period_count) from {{ ref('mart_daily_price') }})
    <> (select count(*) from {{ ref('mart_current_price') }})
