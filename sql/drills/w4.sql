-- ---------------------------------------------------------------------
-- 练习 1: 找出每个节点每天的最高价和对应的时段（窗口函数）
-- ---------------------------------------------------------------------

SELECT
    TradingDate,
    PointOfConnection,
    TradingPeriod AS MaxPricePeriod,
    DollarsPerMegawattHour AS MaxPrice
FROM read_csv_auto('data/raw/prices/20260920_final.csv')
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY PointOfConnection, TradingDate
    ORDER BY DollarsPerMegawattHour DESC, TradingPeriod ASC
) = 1
ORDER BY TradingDate, PointOfConnection;

-- ---------------------------------------------------------------------
-- 练习 2: 每个节点相邻时段的价格变化，找出涨幅最大的 10 个（LAG）
-- ---------------------------------------------------------------------

WITH price_changes AS (
    SELECT
        TradingDate,
        TradingPeriod,
        PointOfConnection,
        DollarsPerMegawattHour AS Price,

        LAG(Price) OVER (
            PARTITION BY PointOfConnection, TradingDate
            ORDER BY TradingPeriod
        ) AS PreviousPrice

    FROM read_csv_auto('data/raw/prices/20260920_final.csv')
),

price_growth AS (
    SELECT
        TradingDate,
        TradingPeriod,
        PointOfConnection,
        Price,
        PreviousPrice,

        ROUND(Price - PreviousPrice, 2) AS PriceChange,
        ROUND(
            (Price - PreviousPrice) * 100.0
            / NULLIF(PreviousPrice, 0),
            2
        ) AS GrowthRate

    FROM price_changes
)

SELECT *
FROM price_growth
WHERE PreviousPrice > 0
ORDER BY GrowthRate DESC
LIMIT 10;

-- ---------------------------------------------------------------------
-- 练习 3: 把两个版本合并，每个键只留一行，有 final 取 final（去重和优先级）
-- ---------------------------------------------------------------------

WITH all_prices AS (
     -- Read interim data -- 
     SELECT 
          TradingDate,
          TradingPeriod,
          PointOfConnection,
          DollarsPerMegawattHour AS Price,
          'interim' AS PriceVersion
      FROM read_csv_auto('data/raw/prices/20260926_interim.csv')
      
      UNION ALL
      -- Read final data -- 
      
      SELECT 
          TradingDate,
          TradingPeriod,
          PointOfConnection,
          DollarsPerMegawattHour AS Price,
          'final' AS PriceVersion
      FROM read_csv_auto('data/raw/prices/20260926_final.csv')
)

SELECT
    TradingDate,
    TradingPeriod,
    PointOfConnection,
    Price,
    PriceVersion

FROM all_prices

QUALIFY ROW_NUMBER() OVER (
    PARTITION BY
        TradingDate,
        TradingPeriod,
        PointOfConnection
    ORDER BY
        CASE
            WHEN PriceVersion = 'final' THEN 1
            ELSE 2
        END
) = 1

ORDER BY
    TradingDate,
    PointOfConnection,
    TradingPeriod;

-- ---------------------------------------------------------------------
-- 练习 4: 判断一个新文件比旧文件多出了哪些键、少了哪些键（增量逻辑）
-- ---------------------------------------------------------------------
SELECT
    TradingDate,
    TradingPeriod,
    PointOfConnection
FROM read_csv_auto('data/raw/prices/20260926_final.csv')

EXCEPT

SELECT
    TradingDate,
    TradingPeriod,
    PointOfConnection
FROM read_csv_auto('data/raw/prices/20260926_interim.csv');

SELECT
    TradingDate,
    TradingPeriod,
    PointOfConnection
FROM read_csv_auto('data/raw/prices/20260926_interim.csv')

EXCEPT

SELECT
    TradingDate,
    TradingPeriod,
    PointOfConnection
FROM read_csv_auto('data/raw/prices/20260926_final.csv');


SELECT COUNT(DISTINCT PointOfConnection) FROM read_csv_auto('data/raw/prices/20260926_final.csv');