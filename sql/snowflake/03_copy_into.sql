-- 03_copy_into.sql  (run as NZ_LOADER)
-- Idempotent: Snowflake's load metadata skips files already loaded (64 days),
-- so running this twice must not change the row count. ON_ERROR=ABORT_STATEMENT = fail loudly.
use role NZ_LOADER;
use warehouse WH_XS;
use schema NZ_POWER.RAW;

copy into PRICES_RAW (TRADINGDATE, TRADINGPERIOD, POINTOFCONNECTION, DOLLARSPERMEGAWATTHOUR, SOURCE_FILE)
from (
    select $1, $2, $3, $4, regexp_substr(metadata$filename, '[^/]+$')
    from @STG_PRICES
)
pattern = '.*[0-9]{8}_(final|interim)[.]csv'
on_error = 'ABORT_STATEMENT';
