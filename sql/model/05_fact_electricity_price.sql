-- fact_electricity_price: 每个交易日 × 时段 × 节点 × 版本（interim/final）一行。
-- 依赖：stg_prices(03)、dim_date(01)、dim_trading_period(02)、dim_node(04)。
-- 规则：
--   整表重建（CREATE OR REPLACE），由 stg_prices 全量构建，天然幂等：重复加载
--   不会产生重复行；interim 与 final 是不同版本，两行并存。
--   period_key / node_key 通过 INNER JOIN 维度表取得，保证外键一定存在。
--   node 按大写 node_id 关联（与 dim_node 一致）。
--   price_nzd_per_mwh 为 DECIMAL(18,2)（源数据最多 2 位小数）。
--   本阶段没有 loaded_at：整表重建时它没有审计意义；来源追溯用 source_file。
--   增量加载与 loaded_at 留到 dbt incremental model。
--   不去重：同一键同一版本重复（例如 aby0111 与 ABY0111 折叠后碰撞）会原样保留，
--   由主键唯一性测试发现。
--   关联不上的行（空 node_id、不存在的时段等）会被 INNER JOIN 排除；
--   必须有对账测试：stg_prices 行数 = 事实表行数，防止静默丢数据。

CREATE OR REPLACE TABLE fact_electricity_price AS
SELECT
    p.period_key,
    n.node_key,
    s.price_version,
    CAST(s.price_nzd_per_mwh AS DECIMAL(18, 2)) AS price_nzd_per_mwh,
    s.source_file
FROM stg_prices AS s
INNER JOIN dim_date AS d
    ON d.trading_date = s.trading_date
INNER JOIN dim_trading_period AS p
    ON p.date_key = d.date_key
    AND p.trading_period = s.trading_period
INNER JOIN dim_node AS n
    ON n.node_id = upper(s.node_id)
ORDER BY p.period_key, n.node_key, s.price_version;
