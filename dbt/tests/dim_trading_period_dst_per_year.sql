-- 每个日历年正好有一个 50 时段日（夏令时结束）和一个 46 时段日（夏令时开始）。
-- 返回的每一行是一个不满足的年份。
with per_day as (

    select date_key, count(*) as periods
    from {{ ref('dim_trading_period') }}
    group by date_key

)

select
    d.year,
    count(*) filter (where p.periods = 50) as days_with_50,
    count(*) filter (where p.periods = 46) as days_with_46
from per_day as p
inner join {{ ref('dim_date') }} as d on d.date_key = p.date_key
group by d.year
having count(*) filter (where p.periods = 50) <> 1
    or count(*) filter (where p.periods = 46) <> 1
