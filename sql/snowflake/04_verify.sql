-- 04_verify.sql  (run as NZ_LOADER)
use role NZ_LOADER;
use warehouse WH_XS;
use schema NZ_POWER.RAW;

-- 1. total rows: final files should sum to 2,156,450 (+ rows of the interim file)
select count(*) as total_rows from PRICES_RAW;

-- 2. per version
select regexp_substr(SOURCE_FILE, '(final|interim)') as version,
       count(distinct SOURCE_FILE) as files,
       count(*) as row_count
from PRICES_RAW group by 1;

-- 3. file names must be bare names (no '/')
select count(*) as bad_source_file from PRICES_RAW where SOURCE_FILE like '%/%';

-- 4. idempotency: re-run 03_copy_into.sql, then re-run query 1. The count must not change.
