-- mart_daily_price: 每个交易日 × 节点一行的日汇总，基于 mart_current_price。
-- 依赖：mart_current_price(07)。
-- 规则：
--   所有交易时段都是 30 分钟（夏令时日只是时段数为 46/50），所以简单平均就等于
--   按时间加权，不需要加权。
--   avg_price 四舍五入保留 2 位，与原始价格一致。
--   interim_period_count = 当天用的是临时价的时段数，用来判断日均价是否已最终定稿。

CREATE OR REPLACE TABLE mart_daily_price AS
SELECT
    trading_date,
    node_key,
    node_id,
    CAST(ROUND(AVG(price_nzd_per_mwh), 2) AS DECIMAL(18, 2)) AS avg_price,
    MIN(price_nzd_per_mwh) AS min_price,
    MAX(price_nzd_per_mwh) AS max_price,
    COUNT(*) AS period_count,
    COUNT(*) FILTER (WHERE price_version = 'interim') AS interim_period_count
FROM mart_current_price
GROUP BY trading_date, node_key, node_id
ORDER BY trading_date, node_id;
