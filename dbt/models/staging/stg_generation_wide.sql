-- stg_generation_wide: EMI Generation_MD 原始宽表（视图，永远反映 raw_generation_glob 下的文件 / RAW.GENERATION_RAW）。
-- 相对路径，必须在项目根目录运行 dbt。
-- 只读文件名符合 YYYYMM_Generation_MD.csv 的文件；全部列保持字符串，不做任何转换。
-- 空的时段列（如普通日的 TP49、TP50）是 NULL。转成长表在 stg_generation 里做。

with raw as (

    {{ nz_raw_generation() }}

)

select *
from raw
where {{ nz_is_generation_file('source_file') }}
