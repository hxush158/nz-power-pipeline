-- 05_reconcile.sql  对账指纹：同一份查询在 Snowflake 和 DuckDB 上各跑一次，14 行结果必须逐行相同。
-- 本文件是 DuckDB 版（由 05_reconcile.sql 去掉库名和 schema 前缀得到）。
select 'current_rows' as metric, cast(count(*) as varchar) as value from mart_current_price
union all select 'current_price_sum', cast(round(sum(price_nzd_per_mwh), 2) as varchar) from mart_current_price
union all select 'current_interim_rows', cast(count(*) as varchar) from mart_current_price where price_version = 'interim'
union all select 'current_nodes', cast(count(distinct node_id) as varchar) from mart_current_price
union all select 'current_min_date', cast(min(trading_date) as varchar) from mart_current_price
union all select 'current_max_date', cast(max(trading_date) as varchar) from mart_current_price
union all select 'daily_rows', cast(count(*) as varchar) from mart_daily_price
union all select 'daily_period_count_sum', cast(sum(period_count) as varchar) from mart_daily_price
union all select 'daily_avg_price_sum', cast(round(sum(avg_price), 2) as varchar) from mart_daily_price
union all select 'periods_20260405', cast(count(*) as varchar) from dim_trading_period where date_key = 20260405
union all select 'periods_20260927', cast(count(*) as varchar) from dim_trading_period where date_key = 20260927
union all select 'fact_rows', cast(count(*) as varchar) from fact_electricity_price
union all select 'dim_node_rows', cast(count(*) as varchar) from dim_node
union all select 'nodes_with_first_seen', cast(count(*) as varchar) from v_dim_node where first_seen_date is not null
order by metric;
