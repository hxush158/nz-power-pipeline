-- mart_current_price 每个 (period_key, node_key) 只能有一行。
select period_key, node_key, count(*) as n
from {{ ref('mart_current_price') }}
group by period_key, node_key
having count(*) > 1
