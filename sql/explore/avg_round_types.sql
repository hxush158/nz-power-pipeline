-- DuckDB：确认 avg_price 新算法每一步的类型，以及舍入结果（ChemQ 要求先用 typeof() 确认）。
-- 用法（项目根目录）：
--   uv run python -c "import duckdb; print(duckdb.sql(open('sql/explore/avg_round_types.sql').read()).fetchall())"
-- 期望：avg_double 那一列是 DOUBLE（说明旧写法确实走浮点数）；cents_sum 是整数类型；
--       new_avg 的类型是 DECIMAL(18,2)；四个 tie 样例分别是 10.01 / -10.01 / 0.01 / -0.01。
with t as (
    select * from (values
        ('a', cast(10.00 as decimal(18,2))), ('a', cast(10.01 as decimal(18,2))),
        ('b', cast(-10.00 as decimal(18,2))), ('b', cast(-10.01 as decimal(18,2))),
        ('c', cast(0.00 as decimal(18,2))), ('c', cast(0.01 as decimal(18,2))),
        ('d', cast(-0.01 as decimal(18,2))), ('d', cast(0.00 as decimal(18,2)))
    ) as v(g, p)
)
select
    g,
    typeof(avg(p)) as avg_type_old,
    round(avg(p), 2) as old_round_avg,
    typeof(sum(cast(p * 100 as bigint))) as cents_sum_type,
    cast(
        cast(
            sign(sum(cast(p * 100 as bigint)))
            * ((2 * abs(sum(cast(p * 100 as bigint))) + count(*)) // (2 * count(*)))
        as bigint) * 0.01
    as decimal(18, 2)) as new_avg,
    typeof(
        cast(
            cast(
                sign(sum(cast(p * 100 as bigint)))
                * ((2 * abs(sum(cast(p * 100 as bigint))) + count(*)) // (2 * count(*)))
            as bigint) * 0.01
        as decimal(18, 2))
    ) as new_avg_type
from t
group by g
order by g
