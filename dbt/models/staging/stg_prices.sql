-- stg_prices: 原始价格 CSV 的统一输入层（视图，永远反映 raw_prices_glob 下的文件）。
-- 相对路径，必须在项目根目录运行 dbt。
-- 规则（与旧版 sql/model/03_stg_prices.sql 相同）：
--   只读文件名符合 YYYYMMDD_final.csv / YYYYMMDD_interim.csv 的文件。
--   node_id 始终按字符串读取；不做 TRIM 或大小写转换，脏数据交给测试发现。
--   不加 loaded_at：视图是文件内容的确定性映射。

with raw as (

    {{ nz_raw_prices() }}

)

select
    cast(TradingDate as date) as trading_date,
    cast(TradingPeriod as smallint) as trading_period,
    PointOfConnection as node_id,
    cast(DollarsPerMegawattHour as double) as price_nzd_per_mwh,
    {{ nz_price_version('source_file') }} as price_version,
    source_file
from raw
where {{ nz_is_price_file('source_file') }}
