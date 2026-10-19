-- dim_date 完整性：范围、连续、键与日期一致、周末标记与星期一致。
-- 每个问题返回一行，problem 说明是哪一类。
with ordered as (

    select
        trading_date,
        date_key,
        day_of_week,
        is_weekend,
        lag(trading_date) over (order by trading_date) as prev_date
    from {{ ref('dim_date') }}

)

select 'gap_or_overlap' as problem, trading_date
from ordered
where prev_date is not null and trading_date - prev_date <> 1

union all

select 'date_key_mismatch', trading_date
from ordered
where date_key <> cast(strftime(trading_date, '%Y%m%d') as integer)

union all

select 'is_weekend_mismatch', trading_date
from ordered
where is_weekend <> (day_of_week in (6, 7))

union all

select 'wrong_first_or_last_date', min(trading_date)
from ordered
having min(trading_date) <> date '2020-01-01'
    or max(trading_date) <> date '2030-12-31'
