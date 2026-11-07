-- 01_stage.sql  (run as NZ_LOADER)
-- File format + external stage pointing at Azure Blob via the storage integration.
-- 用 create or replace：脚本可重复运行，结果总是同一个定义（不能和 if not exists 一起写）。
-- 重建 Stage 不影响 RAW 表的加载记录（加载记录跟着表走），所以 COPY INTO 的幂等性不变。
-- Prerequisite: Azure consent done and "Storage Blob Data Reader" granted on nzpowerhxu.
use role NZ_LOADER;
use warehouse WH_XS;
use schema NZ_POWER.RAW;

create or replace file format FF_PRICES_CSV
    type = csv
    skip_header = 1
    field_optionally_enclosed_by = '"'
    null_if = ('')
    empty_field_as_null = true;

create or replace stage STG_PRICES
    url = 'azure://nzpowerhxu.blob.core.windows.net/raw/prices/'
    storage_integration = INT_AZURE_RAW
    file_format = FF_PRICES_CSV;

-- 验收：直接读 Stage（不用 result_scan(last_query_id())，它会取到别的查询的结果）。
-- 期望：paths = 184，names = 184（没有同名文件在不同目录），row_count = 2168258（183 个 final + 1 个 interim）。
-- 报 403 / not authorized = Azure 权限还没传播完，等几分钟。
select
    count(distinct metadata$filename) as paths,
    count(distinct regexp_substr(metadata$filename, '[^/]+$')) as names,
    count(*) as row_count
from @STG_PRICES (file_format => 'NZ_POWER.RAW.FF_PRICES_CSV');
