-- 比较 9 月 26 日的临时价与最终价
-- 预测：same = 11800, changed = 200, only_final = 150, only_interim = 50

WITH f AS (SELECT * FROM 'data/raw/prices/20260926_final.csv'),
     i AS (SELECT * FROM 'data/raw/prices/20260926_interim.csv')
SELECT
    CASE
        WHEN f.PointOfConnection IS NULL THEN 'only_interim'
        WHEN i.PointOfConnection IS NULL THEN 'only_final'
        WHEN f.DollarsPerMegawattHour = i.DollarsPerMegawattHour THEN 'same'
        ELSE 'changed'
    END AS status,
    COUNT(*) AS row_count
FROM f
FULL OUTER JOIN i
  ON f.TradingDate  = i.TradingDate
  AND f.TradingPeriod = i.TradingPeriod 
  AND f.PointOfConnection = i.PointOfConnection
GROUP BY status
ORDER BY status;

-- 实际结果：
--Total rows: 11808, no changed, only_final = 0, only_interim = 0

WITH f AS (SELECT * FROM 'data/raw/prices/20260926_final.csv'),
     i AS (SELECT * FROM 'data/raw/prices/20260926_interim.csv')
SELECT
    f.TradingDate,
    f.TradingPeriod,
    f.PointOfConnection,
    i.DollarsPerMegawattHour AS interim_price,
    f.DollarsPerMegawattHour AS final_price,
    ABS(f.DollarsPerMegawattHour - i.DollarsPerMegawattHour) AS price_diff
FROM f
JOIN i
  ON f.TradingDate = i.TradingDate
 AND f.TradingPeriod = i.TradingPeriod
 AND f.PointOfConnection = i.PointOfConnection
WHERE f.DollarsPerMegawattHour <> i.DollarsPerMegawattHour
ORDER BY price_diff DESC
LIMIT 10;