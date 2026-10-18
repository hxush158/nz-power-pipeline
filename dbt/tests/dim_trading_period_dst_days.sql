-- 夏令时切换日的时段数检查。
--   2026-04-05（夏令时结束）必须是 50 个时段
--   2026-09-27（夏令时开始）必须是 46 个时段
--   2020-01-01 ~ 2030-12-31 里 46 个时段的日子正好 11 天，50 个时段的日子正好 11 天
-- 每一个不满足的检查返回一行，check_name 说明是哪一个。
with per_day as (

    select date_key, count(*) as periods
    from {{ ref('dim_trading_period') }}
    group by date_key

),

checks as (

    select
        '2026-04-05 应为 50 个时段' as check_name,
        (select periods from per_day where date_key = 20260405) as actual,
        50 as expected

    union all

    select
        '2026-09-27 应为 46 个时段',
        (select periods from per_day where date_key = 20260927),
        46

    union all

    select
        '46 个时段的日子应为 11 天',
        (select count(*) from per_day where periods = 46),
        11

    union all

    select
        '50 个时段的日子应为 11 天',
        (select count(*) from per_day where periods = 50),
        11

)

select check_name, actual, expected
from checks
where actual is distinct from expected
