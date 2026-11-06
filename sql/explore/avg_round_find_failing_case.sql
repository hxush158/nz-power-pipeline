-- DuckDB：找出旧写法 round(avg(DECIMAL), 2) 进位错的"相邻两分"价格对，用来写一个在旧代码上会失败的单元测试。
-- 每一对价格是 a/100 和 (a+1)/100，平均值恰好是 x.xx5；严格四舍五入（远离零）应得 (a+1)/100。
-- 用法：
--   uv run python -c "import duckdb; [print(r) for r in duckdb.sql(open('sql/explore/avg_round_find_failing_case.sql').read()).fetchall()]"
-- 输出列：price_low, price_high, old_round_avg, exact_avg, total_failing_pairs（总共有多少对旧写法算错）
with cents as (
    select range as a from range(0, 100000)
),
long_t as (
    select a, cast(a / 100.0 as decimal(18, 2)) as p from cents
    union all
    select a, cast((a + 1) / 100.0 as decimal(18, 2)) as p from cents
),
calc as (
    select
        a,
        min(p) as price_low,
        max(p) as price_high,
        round(avg(p), 2) as old_round_avg,
        cast((a + 1) / 100.0 as decimal(18, 2)) as exact_avg
    from long_t
    group by a
)
select price_low, price_high, old_round_avg, exact_avg, count(*) over () as total_failing_pairs
from calc
where old_round_avg <> exact_avg
order by a
limit 5
