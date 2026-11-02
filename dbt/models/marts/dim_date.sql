-- dim_date: 每个日历日一行，预生成 2020-01-01 ~ 2030-12-31（含首尾）。
--   date_key    INTEGER，YYYYMMDD
--   day_of_week 1-7，周一 = 1（ISO）
--   is_weekend  day_of_week in (6, 7)；不含新西兰公共假日
--   quarter     日历季度，不是新西兰财年

with days as (

    {{ nz_date_spine('2020-01-01', '2030-12-31') }}

)

select
    {{ nz_date_key('trading_date') }} as date_key,
    trading_date,
    cast(year(trading_date) as smallint) as year,
    cast(month(trading_date) as smallint) as month,
    cast(quarter(trading_date) as smallint) as quarter,
    cast({{ nz_iso_dow('trading_date') }} as smallint) as day_of_week,
    {{ nz_iso_dow('trading_date') }} in (6, 7) as is_weekend
from days
