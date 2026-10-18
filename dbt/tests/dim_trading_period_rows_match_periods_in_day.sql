-- 每个交易日在 dim_trading_period 里的行数，必须等于它自己标的 periods_in_day。
-- 返回的每一行都是行数对不上的交易日。
select
    date_key,
    max(periods_in_day) as periods_in_day,
    count(*) as actual_rows
from {{ ref('dim_trading_period') }}
group by date_key
having count(*) <> max(periods_in_day)
