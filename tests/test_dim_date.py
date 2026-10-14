from datetime import date
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
SQL_FILE = ROOT / "sql" / "model" / "01_dim_date.sql"
PRICES_GLOB = ROOT / "data" / "raw" / "prices" / "*.csv"


@pytest.fixture(scope="module")
def con():
    connection = duckdb.connect(":memory:")
    connection.execute(SQL_FILE.read_text())
    yield connection
    connection.close()


# A: 已知日期，逐列检查
# (date_key, year, month, quarter, day_of_week, is_weekend)
@pytest.mark.parametrize(
    "day, expected",
    [
        (date(2026, 4, 5), (20260405, 2026, 4, 2, 7, True)),
        (date(2026, 9, 26), (20260926, 2026, 9, 3, 6, True)),
        (date(2026, 10, 14), (20261014, 2026, 10, 4, 3, False)),
        (date(2028, 2, 29), (20280229, 2028, 2, 1, 2, False)),
    ],
)
def test_known_dates(con, day, expected):
    row = con.execute(
        "SELECT date_key, year, month, quarter, day_of_week, is_weekend "
        "FROM dim_date WHERE trading_date = ?",
        [day],
    ).fetchone()
    assert row == expected


# B: 边界
def test_first_row(con):
    row = con.execute(
        "SELECT trading_date, date_key FROM dim_date ORDER BY trading_date LIMIT 1"
    ).fetchone()
    assert row == (date(2020, 1, 1), 20200101)


def test_last_row(con):
    row = con.execute(
        "SELECT trading_date, date_key FROM dim_date "
        "ORDER BY trading_date DESC LIMIT 1"
    ).fetchone()
    assert row == (date(2030, 12, 31), 20301231)


def test_row_count(con):
    assert con.execute("SELECT COUNT(*) FROM dim_date").fetchone()[0] == 4018


def test_dates_are_continuous(con):
    bad = con.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT date_diff(
                'day',
                LAG(trading_date) OVER (ORDER BY trading_date),
                trading_date
            ) AS gap
            FROM dim_date
        ) WHERE gap IS NOT NULL AND gap <> 1
        """
    ).fetchone()[0]
    assert bad == 0


# C: 约束
@pytest.mark.parametrize("column", ["date_key", "trading_date"])
def test_key_columns_unique_and_not_null(con, column):
    nulls = con.execute(f"SELECT COUNT(*) FROM dim_date WHERE {column} IS NULL")
    assert nulls.fetchone()[0] == 0
    dups = con.execute(
        f"SELECT COUNT(*) FROM (SELECT {column} FROM dim_date "
        f"GROUP BY {column} HAVING COUNT(*) > 1)"
    )
    assert dups.fetchone()[0] == 0


def test_date_key_matches_trading_date(con):
    bad = con.execute(
        "SELECT COUNT(*) FROM dim_date "
        "WHERE date_key <> CAST(strftime(trading_date, '%Y%m%d') AS INTEGER)"
    ).fetchone()[0]
    assert bad == 0


def test_is_weekend_matches_day_of_week(con):
    bad = con.execute(
        "SELECT COUNT(*) FROM dim_date "
        "WHERE is_weekend <> (day_of_week IN (6, 7))"
    ).fetchone()[0]
    assert bad == 0


# D: 与真实数据衔接（没有本地数据时跳过）
def test_all_loaded_trading_dates_exist_in_dim_date(con):
    if not list(PRICES_GLOB.parent.glob("*.csv")):
        pytest.skip("no local price files")
    missing = con.execute(
        f"""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT CAST(TradingDate AS DATE) AS d
            FROM read_csv_auto('{PRICES_GLOB}')
        ) p
        LEFT JOIN dim_date d ON d.trading_date = p.d
        WHERE d.date_key IS NULL
        """
    ).fetchone()[0]
    assert missing == 0
