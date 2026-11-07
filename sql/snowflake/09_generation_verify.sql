-- 09_generation_verify.sql  (run as NZ_LOADER)
-- 期望值来自本地 6 个文件（2026-04 至 2026-09）的计算，加载后逐项核对。
use role NZ_LOADER;
use warehouse WH_XS;
use schema NZ_POWER.RAW;

-- 1. 总行数：期望 18135
select count(*) as total_rows from GENERATION_RAW;

-- 2. 每个文件的行数：期望 202604=2832, 202605=3021, 202606=2942, 202607=3144, 202608=3157, 202609=3039
select SOURCE_FILE, count(*) as row_count from GENERATION_RAW group by 1 order by 1;

-- 3. SOURCE_FILE 必须是纯文件名（不含 '/'）：期望 0
select count(*) as bad_source_file from GENERATION_RAW where SOURCE_FILE like '%/%';

-- 4. 夏令时：结束日 04-05 有 TP49（期望 94 行）；开始日 09-27 的 TP47 为空（期望 101 行）
select
    count_if(TRADING_DATE = '2026-04-05' and TP49 is not null) as dst_end_rows_with_tp49,
    count_if(TRADING_DATE = '2026-09-27' and TP47 is null)     as dst_start_rows_without_tp47
from GENERATION_RAW;

-- 5. 键唯一：电厂 × 节点 × 网络 × 日期，期望 0 行重复
select count(*) as duplicate_keys from (
    select GEN_CODE, POC_CODE, NWK_CODE, TRADING_DATE from GENERATION_RAW
    group by all having count(*) > 1
);

-- 6. 全部 TP 之和（kWh）：期望 21818516933；不同电厂 93 个、不同 POC 88 个
select
    sum(coalesce(try_to_number(TP1), 0) + coalesce(try_to_number(TP2), 0) + coalesce(try_to_number(TP3), 0) + coalesce(try_to_number(TP4), 0) + coalesce(try_to_number(TP5), 0) + coalesce(try_to_number(TP6), 0) + coalesce(try_to_number(TP7), 0) + coalesce(try_to_number(TP8), 0) + coalesce(try_to_number(TP9), 0) + coalesce(try_to_number(TP10), 0) + coalesce(try_to_number(TP11), 0) + coalesce(try_to_number(TP12), 0) + coalesce(try_to_number(TP13), 0) + coalesce(try_to_number(TP14), 0) + coalesce(try_to_number(TP15), 0) + coalesce(try_to_number(TP16), 0) + coalesce(try_to_number(TP17), 0) + coalesce(try_to_number(TP18), 0) + coalesce(try_to_number(TP19), 0) + coalesce(try_to_number(TP20), 0) + coalesce(try_to_number(TP21), 0) + coalesce(try_to_number(TP22), 0) + coalesce(try_to_number(TP23), 0) + coalesce(try_to_number(TP24), 0) + coalesce(try_to_number(TP25), 0) + coalesce(try_to_number(TP26), 0) + coalesce(try_to_number(TP27), 0) + coalesce(try_to_number(TP28), 0) + coalesce(try_to_number(TP29), 0) + coalesce(try_to_number(TP30), 0) + coalesce(try_to_number(TP31), 0) + coalesce(try_to_number(TP32), 0) + coalesce(try_to_number(TP33), 0) + coalesce(try_to_number(TP34), 0) + coalesce(try_to_number(TP35), 0) + coalesce(try_to_number(TP36), 0) + coalesce(try_to_number(TP37), 0) + coalesce(try_to_number(TP38), 0) + coalesce(try_to_number(TP39), 0) + coalesce(try_to_number(TP40), 0) + coalesce(try_to_number(TP41), 0) + coalesce(try_to_number(TP42), 0) + coalesce(try_to_number(TP43), 0) + coalesce(try_to_number(TP44), 0) + coalesce(try_to_number(TP45), 0) + coalesce(try_to_number(TP46), 0) + coalesce(try_to_number(TP47), 0) + coalesce(try_to_number(TP48), 0) + coalesce(try_to_number(TP49), 0) + coalesce(try_to_number(TP50), 0)) as total_kwh,
    count(distinct GEN_CODE) as plants,
    count(distinct POC_CODE) as pocs
from GENERATION_RAW;

-- 7. 幂等：重新运行 08_generation_copy_into.sql（应显示 0 个文件被处理），再运行查询 1，行数不变。
