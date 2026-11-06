"""逐行比较 DuckDB 与 Snowflake 上 mart_daily_price.avg_price（按 trading_date + node_id 对齐）。

用法（项目根目录）：
    uv run python scripts/compare_daily_price.py [--duckdb dbt_dev.duckdb]

Snowflake 连接只读环境变量（与 dbt 相同），不在代码里放任何密钥：
    SNOWFLAKE_ACCOUNT  DBT_SNOWFLAKE_USER  DBT_SNOWFLAKE_PRIVATE_KEY_PATH  DBT_ENV_SECRET_SNOWFLAKE_PASSPHRASE
只读查询，不修改任何数据。
"""
import argparse
import os
import sys
from decimal import Decimal

import duckdb
import snowflake.connector


def load_duckdb(path: str) -> dict:
    con = duckdb.connect(path, read_only=True)
    rows = con.execute(
        "select cast(trading_date as varchar), node_id, avg_price from mart_daily_price"
    ).fetchall()
    con.close()
    return {(d, n): Decimal(str(v)) for d, n, v in rows}


def load_snowflake() -> dict:
    missing = [
        k for k in (
            "SNOWFLAKE_ACCOUNT", "DBT_SNOWFLAKE_USER",
            "DBT_SNOWFLAKE_PRIVATE_KEY_PATH", "DBT_ENV_SECRET_SNOWFLAKE_PASSPHRASE",
        ) if not os.environ.get(k)
    ]
    if missing:
        sys.exit(f"缺少环境变量：{', '.join(missing)}")
    con = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["DBT_SNOWFLAKE_USER"],
        private_key_file=os.environ["DBT_SNOWFLAKE_PRIVATE_KEY_PATH"],
        private_key_file_pwd=os.environ["DBT_ENV_SECRET_SNOWFLAKE_PASSPHRASE"],
        role="NZ_TRANSFORMER",
        warehouse="WH_XS",
        database="NZ_POWER",
        schema="MART",
    )
    try:
        cur = con.cursor()
        cur.execute(
            "select to_varchar(trading_date, 'YYYY-MM-DD'), node_id, avg_price from mart_daily_price"
        )
        rows = cur.fetchall()
    finally:
        con.close()
    return {(d, n): Decimal(str(v)) for d, n, v in rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--duckdb", default="dbt_dev.duckdb")
    args = ap.parse_args()

    duck = load_duckdb(args.duckdb)
    snow = load_snowflake()

    only_duck = sorted(set(duck) - set(snow))
    only_snow = sorted(set(snow) - set(duck))
    common = sorted(set(duck) & set(snow))
    diff = [(k, duck[k], snow[k]) for k in common if duck[k] != snow[k]]

    print(f"DuckDB 行数            : {len(duck)}")
    print(f"Snowflake 行数         : {len(snow)}")
    print(f"只在 DuckDB 有的键     : {len(only_duck)}")
    print(f"只在 Snowflake 有的键  : {len(only_snow)}")
    print(f"共同键数               : {len(common)}")
    print(f"avg_price 不一致的行数 : {len(diff)}")
    print(f"avg_price 差值合计     : {sum((s - d for _, d, s in diff), Decimal(0))}  (Snowflake - DuckDB)")
    for (d, n), dv, sv in diff[:10]:
        print(f"  {d} {n}: DuckDB={dv}  Snowflake={sv}")
    sys.exit(0 if not (diff or only_duck or only_snow) else 1)


if __name__ == "__main__":
    main()
