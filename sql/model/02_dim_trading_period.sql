-- dim_trading_period: 每个交易日 × 交易时段一行，覆盖 dim_date 的全部日期。
-- 依赖：先执行 01_dim_date.sql。
-- 规则：
--   交易时段按"当地午夜起实际流逝的 30 分钟"编号，不是墙上时钟。
--   period_start_utc = 当地午夜(换算为 UTC) + (trading_period - 1) * 30 分钟
--   periods_in_day   = 当地午夜到下一个当地午夜的实际时长 / 30 分钟（46 / 48 / 50）
--   period_key       = date_key * 100 + trading_period
--   period_start_local 是新西兰墙上时钟（不带时区）。夏令时结束日会出现重复，
--   所以它不能单独当键，必须配合 period_key 使用。
-- 当地时间由 DuckDB 按 Pacific/Auckland 时区规则换算，不手算偏移量。
-- 可重复执行：CREATE OR REPLACE。

CREATE OR REPLACE TABLE dim_trading_period AS
WITH day_bounds AS (
    SELECT
        date_key,
        CAST(trading_date AS TIMESTAMP) AT TIME ZONE 'Pacific/Auckland'
            AS day_start_utc,
        CAST(trading_date + 1 AS TIMESTAMP) AT TIME ZONE 'Pacific/Auckland'
            AS next_day_start_utc
    FROM dim_date
),
day_lengths AS (
    SELECT
        date_key,
        day_start_utc,
        CAST(
            (epoch(next_day_start_utc) - epoch(day_start_utc)) / 1800
            AS SMALLINT
        ) AS periods_in_day
    FROM day_bounds
),
periods AS (
    SELECT
        l.date_key,
        CAST(p.trading_period AS SMALLINT) AS trading_period,
        l.periods_in_day,
        l.day_start_utc + to_minutes((p.trading_period - 1) * 30)
            AS period_start_utc
    FROM day_lengths AS l
    CROSS JOIN range(1, 51) AS p(trading_period)
    WHERE p.trading_period <= l.periods_in_day
)
SELECT
    CAST(date_key AS BIGINT) * 100 + trading_period AS period_key,
    date_key,
    trading_period,
    period_start_utc,
    period_start_utc + to_minutes(30) AS period_end_utc,
    period_start_utc AT TIME ZONE 'Pacific/Auckland' AS period_start_local,
    periods_in_day
FROM periods;
