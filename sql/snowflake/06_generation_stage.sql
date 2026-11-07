-- 06_generation_stage.sql  (run as NZ_LOADER)
-- EMI Generation_MD（按电厂估算的发电量，每月一个文件，宽表：TP1..TP50）。
-- File format + external stage，沿用价格数据的 INT_AZURE_RAW；文件在 raw/generation/YYYY-MM/ 下。
-- 用 create or replace：可重复运行。空字段读成 NULL（正常日的 TP49/TP50、夏令时开始日的 TP47/TP48 都是空）。
use role NZ_LOADER;
use warehouse WH_XS;
use schema NZ_POWER.RAW;

create or replace file format FF_GENERATION_CSV
    type = csv
    skip_header = 1
    field_optionally_enclosed_by = '"'
    null_if = ('')
    empty_field_as_null = true;

create or replace stage STG_GENERATION
    url = 'azure://nzpowerhxu.blob.core.windows.net/raw/generation/'
    storage_integration = INT_AZURE_RAW
    file_format = FF_GENERATION_CSV;

-- 验收：直接读 Stage。期望（2026-04 至 2026-09 共 6 个文件）：paths = 6，names = 6，row_count = 18135。
select
    count(distinct metadata$filename) as paths,
    count(distinct regexp_substr(metadata$filename, '[^/]+$')) as names,
    count(*) as row_count
from @STG_GENERATION (file_format => 'NZ_POWER.RAW.FF_GENERATION_CSV');
