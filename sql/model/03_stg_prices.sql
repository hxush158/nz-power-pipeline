-- stg_prices: 原始价格 CSV 的统一输入层（视图，永远反映 data/raw/prices 下的文件）。
-- 依赖：无。相对路径，必须在项目根目录执行。
-- 规则：
--   只读取文件名符合 YYYYMMDD_final.csv / YYYYMMDD_interim.csv 的文件（与 upload.py 一致）。
--   列名改成模型里的 snake_case 名字。
--   node_id 始终按字符串读取（节点代码如 ABY0111；不让 DuckDB 推断类型）。
--   price_version 来自文件名；source_file 是不含目录的文件名。
--   这里不加 loaded_at：视图应是文件内容的确定性映射，加载时间在事实表加载时记录。
--   不做 TRIM 或大小写转换：忠实反映源文件，脏数据交给后面的测试发现。

CREATE OR REPLACE VIEW stg_prices AS
WITH raw AS (
    SELECT
        *,
        regexp_extract(filename, '([^/\\]+)$', 1) AS source_file
    FROM read_csv(
        'data/raw/prices/*.csv',
        header = true,
        filename = true,
        types = {'PointOfConnection': 'VARCHAR'}
    )
)
SELECT
    CAST(TradingDate AS DATE) AS trading_date,
    CAST(TradingPeriod AS SMALLINT) AS trading_period,
    PointOfConnection AS node_id,
    CAST(DollarsPerMegawattHour AS DOUBLE) AS price_nzd_per_mwh,
    regexp_extract(source_file, '^[0-9]{8}_(final|interim)\.csv$', 1)
        AS price_version,
    source_file
FROM raw
WHERE regexp_matches(source_file, '^[0-9]{8}_(final|interim)\.csv$');
