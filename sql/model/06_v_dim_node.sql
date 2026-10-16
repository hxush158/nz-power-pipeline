-- v_dim_node: dim_node 的全部列 + first_seen_date（派生，不物理存储）。
-- 依赖：dim_node(04)、fact_electricity_price(05)、dim_trading_period(02)、dim_date(01)。
-- 规则：
--   first_seen_date = 该节点在事实表中出现的最早交易日（不区分版本）。
--   如果它等于事实表里的全局最早交易日，则为 NULL（基线节点，真实起点未知）。
--   回填更早的数据后，原来非 NULL 的值会自动变回 NULL 或提前，无需手工维护。
--   只加载一天数据时，所有节点都是 NULL。

CREATE OR REPLACE VIEW v_dim_node AS
WITH fact_dates AS (
    SELECT f.node_key, d.trading_date
    FROM fact_electricity_price AS f
    INNER JOIN dim_trading_period AS p ON p.period_key = f.period_key
    INNER JOIN dim_date AS d ON d.date_key = p.date_key
),
first_seen AS (
    SELECT node_key, MIN(trading_date) AS first_date
    FROM fact_dates
    GROUP BY node_key
),
global_min AS (
    SELECT MIN(trading_date) AS min_date FROM fact_dates
)
SELECT
    n.node_key,
    n.node_id,
    n.node_name,
    n.island,
    n.region,
    CASE WHEN f.first_date > g.min_date THEN f.first_date END AS first_seen_date
FROM dim_node AS n
LEFT JOIN first_seen AS f ON f.node_key = n.node_key
CROSS JOIN global_min AS g;
