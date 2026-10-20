-- fact_electricity_price: 交易日 × 时段 × 节点 × 版本（interim/final）一行。
--   增量模型：每次运行重新处理"已加载数据里最晚交易日往前 N 天"的数据
--   （N = var fact_lookback_days，默认 7），按 unique_key 先删后插（delete+insert）。
--   所以窗口内被修订的价格会覆盖旧值；同一版本重复加载不产生重复行。
--   interim 与 final 是不同版本（主键含 price_version），final 到达时新增一行，不删除 interim。
--   窗口之外的历史修订不会被发现，需要 `dbt build --full-refresh` 整表重建。
--   窗口的起点由已加载数据决定而不是今天的日期，结果只取决于数据。
--   period_key / node_key 通过 inner join 维度表取得，保证外键一定存在。
--   node 按大写 node_id 关联（与 dim_node 一致）。
--   price_nzd_per_mwh 为 decimal(18,2)。
--   loaded_at：这一行是哪次 dbt 运行写入的（带时区的时刻）。审计用，不参与主键。
--   不去重：同键同版本重复会原样保留，由 tests/ 下的主键唯一性测试发现。
--   关联不上的行会被 inner join 排除；对账测试（stg 行数 = 事实表行数）防止静默丢数据。
--   on_schema_change=fail：表结构变化时直接报错，不静默忽略；改结构后用 --full-refresh。

{{
    config(
        materialized='incremental',
        unique_key=['period_key', 'node_key', 'price_version'],
        incremental_strategy='delete+insert',
        on_schema_change='fail'
    )
}}

select
    p.period_key,
    n.node_key,
    s.price_version,
    cast(s.price_nzd_per_mwh as decimal(18, 2)) as price_nzd_per_mwh,
    s.source_file,
    current_timestamp as loaded_at
from {{ ref('stg_prices') }} as s
inner join {{ ref('dim_date') }} as d
    on d.trading_date = s.trading_date
inner join {{ ref('dim_trading_period') }} as p
    on p.date_key = d.date_key
    and p.trading_period = s.trading_period
inner join {{ ref('dim_node') }} as n
    on n.node_id = upper(s.node_id)
{% if is_incremental() %}
where d.trading_date >= coalesce(
    (
        select max(d2.trading_date)
        from {{ this }} as t
        inner join {{ ref('dim_trading_period') }} as p2
            on p2.period_key = t.period_key
        inner join {{ ref('dim_date') }} as d2
            on d2.date_key = p2.date_key
    ) - {{ var('fact_lookback_days') }},
    date '1900-01-01'
)
{% endif %}
