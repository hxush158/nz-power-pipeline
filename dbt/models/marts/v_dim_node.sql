-- v_dim_node: dim_node 的全部列 + first_seen_date（派生视图，不物理存储）。
--   first_seen_date = 该节点在事实表中出现的最早交易日（不区分版本）。
--   等于事实表全局最早交易日时为 NULL（基线节点，真实起点未知）。
--   单独做视图而不是 dim_node 的一列，避免 dim_node → fact → dim_node 的循环依赖。

{{ config(materialized='view') }}

with fact_dates as (

    select f.node_key, d.trading_date
    from {{ ref('fact_electricity_price') }} as f
    inner join {{ ref('dim_trading_period') }} as p on p.period_key = f.period_key
    inner join {{ ref('dim_date') }} as d on d.date_key = p.date_key

),

first_seen as (

    select node_key, min(trading_date) as first_date
    from fact_dates
    group by node_key

),

global_min as (

    select min(trading_date) as min_date from fact_dates

)

select
    n.node_key,
    n.node_id,
    n.node_name,
    n.island,
    n.region,
    case when f.first_date > g.min_date then f.first_date end as first_seen_date
from {{ ref('dim_node') }} as n
left join first_seen as f on f.node_key = n.node_key
cross join global_min as g
