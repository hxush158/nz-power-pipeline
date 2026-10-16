# Electricity Price Data Model Design

> **目标**：为 EMI 电力节点价格 CSV 建立简单、可测试、可重复运行的维度模型，优先完成 ingestion → RAW → staging → dimensional model → MART 的端到端 Pipeline。价格预测和完整修订审计暂不纳入本阶段。

---

## 1. 模型与粒度

- **业务事实粒度**：一个交易日 × 一个交易时段 × 一个节点，对应一条价格观测。
- **存储粒度**：一个交易日 × 一个交易时段 × 一个节点 × 一个发布版本（`interim` / `final`）。两个版本是同一业务事实的不同发布状态，**不可混在一起做普通聚合**。
- **修订策略**：整表重建，由文件全量构建，重复加载不产生重复行。

---

## 2. 表定义

| 表 | 粒度 / 主键 | 主要字段（建议类型） | 约束 / 备注 |
|---|---|---|---|
| `dim_date` | 每个交易日一行；**PK** `date_key` (`INTEGER`, `YYYYMMDD`) | `trading_date DATE`, `year SMALLINT`, `month SMALLINT`, `quarter SMALLINT`, `day_of_week SMALLINT`, `is_weekend BOOLEAN` | `trading_date` 唯一 |
| `dim_trading_period` | 每个**交易日 + 交易时段**一行；**PK** `period_key` (`BIGINT`) | `date_key INTEGER`, `trading_period SMALLINT`, `period_start_utc TIMESTAMPTZ`, `period_end_utc TIMESTAMPTZ`, `period_start_local TIMESTAMP`, `periods_in_day SMALLINT`, `period_key = date_key * 100 + trading_period` | `UNIQUE(date_key, trading_period)`；`date_key` → `dim_date`；具体时间须依可信交易时段规则生成 |
| `dim_node` | 每个价格节点一行；**PK** `node_key` (`BIGINT`) | `node_id VARCHAR`, `node_name VARCHAR NULL`, `island VARCHAR NULL`, `region VARCHAR NULL` | `node_id` 唯一；缺失属性暂为 `NULL`，后续从 EMI 节点参考数据补全 |
| `v_dim_node` | 每个节点一行（视图，建在 dim_node 之上）**PK** `node_key` (`BIGINT`) | `node_id VARCHAR`, `node_name VARCHAR NULL`, `island VARCHAR NULL`, `region VARCHAR NULL`，`first_seen_date DATE` | 最早交易日，等于全局最小日则为 NULL；派生，不物理存储 |
| `fact_electricity_price` | 每个交易日 × 时段 × 节点 × 版本一行；**PK** (`period_key`, `node_key`, `price_version`) | `period_key BIGINT`, `node_key BIGINT`, `price_version VARCHAR`, `price_nzd_per_mwh DECIMAL(18,2)`, `source_file VARCHAR` | 版本仅允许 `interim` / `final`；`period_key`、`node_key` 为外键；事实表不含 `date_key`，日期通过 `period_key` 关联。 |
| `mart_current_price` | 每个交易时段 × 节点一行；**PK**  `period_key` (`BIGINT`), `node_key` (`BIGINT`) | `trading_date DATE`, `trading_period SMALLINT`, `period_start_local TIMESTAMP`, `node_id VARCHAR`, `price_version VARCHAR`, `price_nzd_per_mwh DECIMAL(18,2)`| 表（非视图）、整表重建、有 final 取 final 否则 interim |
| `mart_daily_price` | 粒度每个交易日 × 节点；**PK**  `trading_date`(`DATE`) , `node_key` (`BIGINT`) | `node_id VARCHAR`, `avg_price DECIMAL(18,2)`, `min_price DECIMAL(18,2)`, `max_price DECIMAL(18,2)`, `period_count BIGINT`, `interim_period_count BIGINT`| 表（非视图）、整表重建；基于 `mart_current_price` 汇总；简单平均，等同于时间加权（所有时段都是 30 分钟）；`interim_period_count` 表示当天使用临时价的时段数 |


> 注：事实表不含 `date_key`，日期一律通过 `period_key` 关联 `dim_trading_period` 再到 `dim_date`。`period_start_utc` / `period_end_utc` 是 `TIMESTAMPTZ`（绝对时刻）；`period_start_local` 是不带时区的新西兰墙上时钟，夏令时结束日会出现重复读数，不能单独当键，必须配合 `period_key` 使用。

## 3. 文字版 ERD

```text
 dim_date (PK date_key)
      │ 1:N
      ▼
 dim_trading_period (PK period_key; FK date_key; UNIQUE date_key + trading_period)
      │ 1:N
      │
      ├──────────────┐
      ▼              │
 fact_electricity_price
   PK (period_key, node_key, price_version)
   FK period_key → dim_trading_period.period_key
   FK date_key   → dim_date.date_key     [冗余，需一致性校验]
   FK node_key   → dim_node.node_key
   price_nzd_per_mwh, loaded_at, source_file
      ▲
      │ N:1
 dim_node (PK node_key; UNIQUE node_id)
```
## 4. 五项关键设计决策

1. **价格粒度与版本**：保留 `interim` 和 `final` 两个业务版本；同一版本重新下载后采用可重复执行的 upsert/替换策略，整表重建，增量放到 dbt。
2. **夏令时**：交易时段编号不是固定本地钟点。`dim_trading_period` 依据交易日和市场时段规则记录实际 UTC 起止时间及新西兰本地时间，支持 46/48/50 时段日；禁止仅以 `(trading_period - 1) × 30分钟` 推算所有日期的本地时间。时段长度与源文件语义需在 ingestion 时核验。
3. **节点维度**：先从价格数据中抽取唯一 `node_id` 建 `dim_node`，不等待岛屿/区域属性；`island`、`region` 后续通过 EMI 参考数据补齐，暂不引入 SCD Type 2。每次加载把新 node_id 补进 dim_node。
4. **发电量数据**：当前只做价格事实表；第 9 周另建 `fact_generation`（粒度依实际数据源确认），尽可能复用一致性日期、时段及节点维度，但必须先核实发电计量对象和价格节点是否可映射。first_seen_date 取事实表中该节点的 MIN(交易日)，每次重算，所以重跑和回填历史数据都是幂等的。
5. **最佳可用价格**：在 MART 表 `mart_current_price` 中对每个 `(period_key, node_key)` 只选一行：**有 final 则选 final，否则选 interim**。下游日均价、趋势和 BI 均基于此表，避免重复计数。

## 5. MART 与数据质量验收

- `mart_current_price`：每个交易时段 × 节点保留一条当前最佳价格；`mart_daily_price`：基于当前最佳价格按交易日、节点汇总（简单平均，等同于时间加权"）。
- **基础测试**：主键无重复、维度外键可解析、`price_version` 值合法、每个交易日时段数量和 UTC 时间映射合理、`final` 优先级正确、重跑结果幂等。
- **范围控制**：暂不实现价格预测、完整发布修订审计、复杂区域映射或发电与价格的联合归因；优先落实自动化加载、清洗、转换、测试和编排。