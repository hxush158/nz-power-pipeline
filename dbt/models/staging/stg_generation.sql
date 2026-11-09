-- stg_generation: 发电宽表（TP1..TP50）转成长表，一行 = 电厂 × 节点 × 网络 × 交易日 × 交易时段。
--   - 空的时段列不出行（该日没有这个时段：普通日的 TP49/TP50、夏令时开始日的 TP47 以后）；
--     值为 0 的时段是真实数据，保留。是否有时段被误丢，由 tests/stg_generation_periods_match_calendar.sql 检查。
--   - 同一电厂在同一节点同一天可有两行，区别只在 nwk_code（输电网 / 配电网），所以网络在键里。
--   - node_id 转大写（与 stg_prices / dim_node 一致）；电厂、燃料、技术代码保持原样（燃料有两套写法，映射放到下一层）。
--   - generation_kwh 是 EMI 的估算值（把计量的并网注入量对应到电厂），单位 kWh。
--   用 50 条 select ... union all 展开，两个引擎通用，不依赖 unpivot 语法。

with wide as (

    select * from {{ ref('stg_generation_wide') }}

)

    select
        cast(trading_date as date) as trading_date,
        cast(1 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp1 as bigint) as generation_kwh,
        source_file
    from wide
    where tp1 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(2 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp2 as bigint) as generation_kwh,
        source_file
    from wide
    where tp2 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(3 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp3 as bigint) as generation_kwh,
        source_file
    from wide
    where tp3 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(4 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp4 as bigint) as generation_kwh,
        source_file
    from wide
    where tp4 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(5 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp5 as bigint) as generation_kwh,
        source_file
    from wide
    where tp5 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(6 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp6 as bigint) as generation_kwh,
        source_file
    from wide
    where tp6 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(7 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp7 as bigint) as generation_kwh,
        source_file
    from wide
    where tp7 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(8 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp8 as bigint) as generation_kwh,
        source_file
    from wide
    where tp8 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(9 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp9 as bigint) as generation_kwh,
        source_file
    from wide
    where tp9 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(10 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp10 as bigint) as generation_kwh,
        source_file
    from wide
    where tp10 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(11 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp11 as bigint) as generation_kwh,
        source_file
    from wide
    where tp11 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(12 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp12 as bigint) as generation_kwh,
        source_file
    from wide
    where tp12 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(13 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp13 as bigint) as generation_kwh,
        source_file
    from wide
    where tp13 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(14 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp14 as bigint) as generation_kwh,
        source_file
    from wide
    where tp14 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(15 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp15 as bigint) as generation_kwh,
        source_file
    from wide
    where tp15 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(16 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp16 as bigint) as generation_kwh,
        source_file
    from wide
    where tp16 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(17 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp17 as bigint) as generation_kwh,
        source_file
    from wide
    where tp17 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(18 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp18 as bigint) as generation_kwh,
        source_file
    from wide
    where tp18 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(19 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp19 as bigint) as generation_kwh,
        source_file
    from wide
    where tp19 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(20 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp20 as bigint) as generation_kwh,
        source_file
    from wide
    where tp20 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(21 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp21 as bigint) as generation_kwh,
        source_file
    from wide
    where tp21 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(22 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp22 as bigint) as generation_kwh,
        source_file
    from wide
    where tp22 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(23 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp23 as bigint) as generation_kwh,
        source_file
    from wide
    where tp23 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(24 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp24 as bigint) as generation_kwh,
        source_file
    from wide
    where tp24 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(25 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp25 as bigint) as generation_kwh,
        source_file
    from wide
    where tp25 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(26 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp26 as bigint) as generation_kwh,
        source_file
    from wide
    where tp26 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(27 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp27 as bigint) as generation_kwh,
        source_file
    from wide
    where tp27 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(28 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp28 as bigint) as generation_kwh,
        source_file
    from wide
    where tp28 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(29 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp29 as bigint) as generation_kwh,
        source_file
    from wide
    where tp29 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(30 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp30 as bigint) as generation_kwh,
        source_file
    from wide
    where tp30 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(31 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp31 as bigint) as generation_kwh,
        source_file
    from wide
    where tp31 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(32 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp32 as bigint) as generation_kwh,
        source_file
    from wide
    where tp32 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(33 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp33 as bigint) as generation_kwh,
        source_file
    from wide
    where tp33 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(34 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp34 as bigint) as generation_kwh,
        source_file
    from wide
    where tp34 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(35 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp35 as bigint) as generation_kwh,
        source_file
    from wide
    where tp35 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(36 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp36 as bigint) as generation_kwh,
        source_file
    from wide
    where tp36 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(37 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp37 as bigint) as generation_kwh,
        source_file
    from wide
    where tp37 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(38 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp38 as bigint) as generation_kwh,
        source_file
    from wide
    where tp38 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(39 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp39 as bigint) as generation_kwh,
        source_file
    from wide
    where tp39 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(40 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp40 as bigint) as generation_kwh,
        source_file
    from wide
    where tp40 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(41 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp41 as bigint) as generation_kwh,
        source_file
    from wide
    where tp41 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(42 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp42 as bigint) as generation_kwh,
        source_file
    from wide
    where tp42 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(43 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp43 as bigint) as generation_kwh,
        source_file
    from wide
    where tp43 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(44 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp44 as bigint) as generation_kwh,
        source_file
    from wide
    where tp44 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(45 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp45 as bigint) as generation_kwh,
        source_file
    from wide
    where tp45 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(46 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp46 as bigint) as generation_kwh,
        source_file
    from wide
    where tp46 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(47 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp47 as bigint) as generation_kwh,
        source_file
    from wide
    where tp47 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(48 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp48 as bigint) as generation_kwh,
        source_file
    from wide
    where tp48 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(49 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp49 as bigint) as generation_kwh,
        source_file
    from wide
    where tp49 is not null
    union all

    select
        cast(trading_date as date) as trading_date,
        cast(50 as smallint) as trading_period,
        site_code,
        upper(poc_code) as node_id,
        nwk_code as network_code,
        gen_code as plant_code,
        fuel_code,
        tech_code,
        cast(tp50 as bigint) as generation_kwh,
        source_file
    from wide
    where tp50 is not null
