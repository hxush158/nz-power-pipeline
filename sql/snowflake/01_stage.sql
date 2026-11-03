-- 01_stage.sql  (run as NZ_LOADER)
-- File format + external stage pointing at Azure Blob via the storage integration.
-- Prerequisite: Azure consent done and "Storage Blob Data Reader" granted on nzpowerhxu.
use role NZ_LOADER;
use warehouse WH_XS;
use schema NZ_POWER.RAW;

create file format if not exists FF_PRICES_CSV
    type = csv
    skip_header = 1
    field_optionally_enclosed_by = '"'
    null_if = ('')
    empty_field_as_null = true;

create stage if not exists STG_PRICES
    url = 'azure://nzpowerhxu.blob.core.windows.net/raw/prices/'
    storage_integration = INT_AZURE_RAW
    file_format = FF_PRICES_CSV;

-- Acceptance: expect 184 rows (183 final + 1 interim). 403 here = permission not propagated yet.
list @STG_PRICES;
select count(*) as files_listed from table(result_scan(last_query_id()));
