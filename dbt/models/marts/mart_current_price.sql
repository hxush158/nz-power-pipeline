-- mart_current_price: 每个交易时段 × 节点一行的"当前最佳价格"。
--   有 final 取 final，否则取 interim；price_version 标明选中的版本。
--   同键同版本重复属于上游错误，由事实表主键测试发现；
--   这里用 source_file、价格兜底排序，保证输出确定。

-- 对外暴露的三张表之一：放在 MART schema（ChemQ 只读用户可见），其余 dim/fact 在 CORE。
{{ config(schema='MART') }}

select
    f.period_key,
    f.node_key,
    d.trading_date,
    p.trading_period,
    p.period_start_local,
    n.node_id,
    f.price_nzd_per_mwh,
    f.price_version
from {{ ref('fact_electricity_price') }} as f
inner join {{ ref('dim_trading_period') }} as p on p.period_key = f.period_key
inner join {{ ref('dim_date') }} as d on d.date_key = p.date_key
inner join {{ ref('dim_node') }} as n on n.node_key = f.node_key
qualify row_number() over (
    partition by f.period_key, f.node_key
    order by
        (f.price_version = 'final') desc,
        f.source_file,
        f.price_nzd_per_mwh
) = 1
order by f.period_key, f.node_key
