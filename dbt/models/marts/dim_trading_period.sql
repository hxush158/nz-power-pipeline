-- dim_trading_period: 每个交易日 × 交易时段一行，覆盖 dim_date 的全部日期。
--   时段按"当地午夜起实际流逝的 30 分钟"编号（46 / 48 / 50 个）。
--   period_start_utc = 当地午夜(换算为 UTC) + (trading_period - 1) * 30 分钟
--   period_key       = date_key * 100 + trading_period
--   period_start_local 是墙上时钟（不带时区），夏令时结束日会重复，不能单独当键。
--   当地时间由数据库按 Pacific/Auckland 规则换算（见 macros/portable.sql），不手算偏移量。

with day_bounds as (

    select
        date_key,
        {{ nz_local_to_utc('cast(trading_date as timestamp)') }}
            as day_start_utc,
        {{ nz_local_to_utc('cast(trading_date + 1 as timestamp)') }}
            as next_day_start_utc
    from {{ ref('dim_date') }}

),

day_lengths as (

    select
        date_key,
        day_start_utc,
        cast(
            ({{ nz_epoch_seconds('next_day_start_utc') }} - {{ nz_epoch_seconds('day_start_utc') }}) / 1800
            as smallint
        ) as periods_in_day
    from day_bounds

),

periods as (

    select
        l.date_key,
        cast(p.trading_period as smallint) as trading_period,
        l.periods_in_day,
        {{ nz_add_minutes('l.day_start_utc', '(p.trading_period - 1) * 30') }}
            as period_start_utc
    from day_lengths as l
    cross join {{ nz_period_numbers() }}
    where p.trading_period <= l.periods_in_day

)

select
    cast(date_key as bigint) * 100 + trading_period as period_key,
    date_key,
    trading_period,
    period_start_utc,
    {{ nz_add_minutes('period_start_utc', '30') }} as period_end_utc,
    {{ nz_utc_to_local('period_start_utc') }} as period_start_local,
    periods_in_day
from periods
