-- 用 DuckDB 回答下面这些问题。每题先写下你的预测，再运行查询：

-- 1.这个文件有哪些列？每列是什么类型？（用 DESCRIBE）
--实际
-- ┌────────────────────────────────────┐
-- │ data/raw/prices/20260920_final.csv │
-- │                                    │
-- │ TradingDate                date    │
-- │ TradingPeriod              bigint  │
-- │ PointOfConnection          varchar │
-- │ DollarsPerMegawattHour     double  │
-- └────────────────────────────────────┘
DESCRIBE 'data/raw/prices/20260920_final.csv';

-- 2.一天有多少行？有多少个不同的节点？
--预测，一天12000行，244左右节点
--实际
-- ┌─────────────┬────────────┬────────────┐
-- │ TradingDate │ total_rows │ node_count │
-- │    date     │   int64    │   int64    │
-- ├─────────────┼────────────┼────────────┤
-- │ 2026-09-20  │      11808 │        246 │
-- └─────────────┴────────────┴────────────┘

SELECT 
  TradingDate, 
  COUNT(*) AS total_rows, 
  COUNT(DISTINCT PointOfConnection) AS node_count
FROM 'data/raw/prices/20260920_final.csv'
GROUP BY TradingDate
ORDER BY TradingDate;



-- 3.交易时段的最小值和最大值是多少？2026-04-05 那天真的有 50 个时段吗？
-- 预测，最小值是1，最大值是50，2026-04-05有50个时段
-- 实际
-- ┌─────────────┬────────────┬────────────┬──────────────┐
-- │ TradingDate │ MAX_PERIOD │ MIN_PERIOD │ PERIOD_COUNT │
-- │    date     │   int64    │   int64    │    int64     │
-- ├─────────────┼────────────┼────────────┼──────────────┤
-- │ 2026-04-05  │         50 │          1 │           50 │
-- │ 2026-09-20  │         48 │          1 │           48 │
-- └─────────────┴────────────┴────────────┴──────────────┘

SELECT
    TradingDate,
    MAX(TradingPeriod) AS MAX_PERIOD,
    MIN(TradingPeriod) AS MIN_PERIOD,
    COUNT(DISTINCT TradingPeriod) AS PERIOD_COUNT
FROM 'data/raw/prices/*_final.csv'
GROUP BY TradingDate
ORDER BY TradingDate;

-- 4.价格的最小值、最大值和中位数各是多少？有没有负价格或零价格？有没有空值？
-- 预测，最小值是负数，最大值超过200，中位数是100左右，有负价格和零价格，有空值
-- 实际
-- ┌─────────────┬───────────┬───────────┬──────────────┬───────────────────────────┬──────────────────┐
-- │ TradingDate │ MIN_PRICE │ MAX_PRICE │ MEDIAN_PRICE │ ZERO_NEGATIVE_PRICE_COUNT │ NULL_PRICE_COUNT │
-- │    date     │  double   │  double   │    double    │           int64           │      int64       │
-- ├─────────────┼───────────┼───────────┼──────────────┼───────────────────────────┼──────────────────┤
-- │ 2026-04-05  │     71.74 │    253.47 │      121.725 │                         0 │                0 │
-- │ 2026-09-20  │     -0.19 │    150.75 │        15.39 │                         1 │                0 │
-- └─────────────┴───────────┴───────────┴──────────────┴───────────────────────────┴──────────────────┘
SELECT
    TradingDate,
    MIN(DollarsPerMegawattHour) AS MIN_PRICE,
    MAX(DollarsPerMegawattHour) AS MAX_PRICE,
    MEDIAN(DollarsPerMegawattHour) AS MEDIAN_PRICE,
    COUNT(*) FILTER (WHERE DollarsPerMegawattHour <= 0) AS ZERO_NEGATIVE_PRICE_COUNT,
    COUNT(*) FILTER (WHERE DollarsPerMegawattHour IS NULL) AS NULL_PRICE_COUNT
FROM 'data/raw/prices/*_final.csv'
GROUP BY TradingDate
ORDER BY TradingDate;

-- 5.开放问题： 9 月 20 日的临时价文件（文件名带 _I）在最终价发布之后还能下载到吗？如果能，和最终价相比，有多少行的价格不一样？
-- 预测：最终价发布后无法下载
--curl -L -s -o data/raw/prices/20260920_interim.csv -w "%{http_code}\n" \
--  https://www.emi.ea.govt.nz/Wholesale/Datasets/DispatchAndPricing/FinalEnergyPrices/20260920_FinalEnergyPrices_I.csv
-- 404已删除