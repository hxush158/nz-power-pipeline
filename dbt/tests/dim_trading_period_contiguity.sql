-- 时段首尾相接且每个时段正好 30 分钟：下一个时段的开始 = 上一个时段的结束，
-- 跨日也一样（下一个当地午夜就是上一天最后一个时段的结束）。
with ordered as (

    select
        period_key,
        period_start_utc,
        period_end_utc,
        lag(period_end_utc) over (order by period_key) as prev_end
    from {{ ref('dim_trading_period') }}

)

select 'not_contiguous' as problem, period_key
from ordered
where prev_end is not null and period_start_utc <> prev_end

union all

select 'not_30_minutes', period_key
from ordered
where period_end_utc - period_start_utc <> interval 30 minute
