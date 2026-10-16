-- mart_current_price: 每个交易时段 × 节点一行的"当前最佳价格"。
-- 依赖：fact_electricity_price(05) 及三个维度。
-- 规则：
--   有 final 取 final，否则取 interim；price_version 标明选中的是哪个版本。
--   带上常用的可读列（日期、时段、本地开始时间、node_id），方便 BI 直接使用。
--   物化为表（整表重建，幂等）。
--   同键同版本重复属于上游数据错误，由事实表的主键测试发现；
--   这里只用 source_file、价格做兜底排序，保证输出确定。

CREATE OR REPLACE TABLE mart_current_price AS
SELECT
    f.period_key,
    f.node_key,
    d.trading_date,
    p.trading_period,
    p.period_start_local,
    n.node_id,
    f.price_nzd_per_mwh,
    f.price_version
FROM fact_electricity_price AS f
INNER JOIN dim_trading_period AS p ON p.period_key = f.period_key
INNER JOIN dim_date AS d ON d.date_key = p.date_key
INNER JOIN dim_node AS n ON n.node_key = f.node_key
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY f.period_key, f.node_key
    ORDER BY
        (f.price_version = 'final') DESC,
        f.source_file,
        f.price_nzd_per_mwh
) = 1
ORDER BY f.period_key, f.node_key;
