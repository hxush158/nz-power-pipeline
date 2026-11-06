# DuckDB → Snowflake 移植笔记

跨引擎差异集中在 `dbt/macros/portable.sql`（模型只调用 `nz_*` macro）。本表记录每一处差异和原因。
状态列：**已验证** = 2026-11-04 在 Snowflake 上 `dbt build` 72 项全部通过，且和 DuckDB 的对账指纹一致（见文末）。

| 功能 | DuckDB | Snowflake | 原因 / 注意 | 状态 |
|---|---|---|---|---|
| 日期序列 | `generate_series(.., interval 1 day)` | `generator(rowcount => N)` + `dateadd` | Snowflake 没有 generate_series；rowcount 必须是常量，所以天数在 Jinja 里算 | 已验证 |
| 日期→YYYYMMDD | `strftime(d, '%Y%m%d')` | `to_char(d, 'YYYYMMDD')` | 格式串写法不同 | 已验证 |
| ISO 星期 | `isodow` | `dayofweekiso` | 同为周一=1 | 已验证 |
| 节点键 | `hash(x) >> 1` | `hash(x)` | DuckDB 的 hash 是无符号 64 位，要右移才装得进 BIGINT；Snowflake 的 HASH 已是有符号 64 位。两边键值不同（已决定保留各引擎自己的哈希） | 已验证 |
| 当地→UTC | `ts at time zone 'Pacific/Auckland'` | `convert_timezone('Pacific/Auckland','UTC',ts)` | **夏令时风险最高**。当地午夜不会落在切换的模糊时段，所以安全 | 已验证 |
| UTC→当地 | `ts at time zone ..` | `convert_timezone('UTC','Pacific/Auckland',ts)` | 同上 | 已验证 |
| Unix 秒 | `epoch(ts)` | `date_part(epoch_second, ts)` | Snowflake 上 UTC 时刻存 TIMESTAMP_NTZ，按 UTC 理解 | 已验证 |
| 加分钟 | `ts + to_minutes(n)` | `dateadd(minute, n, ts)` | | 已验证 |
| 1..50 数字表 | `range(1,51) as p(trading_period)` | `generator` + `row_number()` | | 已验证 |
| 条件计数 | `count(*) filter (where c)` | `count_if(c)` | | 已验证 |
| 读原始价格 | `read_csv(glob, filename=true)` | 读 RAW.PRICES_RAW（source） | Snowflake 数据由 COPY INTO 装载；RAW 全是字符串，类型转换在 stg_prices | 已验证 |
| 版本提取/文件名匹配 | `regexp_extract` / `regexp_matches` + `\.` | `regexp_substr(..,'e',1)` / `regexp_like` + `[.]` | Snowflake 字符串里反斜杠是转义符，用 `[.]` 避开 | 已验证 |
| 日期差 | `date_diff('day',a,b)` | `datediff(day,a,b)` | 测试里原来用 `date - date` | 已验证 |
| UTC 时刻字面量 | `timestamptz '..+00'` | `to_timestamp_ntz('..')` | 测试里的期望值 | 已验证 |

## 约定
- **绝对时刻的类型**：DuckDB 用 TIMESTAMPTZ；Snowflake 用 TIMESTAMP_NTZ，存 UTC 墙上时钟（不用 LTZ，避免受账号时区影响；本账号时区是美国太平洋）。两边表示同一个时刻，但列的类型不同。
- **Schema**：Snowflake 上 staging→STAGING，dim/fact→CORE，三张对外的表→MART（见 `generate_schema_name.sql`）。DuckDB 全部在 `main`。
- **测试里去掉的写法**：`HAVING` 不带 `GROUP BY`、`date - date`、`interval 30 minute`、`FILTER (WHERE ..)`、`timestamptz` 字面量。

## 第一次在 Snowflake 上构建
增量模型 `fact_electricity_price` 的单元测试需要这张表已存在（要读表结构给模拟数据定类型）。全新环境第一次构建会报
"relation doesn't exist"，先建一张空表再整体构建：

    dbt run --select fact_electricity_price --empty --target snowflake
    dbt build --target snowflake

空表上的第一次增量运行会回退到 `date '1900-01-01'`，把全部数据加载进来。本地 DuckDB 因为库里早就有这张表，不会遇到。

## 对账结果（2026-11-04）
同一份指纹查询（`sql/snowflake/05_reconcile.sql` 和 `05_reconcile_duckdb.sql`）在两个引擎上各跑一次，14 项里 13 项逐行相同：
行数 2,156,450、价格总和 137,078,471.80、246 个节点、日汇总 44,927 行、4 月 5 日 50 个时段、9 月 27 日 46 个时段、事实表 2,168,258 行等。

**已知差异（11-06 已修，见下）**：`daily_avg_price_sum` Snowflake 2,855,139.18，DuckDB 2,855,138.75，差 0.43。
- 原因：`round(avg(price), 2)` 在"恰好落在 x.xx5"时的进位方式不同。DuckDB 的 `avg(DECIMAL)` 返回 DOUBLE，x.xx5 没法精确表示，进位不稳定；Snowflake 保持精确小数，按远离零方向进位。
- 验证：用整数运算按"远离零方向进位"算出的日均价总和是 2,855,139.18，与 Snowflake 相同；共有 913 个（日 × 节点）分组恰好落在中间。

## avg_price 的修复（2026-11-06，应 ChemQ 要求）
ChemQ 的标准答案只从 DuckDB 生成，要求两个引擎逐行一致，所以不再容忍这 0.01 的差异。
- 新 macro `nz_avg_price_2dp`：价格先换成整数"分"求和，平均数用整数运算舍入（`sign(S) * floor((2|S| + n) / (2n))`），
  规则与 Snowflake 的 ROUND 相同：四舍五入、远离零（0.005 → 0.01，-0.005 → -0.01）。
- DuckDB 版用 `//`（DuckDB 的 `/` 是浮点除法），Snowflake 版用 `floor(a / b)`。
- 先转 bigint 再乘 0.01，避免 hugeint 乘 decimal 超 38 位后悄悄变成 DOUBLE。
- 只动 `avg_price`；`min_price`、`max_price`、计数和 `mart_current_price` 不变。
- 单元测试：`daily_d2`（10.00、10.01 → 10.01）、`daily_d3`（-10.00、-10.01 → -10.01）、`daily_d4`（0 附近的正负两个 tie），两个引擎都要跑过。
- 逐行比较：`scripts/compare_daily_price.py`（按 trading_date + node_id 对齐，只读）。
