import os
from datetime import date, datetime
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
    """两张日期相关维度只建一次，每个测试重建其余对象。"""
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
    for name in [
        "04_dim_node.sql",
        "05_fact_electricity_price.sql",
        "06_v_dim_node.sql",
        "07_mart_current_price.sql",
        "08_mart_daily_price.sql",
    ]:
        con.execute(sql(name))
    return con


def file_name(day, version):
    return f"{day.replace('-', '')}_{version}.csv"


def count(con, query):
    return con.execute(query).fetchone()[0]


def describe(con, table):
    return [(c[0], c[1]) for c in con.execute(f"DESCRIBE {table}").fetchall()]


# ---------------------------------------------------------------- v_dim_node
def first_seen(con):
    rows = con.execute(
        "SELECT node_id, first_seen_date FROM v_dim_node ORDER BY node_id"
    ).fetchall()
    return dict(rows)


def test_v1_single_day_means_every_node_is_baseline(base):
    load(
        base,
        [
            ("A", "2026-09-26", 1, 10.0, "final"),
            ("B", "2026-09-26", 1, 10.0, "final"),
        ],
    )
    assert first_seen(base) == {"A": None, "B": None}


def test_v2_node_appearing_later_gets_its_first_date(base):
    load(
        base,
        [
            ("A", "2026-09-26", 1, 10.0, "final"),
            ("B", "2026-09-26", 1, 10.0, "final"),
            ("A", "2026-09-27", 1, 10.0, "final"),
            ("B", "2026-09-27", 1, 10.0, "final"),
            ("C", "2026-09-27", 1, 10.0, "final"),
        ],
    )
    assert first_seen(base) == {"A": None, "B": None, "C": date(2026, 9, 27)}


def test_v3_backfilling_earlier_data_turns_values_back_into_null(base):
    rows = [
        ("A", "2026-09-26", 1, 10.0, "final"),
        ("B", "2026-09-26", 1, 10.0, "final"),
        ("C", "2026-09-27", 1, 10.0, "final"),
    ]
    load(base, rows)
    assert first_seen(base)["C"] == date(2026, 9, 27)
    load(base, rows + [(n, "2026-09-20", 1, 10.0, "final") for n in "ABC"])
    assert first_seen(base) == {"A": None, "B": None, "C": None}


def test_v4_columns_and_types(base):
    load(base, [("A", "2026-09-26", 1, 10.0, "final")])
    assert describe(base, "v_dim_node") == [
        ("node_key", "BIGINT"),
        ("node_id", "VARCHAR"),
        ("node_name", "VARCHAR"),
        ("island", "VARCHAR"),
        ("region", "VARCHAR"),
        ("first_seen_date", "DATE"),
    ]


def test_v5_has_one_row_per_dim_node_row(base):
    load(base, [(n, "2026-09-26", 1, 10.0, "final") for n in ["A", "B", "C"]])
    assert count(base, "SELECT COUNT(*) FROM v_dim_node") == 3


# --------------------------------------------------------- mart_current_price
def test_m1_final_wins_over_interim_with_different_prices(base):
    load(
        base,
        [
            ("A", "2026-09-26", 1, 100.0, "interim"),
            ("A", "2026-09-26", 1, 10.0, "final"),
        ],
    )
    rows = base.execute(
        "SELECT price_nzd_per_mwh, price_version FROM mart_current_price"
    ).fetchall()
    assert rows == [(Decimal("10.00"), "final")]


def test_m2_interim_is_used_when_there_is_no_final(base):
    load(base, [("A", "2026-09-26", 1, 12.5, "interim")])
    rows = base.execute(
        "SELECT price_nzd_per_mwh, price_version FROM mart_current_price"
    ).fetchall()
    assert rows == [(Decimal("12.50"), "interim")]


def test_m3_one_row_per_period_and_node(base):
    load(
        base,
        [
            ("A", "2026-09-26", 1, 10.0, "interim"),
            ("A", "2026-09-26", 1, 11.0, "final"),
            ("A", "2026-09-26", 2, 12.0, "interim"),
            ("B", "2026-09-26", 1, 13.0, "final"),
            ("B", "2026-09-26", 2, 14.0, "final"),
            ("B", "2026-09-26", 2, 15.0, "interim"),
        ],
    )
    assert count(base, "SELECT COUNT(*) FROM mart_current_price") == 4
    dup = count(
        base,
        "SELECT COUNT(*) FROM (SELECT period_key, node_key "
        "FROM mart_current_price GROUP BY ALL HAVING COUNT(*) > 1)",
    )
    assert dup == 0


def test_m4_columns_and_types(base):
    load(base, [("A", "2026-09-26", 1, 10.0, "final")])
    assert describe(base, "mart_current_price") == [
        ("period_key", "BIGINT"),
        ("node_key", "BIGINT"),
        ("trading_date", "DATE"),
        ("trading_period", "SMALLINT"),
        ("period_start_local", "TIMESTAMP"),
        ("node_id", "VARCHAR"),
        ("price_nzd_per_mwh", "DECIMAL(18,2)"),
        ("price_version", "VARCHAR"),
    ]


def test_m5_readable_columns_are_filled_from_dimensions(base):
    load(base, [("aby0111", "2026-09-26", 2, 15.55, "final")])
    row = base.execute(
        "SELECT trading_date, trading_period, period_start_local, node_id, "
        "price_nzd_per_mwh FROM mart_current_price"
    ).fetchone()
    assert row == (
        date(2026, 9, 26),
        2,
        datetime(2026, 9, 26, 0, 30),
        "ABY0111",
        Decimal("15.55"),
    )


def test_m6_rebuild_is_idempotent(base):
    load(
        base,
        [
            ("B", "2026-09-26", 2, 11.0, "final"),
            ("A", "2026-09-26", 1, 10.0, "interim"),
            ("A", "2026-09-26", 1, 10.5, "final"),
        ],
    )
    before = base.execute("SELECT * FROM mart_current_price").fetchall()
    base.execute(sql("07_mart_current_price.sql"))
    assert base.execute("SELECT * FROM mart_current_price").fetchall() == before


def test_m7_empty_input_gives_empty_tables(base):
    load(base, [])
    assert count(base, "SELECT COUNT(*) FROM mart_current_price") == 0
    assert count(base, "SELECT COUNT(*) FROM mart_daily_price") == 0
    assert count(base, "SELECT COUNT(*) FROM v_dim_node") == 0


# ----------------------------------------------------------- mart_daily_price
def daily(con):
    return con.execute(
        "SELECT avg_price, min_price, max_price, period_count, "
        "interim_period_count FROM mart_daily_price"
    ).fetchall()


def test_d1_statistics_of_one_day(base):
    prices = [(1, 10.0), (2, 20.0), (3, 30.0)]
    load(base, [("A", "2026-09-26", p, price, "final") for p, price in prices])
    assert daily(base) == [
        (Decimal("20.00"), Decimal("10.00"), Decimal("30.00"), 3, 0)
    ]


def test_d2_interim_periods_are_counted(base):
    load(
        base,
        [
            ("A", "2026-09-26", 1, 10.0, "final"),
            ("A", "2026-09-26", 2, 20.0, "final"),
            ("A", "2026-09-26", 3, 30.0, "interim"),
        ],
    )
    assert daily(base) == [
        (Decimal("20.00"), Decimal("10.00"), Decimal("30.00"), 3, 1)
    ]


def test_d3_final_replaces_interim_in_the_daily_numbers(base):
    load(
        base,
        [
            ("A", "2026-09-26", 1, 100.0, "interim"),
            ("A", "2026-09-26", 1, 10.0, "final"),
        ],
    )
    assert daily(base) == [
        (Decimal("10.00"), Decimal("10.00"), Decimal("10.00"), 1, 0)
    ]


def test_d4_dst_days_have_50_and_46_periods(base):
    load(
        base,
        [("A", "2026-04-05", p, 10.0, "final") for p in range(1, 51)]
        + [("A", "2026-09-27", p, 10.0, "final") for p in range(1, 47)],
    )
    rows = base.execute(
        "SELECT trading_date, period_count FROM mart_daily_price "
        "ORDER BY trading_date"
    ).fetchall()
    assert rows == [(date(2026, 4, 5), 50), (date(2026, 9, 27), 46)]


def test_d5_average_is_rounded_to_two_decimals(base):
    load(
        base,
        [
            ("A", "2026-09-26", 1, 10.00, "final"),
            ("A", "2026-09-26", 2, 10.00, "final"),
            ("A", "2026-09-26", 3, 10.01, "final"),
        ],
    )
    assert daily(base)[0][0] == Decimal("10.00")


def test_d6_one_row_per_day_and_node(base):
    load(
        base,
        [
            (node, day, 1, 10.0, "final")
            for node in ["A", "B"]
            for day in ["2026-09-26", "2026-09-27"]
        ],
    )
    assert count(base, "SELECT COUNT(*) FROM mart_daily_price") == 4


def test_d7_columns_and_types(base):
    load(base, [("A", "2026-09-26", 1, 10.0, "final")])
    assert describe(base, "mart_daily_price") == [
        ("trading_date", "DATE"),
        ("node_key", "BIGINT"),
        ("node_id", "VARCHAR"),
        ("avg_price", "DECIMAL(18,2)"),
        ("min_price", "DECIMAL(18,2)"),
        ("max_price", "DECIMAL(18,2)"),
        ("period_count", "BIGINT"),
        ("interim_period_count", "BIGINT"),
    ]


# ------------------------------------------- 与真实数据衔接（没有数据时跳过）
@pytest.fixture(scope="module")
def real():
    if not list(PRICES_DIR.glob("*.csv")):
        pytest.skip("no local price files")
    con = duckdb.connect(":memory:")
    previous = Path.cwd()
    os.chdir(ROOT)
    try:
        for path in sorted(SQL_DIR.glob("0*.sql")):
            con.execute(path.read_text())
    finally:
        os.chdir(previous)
    yield con
    con.close()


def test_r1_current_price_has_one_row_per_period_and_node(real):
    expected = count(
        real,
        "SELECT COUNT(*) FROM (SELECT DISTINCT period_key, node_key "
        "FROM fact_electricity_price)",
    )
    assert count(real, "SELECT COUNT(*) FROM mart_current_price") == expected


def test_r2_daily_period_counts_add_up_to_current_price_rows(real):
    total = count(real, "SELECT SUM(period_count) FROM mart_daily_price")
    assert total == count(real, "SELECT COUNT(*) FROM mart_current_price")


def test_r3_every_node_has_50_periods_on_2026_04_05(real):
    if not (PRICES_DIR / "20260405_final.csv").exists():
        pytest.skip("20260405_final.csv not available")
    rows = real.execute(
        "SELECT DISTINCT period_count FROM mart_daily_price "
        "WHERE trading_date = DATE '2026-04-05'"
    ).fetchall()
    assert rows == [(50,)]


def test_r4_nodes_of_the_earliest_file_are_baseline(real):
    path = PRICES_DIR / "20260405_final.csv"
    if not path.exists():
        pytest.skip("20260405_final.csv not available")
    not_null = count(
        real,
        f"""
        SELECT COUNT(*) FROM v_dim_node
        WHERE first_seen_date IS NOT NULL
          AND node_id IN (
              SELECT DISTINCT upper(PointOfConnection)
              FROM read_csv_auto('{path}'))
        """,
    )
    assert not_null == 0
