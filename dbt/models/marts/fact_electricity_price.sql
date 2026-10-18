-- fact_electricity_price: 交易日 × 时段 × 节点 × 版本（interim/final）一行。
--   全量重建，由 stg_prices 构建，天然幂等；interim 与 final 是不同版本，两行并存。
--   period_key / node_key 通过 inner join 维度表取得，保证外键一定存在。
--   node 按大写 node_id 关联（与 dim_node 一致）。
--   price_nzd_per_mwh 为 decimal(18,2)。
--   不去重：同键同版本重复会原样保留，由 tests/ 下的主键唯一性测试发现。
--   关联不上的行（空 node_id、不存在的时段）会被 inner join 排除；
--   对账测试（stg 行数 = 事实表行数）在第 D 步加入，防止静默丢数据。
--   增量加载和 loaded_at 留到第 F 步。

select
    p.period_key,
    n.node_key,
    s.price_version,
    cast(s.price_nzd_per_mwh as decimal(18, 2)) as price_nzd_per_mwh,
    s.source_file
from {{ ref('stg_prices') }} as s
inner join {{ ref('dim_date') }} as d
    on d.trading_date = s.trading_date
inner join {{ ref('dim_trading_period') }} as p
    on p.date_key = d.date_key
    and p.trading_period = s.trading_period
inner join {{ ref('dim_node') }} as n
    on n.node_id = upper(s.node_id)
order by p.period_key, n.node_key, s.price_version
