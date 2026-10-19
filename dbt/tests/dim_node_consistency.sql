-- dim_node 行数 = stg_prices 里去掉空 ID、折叠大小写后的不同节点数；
-- v_dim_node 行数 = dim_node 行数（视图没有多出或少掉节点）。
select 'dim_node_count_mismatch' as problem, 1 as detail
where (select count(*) from {{ ref('dim_node') }})
    <> (
        select count(distinct upper(node_id))
        from {{ ref('stg_prices') }}
        where node_id is not null and trim(node_id) <> ''
    )

union all

select 'v_dim_node_count_mismatch', 1
where (select count(*) from {{ ref('v_dim_node') }})
    <> (select count(*) from {{ ref('dim_node') }})
