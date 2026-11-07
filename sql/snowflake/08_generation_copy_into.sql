-- 08_generation_copy_into.sql  (run as NZ_LOADER)
-- 幂等：Snowflake 的加载记录会跳过已加载的文件，所以重复运行行数不变。ON_ERROR=ABORT_STATEMENT：出错就整体失败。
use role NZ_LOADER;
use warehouse WH_XS;
use schema NZ_POWER.RAW;

copy into GENERATION_RAW (SITE_CODE, POC_CODE, NWK_CODE, GEN_CODE, FUEL_CODE, TECH_CODE, TRADING_DATE, TP1, TP2, TP3, TP4, TP5, TP6, TP7, TP8, TP9, TP10, TP11, TP12, TP13, TP14, TP15, TP16, TP17, TP18, TP19, TP20, TP21, TP22, TP23, TP24, TP25, TP26, TP27, TP28, TP29, TP30, TP31, TP32, TP33, TP34, TP35, TP36, TP37, TP38, TP39, TP40, TP41, TP42, TP43, TP44, TP45, TP46, TP47, TP48, TP49, TP50, SOURCE_FILE)
from (
    select $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39, $40, $41, $42, $43, $44, $45, $46, $47, $48, $49, $50, $51, $52, $53, $54, $55, $56, $57, regexp_substr(metadata$filename, '[^/]+$')
    from @STG_GENERATION
)
pattern = '.*[0-9]{6}_Generation_MD[.]csv'
on_error = 'ABORT_STATEMENT';
