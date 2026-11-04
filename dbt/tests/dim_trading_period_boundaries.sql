-- dim_trading_period 关键边界时段的 UTC / 本地时间检查（T1）。
-- 期望值与 docs/test_cases_dim_trading_period.xlsx 的 B 表一致：
--   NZDT = UTC+13（夏令时），NZST = UTC+12。
-- 每个不满足的检查返回一行；没有对应时段的也会返回（actual 为空）。
with expected as (

    select 20261013 as date_key, 1 as trading_period,
        {{ nz_utc_literal('2026-10-12 11:00:00') }} as start_utc,
        {{ nz_utc_literal('2026-10-12 11:30:00') }} as end_utc,
        timestamp '2026-10-13 00:00:00' as start_local
    union all
    -- 夏令时结束日 2026-04-05：共 50 个时段，最后一个是 11:30–12:00 UTC
    select 20260405, 50,
        {{ nz_utc_literal('2026-04-05 11:30:00') }},
        {{ nz_utc_literal('2026-04-05 12:00:00') }},
        timestamp '2026-04-05 23:30:00'
    union all
    -- 夏令时结束日第 5 个和第 7 个时段，本地开始时间都是 02:00（时钟回拨，重复一小时）
    select 20260405, 5,
        {{ nz_utc_literal('2026-04-04 13:00:00') }},
        {{ nz_utc_literal('2026-04-04 13:30:00') }},
        timestamp '2026-04-05 02:00:00'
    union all
    select 20260405, 7,
        {{ nz_utc_literal('2026-04-04 14:00:00') }},
        {{ nz_utc_literal('2026-04-04 14:30:00') }},
        timestamp '2026-04-05 02:00:00'
    union all
    -- 夏令时开始日 2026-09-27：共 46 个时段，最后一个是 10:30–11:00 UTC
    select 20260927, 46,
        {{ nz_utc_literal('2026-09-27 10:30:00') }},
        {{ nz_utc_literal('2026-09-27 11:00:00') }},
        timestamp '2026-09-27 23:30:00'

)

select e.date_key, e.trading_period, a.period_start_utc, e.start_utc,
    a.period_end_utc, e.end_utc, a.period_start_local, e.start_local
from expected as e
left join {{ ref('dim_trading_period') }} as a
    on a.date_key = e.date_key and a.trading_period = e.trading_period
where a.period_start_utc is distinct from e.start_utc
    or a.period_end_utc is distinct from e.end_utc
    or a.period_start_local is distinct from e.start_local
