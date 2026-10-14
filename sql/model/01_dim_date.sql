-- dim_date: 每个日历日一行，预生成 2020-01-01 ~ 2030-12-31（含首尾）。
-- 规则：
--   date_key     INTEGER，YYYYMMDD
--   day_of_week  1-7，周一 = 1（ISO）
--   is_weekend   day_of_week IN (6, 7)；不含新西兰公共假日
--   quarter      日历季度（1-3 月 = 1），不是新西兰财年
-- 可重复执行：CREATE OR REPLACE。

CREATE OR REPLACE TABLE dim_date AS
WITH days AS (
    SELECT CAST(d AS DATE) AS trading_date
    FROM generate_series(
        DATE '2020-01-01', DATE '2030-12-31', INTERVAL 1 DAY
    ) AS t(d)
)
SELECT
    CAST(strftime(trading_date, '%Y%m%d') AS INTEGER) AS date_key,
    trading_date,
    CAST(year(trading_date) AS SMALLINT) AS year,
    CAST(month(trading_date) AS SMALLINT) AS month,
    CAST(quarter(trading_date) AS SMALLINT) AS quarter,
    CAST(isodow(trading_date) AS SMALLINT) AS day_of_week,
    isodow(trading_date) IN (6, 7) AS is_weekend
FROM days;
