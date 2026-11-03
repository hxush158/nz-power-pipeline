-- 02_raw_table.sql  (run as NZ_LOADER)
-- RAW keeps the 4 CSV columns exactly as text; typing happens in dbt staging.
use role NZ_LOADER;
use warehouse WH_XS;
use schema NZ_POWER.RAW;

create table if not exists PRICES_RAW (
    TRADINGDATE             varchar,
    TRADINGPERIOD           varchar,
    POINTOFCONNECTION       varchar,
    DOLLARSPERMEGAWATTHOUR  varchar,
    SOURCE_FILE             varchar,                                  -- file name only, no folders
    LOADED_AT               timestamp_ltz default current_timestamp()
);
