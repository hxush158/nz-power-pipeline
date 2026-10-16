import os
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql" / "model"
PRICES_DIR = ROOT / "data" / "raw" / "prices"


def sql(name):
    return (SQL_DIR / name).read_text()


@pytest.fixture(scope="module")
def base():
    """两张日期相关维度只建一次，每个测试重建 stg_prices / dim_node / fact。"""
    con = duckdb.connect(":memory:")
    con.execute(sql("01_dim_date.sql"))
    con.execute(sql("02_dim_trading_period.sql"))
    yield con
    con.close()


def load(con, rows):
    """rows: [(node_id, trading_date, period, price, price_version), ...]"""
    con.execute(
        """
        CREATE OR REPLACE TABLE stg_prices (
            trading_date DATE,
            trading_period SMALLINT,
            node_id VARCHAR,
            price_nzd_per_mwh DOUBLE,
            price_version VARCHAR,
            source_file VARCHAR
        )
        """
    )
    if rows:  # executemany 不接受空列表
        con.executemany(
            "INSERT INTO stg_prices VALUES (?, ?, ?, ?, ?, ?)",
            [
                (day, period, node, price, version, file_name(day, version))
                for node, day, period, price, version in rows
            ],
        )
    con.execute(sql("04_dim_node.sql"))
    con.execute(sql("05_fact_electricity_price.sql"))
    return con


def file_name(day, version):
    return f"{day.replace('-', '')}_{version}.csv"


def count(con, query):
    return con.execute(query).fetchone()[0]


PK_DUPLICATE_GROUPS = """
    SELECT COUNT(*) FROM (
        SELECT period_key, node_key, price_version
        FROM fact_electricity_price
        GROUP BY ALL HAVING COUNT(*) > 1
    )
"""


def test_f1_interim_and_final_coexist_with_their_own_prices(base):
    load(
        base,
        [
            ("ABY0111", "2026-09-26", 1, 10.0, "interim"),
            ("ABY0111", "2026-09-26", 1, 12.5, "final"),
        ],
    )
    rows = base.execute(
        "SELECT price_version, price_nzd_per_mwh FROM fact_electricity_price "
        "ORDER BY price_version"
    ).fetchall()
    assert rows == [("final", Decimal("12.50")), ("interim", Decimal("10.00"))]


def test_f2_primary_key_is_unique(base):
    load(
        base,
        [
            (node, "2026-09-26", period, 10.0, version)
            for node in ["A", "B"]
            for period in [1, 2, 3]
            for version in ["interim", "final"]
        ],
    )
    assert count(base, "SELECT COUNT(*) FROM fact_electricity_price") == 12
    assert count(base, PK_DUPLICATE_GROUPS) == 0


def test_f3_foreign_keys_resolve(base):
    load(
        base,
        [
            ("A", "2026-09-26", 1, 10.0, "final"),
            ("B", "2026-09-27", 3, 11.0, "final"),
        ],
    )
    orphan_periods = count(
        base,
        "SELECT COUNT(*) FROM fact_electricity_price AS f "
        "LEFT JOIN dim_trading_period AS p ON p.period_key = f.period_key "
        "WHERE p.period_key IS NULL",
    )
    orphan_nodes = count(
        base,
        "SELECT COUNT(*) FROM fact_electricity_price AS f "
        "LEFT JOIN dim_node AS n ON n.node_key = f.node_key "
        "WHERE n.node_key IS NULL",
    )
    assert (orphan_periods, orphan_nodes) == (0, 0)


def test_f4_values_are_preserved_including_negative_prices(base):
    load(
        base,
        [
            ("ABY0111", "2026-09-26", 1, 15.55, "final"),
            ("ABY0111", "2026-09-26", 2, -0.19, "final"),
        ],
    )
    rows = base.execute(
        "SELECT period_key, price_version, price_nzd_per_mwh, source_file "
        "FROM fact_electricity_price ORDER BY period_key"
    ).fetchall()
    assert rows == [
        (2026092601, "final", Decimal("15.55"), "20260926_final.csv"),
        (2026092602, "final", Decimal("-0.19"), "20260926_final.csv"),
    ]


def test_f5_node_ids_differing_only_in_case_share_one_node_key(base):
    load(
        base,
        [
            ("aby0111", "2026-09-26", 1, 10.0, "final"),
            ("ABY0111", "2026-09-27", 1, 11.0, "final"),
        ],
    )
    row = base.execute(
        "SELECT COUNT(*), COUNT(DISTINCT node_key) FROM fact_electricity_price"
    ).fetchone()
    assert row == (2, 1)


def test_f6_case_collision_is_not_hidden_it_shows_up_as_duplicate_key(base):
    load(
        base,
        [
            ("aby0111", "2026-09-26", 1, 10.0, "final"),
            ("ABY0111", "2026-09-26", 1, 11.0, "final"),
        ],
    )
    assert count(base, "SELECT COUNT(*) FROM fact_electricity_price") == 2
    assert count(base, PK_DUPLICATE_GROUPS) == 1


def test_f7_rows_without_a_matching_dimension_are_excluded(base):
    load(
        base,
        [
            ("A", "2026-09-26", 1, 10.0, "final"),
            (None, "2026-09-26", 2, 10.0, "final"),  # 空 node_id
            ("A", "2026-09-26", 49, 10.0, "final"),  # 普通日没有第 49 个时段
        ],
    )
    stg = count(base, "SELECT COUNT(*) FROM stg_prices")
    fact = count(base, "SELECT COUNT(*) FROM fact_electricity_price")
    assert (stg, fact) == (3, 1)  # 对账不平 = 有行被排除，真实数据测试会据此失败


def test_f8_rebuild_is_idempotent(base):
    load(
        base,
        [
            ("B", "2026-09-26", 2, 11.0, "final"),
            ("A", "2026-09-26", 1, 10.0, "interim"),
            ("A", "2026-09-26", 1, 10.5, "final"),
        ],
    )
    before = base.execute("SELECT * FROM fact_electricity_price").fetchall()
    base.execute(sql("05_fact_electricity_price.sql"))
    assert base.execute("SELECT * FROM fact_electricity_price").fetchall() == before


def test_f9_dst_days_accept_exactly_46_and_50_periods(base):
    load(
        base,
        [("A", "2026-04-05", p, 10.0, "final") for p in range(1, 52)]
        + [("A", "2026-09-27", p, 10.0, "final") for p in range(1, 48)],
    )
    rows = base.execute(
        "SELECT p.date_key, COUNT(*) FROM fact_electricity_price AS f "
        "JOIN dim_trading_period AS p ON p.period_key = f.period_key "
        "GROUP BY p.date_key ORDER BY p.date_key"
    ).fetchall()
    assert rows == [(20260405, 50), (20260927, 46)]


def test_f10_column_types_and_order(base):
    load(base, [("A", "2026-09-26", 1, 10.0, "final")])
    described = base.execute("DESCRIBE fact_electricity_price").fetchall()
    cols = [(c[0], c[1]) for c in described]
    assert cols == [
        ("period_key", "BIGINT"),
        ("node_key", "BIGINT"),
        ("price_version", "VARCHAR"),
        ("price_nzd_per_mwh", "DECIMAL(18,2)"),
        ("source_file", "VARCHAR"),
    ]


def test_f11_empty_input_gives_empty_table(base):
    load(base, [])
    assert count(base, "SELECT COUNT(*) FROM fact_electricity_price") == 0


# R: 与真实数据衔接（没有本地数据时跳过）
@pytest.fixture(scope="module")
def real():
    if not list(PRICES_DIR.glob("*.csv")):
        pytest.skip("no local price files")
    con = duckdb.connect(":memory:")
    previous = Path.cwd()
    os.chdir(ROOT)
    try:
        for name in [
            "01_dim_date.sql",
            "02_dim_trading_period.sql",
            "03_stg_prices.sql",
            "04_dim_node.sql",
            "05_fact_electricity_price.sql",
        ]:
            con.execute(sql(name))
    finally:
        os.chdir(previous)
    yield con
    con.close()


def test_r1_fact_rows_reconcile_with_stg_prices(real):
    stg = count(real, "SELECT COUNT(*) FROM stg_prices")
    fact = count(real, "SELECT COUNT(*) FROM fact_electricity_price")
    assert fact == stg, f"{stg - fact} rows were dropped by the dimension joins"


def test_r2_rows_per_version_match_stg_prices(real):
    stg = real.execute(
        "SELECT price_version, COUNT(*) FROM stg_prices GROUP BY 1 ORDER BY 1"
    ).fetchall()
    fact = real.execute(
        "SELECT price_version, COUNT(*) FROM fact_electricity_price "
        "GROUP BY 1 ORDER BY 1"
    ).fetchall()
    assert fact == stg


def test_r3_primary_key_is_unique_on_real_data(real):
    assert count(real, PK_DUPLICATE_GROUPS) == 0


def test_r4_foreign_keys_resolve_on_real_data(real):
    bad = count(
        real,
        "SELECT COUNT(*) FROM fact_electricity_price AS f "
        "LEFT JOIN dim_trading_period AS p ON p.period_key = f.period_key "
        "LEFT JOIN dim_node AS n ON n.node_key = f.node_key "
        "WHERE p.period_key IS NULL OR n.node_key IS NULL",
    )
    assert bad == 0
