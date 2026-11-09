-- fact_generation 的主键 (period_key, plant_key) 必须唯一。返回的每一行都是重复的键。
select period_key, plant_key, count(*) as n
from {{ ref('fact_generation') }}
group by period_key, plant_key
having count(*) > 1
