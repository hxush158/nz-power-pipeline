-- dim_node: 每个价格节点一行，从 stg_prices 取不重复的 node_id。
-- 依赖：stg_prices（03_stg_prices.sql，或测试里手工造的同结构表）。
-- 规则：
--   节点身份按大写比较：aby0111 与 ABY0111 是同一个节点，node_id 存大写形式。
--   只折叠大小写，不做 TRIM 等其他修正；带前导空格的值是另一个值，原样保留，
--   由 stg_prices 上的检查去发现。
--   NULL、空字符串、全空格的 node_id 没有身份，直接排除（不静默：
--   stg_prices 上另有"空 node_id 行数必须为 0"的检查）。
--   node_key = hash(大写 node_id) 右移 1 位转有符号 BIGINT：同一个 node_id
--   永远得到同一个 node_key，可整表重建。事实表加载必须用同一个表达式。
--   node_name / island / region 目前为 NULL，之后由参考数据（dbt seed）补充。
--   first_seen_date 不在本表，事实表完成后做成派生视图。
-- 可重复执行：CREATE OR REPLACE，按 node_id 排序保证输出确定。

CREATE OR REPLACE TABLE dim_node AS
WITH nodes AS (
    SELECT DISTINCT upper(node_id) AS node_id
    FROM stg_prices
    WHERE node_id IS NOT NULL AND trim(node_id) <> ''
)
SELECT
    CAST(hash(node_id) >> 1 AS BIGINT) AS node_key,
    node_id,
    CAST(NULL AS VARCHAR) AS node_name,
    CAST(NULL AS VARCHAR) AS island,
    CAST(NULL AS VARCHAR) AS region
FROM nodes
ORDER BY node_id;
