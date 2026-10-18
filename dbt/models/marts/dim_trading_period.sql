-- dim_trading_period: 每个交易日 × 交易时段一行，覆盖 dim_date 的全部日期。
--   时段按"当地午夜起实际流逝的 30 分钟"编号（46 / 48 / 50 个）。
--   period_start_utc = 当地午夜(换算为 UTC) + (trading_period - 1) * 30 分钟
--   period_key       = date_key * 100 + trading_period
--   period_start_local 是墙上时钟（不带时区），夏令时结束日会重复，不能单独当键。
--   当地时间由 DuckDB 按 Pacific/Auckland 规则换算，不手算偏移量。

with day_bounds as (

    select
        date_key,
        cast(trading_date as timestamp) at time zone 'Pacific/Auckland'
            as day_start_utc,
        cast(trading_date + 1 as timestamp) at time zone 'Pacific/Auckland'
            as next_day_start_utc
    from {{ ref('dim_date') }}

),

day_lengths as (

    select
        date_key,
        day_start_utc,
        cast(
            (epoch(next_day_start_utc) - epoch(day_start_utc)) / 1800
            as smallint
        ) as periods_in_day
    from day_bounds

),

periods as (

    select
        l.date_key,
        cast(p.trading_period as smallint) as trading_period,
        l.periods_in_day,
        l.day_start_utc + to_minutes((p.trading_period - 1) * 30)
            as period_start_utc
    from day_lengths as l
    cross join range(1, 51) as p(trading_period)
    where p.trading_period <= l.periods_in_day

)

select
    cast(date_key as bigint) * 100 + trading_period as period_key,
    date_key,
    trading_period,
    period_start_utc,
    period_start_utc + to_minutes(30) as period_end_utc,
    period_start_utc at time zone 'Pacific/Auckland' as period_start_local,
    periods_in_day
from periods
