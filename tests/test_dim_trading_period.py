from datetime import datetime
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql" / "model"
PRICES_GLOB = ROOT / "data" / "raw" / "prices" / "*.csv"


@pytest.fixture(scope="module")
def con():
    connection = duckdb.connect(":memory:")
    connection.execute((SQL_DIR / "01_dim_date.sql").read_text())
    connection.execute((SQL_DIR / "02_dim_trading_period.sql").read_text())
    yield connection
    connection.close()


# A: 每日时段数
@pytest.mark.parametrize(
    "date_key, expected",
    [
        pytest.param(20261014, 48, id="A1-normal-day"),
        pytest.param(20260405, 50, id="A2-dst-end"),
        pytest.param(20260927, 46, id="A3-dst-start"),
    ],
)
def test_periods_per_day(con, date_key, expected):
    row = con.execute(
        "SELECT MIN(periods_in_day), MAX(periods_in_day), COUNT(*) "
        "FROM dim_trading_period WHERE date_key = ?",
        [date_key],
    ).fetchone()
    assert row == (expected, expected, expected)


# B: 关键时段。时间一律以"不带时区的 UTC"取出，避免依赖 pytz 和会话时区。
# (period_key, start_utc, end_utc, start_local)
@pytest.mark.parametrize(
    "date_key, period, expected",
    [
        pytest.param(
            20261014,
            1,
            (
                2026101401,
                datetime(2026, 10, 13, 11, 0),
                datetime(2026, 10, 13, 11, 30),
                datetime(2026, 10, 14, 0, 0),
            ),
            id="B1",
        ),
        pytest.param(
            20261014,
            48,
            (
                2026101448,
                datetime(2026, 10, 14, 10, 30),
                datetime(2026, 10, 14, 11, 0),
                datetime(2026, 10, 14, 23, 30),
            ),
            id="B2",
        ),
        pytest.param(
            20260405,
            1,
            (
                2026040501,
                datetime(2026, 4, 4, 11, 0),
                datetime(2026, 4, 4, 11, 30),
                datetime(2026, 4, 5, 0, 0),
            ),
            id="B3",
        ),
        pytest.param(
            20260405,
            6,
            (
                2026040506,
                datetime(2026, 4, 4, 13, 30),
                datetime(2026, 4, 4, 14, 0),
                datetime(2026, 4, 5, 2, 30),
            ),
            id="B4",
        ),
        pytest.param(
            20260405,
            7,
            (
                2026040507,
                datetime(2026, 4, 4, 14, 0),
                datetime(2026, 4, 4, 14, 30),
                datetime(2026, 4, 5, 2, 0),
            ),
            id="B5",
        ),
        pytest.param(
            20260405,
            50,
            (
                2026040550,
                datetime(2026, 4, 5, 11, 30),
                datetime(2026, 4, 5, 12, 0),
                datetime(2026, 4, 5, 23, 30),
            ),
            id="B6",
        ),
        pytest.param(
            20260927,
            4,
            (
                2026092704,
                datetime(2026, 9, 26, 13, 30),
                datetime(2026, 9, 26, 14, 0),
                datetime(2026, 9, 27, 1, 30),
            ),
            id="B7",
        ),
        pytest.param(
            20260927,
            5,
            (
                2026092705,
                datetime(2026, 9, 26, 14, 0),
                datetime(2026, 9, 26, 14, 30),
                datetime(2026, 9, 27, 3, 0),
            ),
            id="B8",
        ),
        pytest.param(
            20260927,
            46,
            (
                2026092746,
                datetime(2026, 9, 27, 10, 30),
                datetime(2026, 9, 27, 11, 0),
                datetime(2026, 9, 27, 23, 30),
            ),
            id="B9",
        ),
    ],
)
def test_key_periods(con, date_key, period, expected):
    row = con.execute(
        """
        SELECT
            period_key,
            period_start_utc AT TIME ZONE 'UTC',
            period_end_utc AT TIME ZONE 'UTC',
            period_start_local
        FROM dim_trading_period
        WHERE date_key = ? AND trading_period = ?
        """,
        [date_key, period],
    ).fetchone()
    assert row == expected


# C: 约束
def test_total_row_count(con):
    # 4018 天 × 48，每年多 2 个（50 时段日）又少 2 个（46 时段日），净增 0。
    assert con.execute("SELECT COUNT(*) FROM dim_trading_period").fetchone()[0] == (
        192864
    )


def test_each_year_has_one_dst_end_and_one_dst_start_day(con):
    rows = con.execute(
        """
        SELECT periods_in_day, COUNT(DISTINCT date_key)
        FROM dim_trading_period
        WHERE periods_in_day <> 48
        GROUP BY periods_in_day ORDER BY periods_in_day
        """
    ).fetchall()
    assert rows == [(46, 11), (50, 11)]


def test_period_key_unique_and_not_null(con):
    nulls = con.execute(
        "SELECT COUNT(*) FROM dim_trading_period WHERE period_key IS NULL"
    ).fetchone()[0]
    dups = con.execute(
        "SELECT COUNT(*) FROM (SELECT period_key FROM dim_trading_period "
        "GROUP BY period_key HAVING COUNT(*) > 1)"
    ).fetchone()[0]
    assert (nulls, dups) == (0, 0)


def test_date_key_and_period_unique(con):
    dups = con.execute(
        "SELECT COUNT(*) FROM (SELECT date_key, trading_period "
        "FROM dim_trading_period GROUP BY date_key, trading_period "
        "HAVING COUNT(*) > 1)"
    ).fetchone()[0]
    assert dups == 0


def test_adjacent_periods_are_contiguous(con):
    bad = con.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT
                period_start_utc,
                LAG(period_end_utc) OVER (ORDER BY period_start_utc) AS prev_end
            FROM dim_trading_period
        ) WHERE prev_end IS NOT NULL AND prev_end <> period_start_utc
        """
    ).fetchone()[0]
    assert bad == 0


def test_every_date_key_exists_in_dim_date(con):
    bad = con.execute(
        "SELECT COUNT(*) FROM dim_trading_period AS p "
        "LEFT JOIN dim_date AS d ON d.date_key = p.date_key "
        "WHERE d.date_key IS NULL"
    ).fetchone()[0]
    assert bad == 0


def test_row_count_per_day_equals_periods_in_day(con):
    bad = con.execute(
        "SELECT COUNT(*) FROM ("
        "SELECT date_key FROM dim_trading_period "
        "GROUP BY date_key, periods_in_day "
        "HAVING COUNT(*) <> periods_in_day)"
    ).fetchone()[0]
    assert bad == 0


def test_every_period_is_30_minutes(con):
    bad = con.execute(
        "SELECT COUNT(*) FROM dim_trading_period "
        "WHERE epoch(period_end_utc) - epoch(period_start_utc) <> 1800"
    ).fetchone()[0]
    assert bad == 0


# C8: 与真实数据衔接（没有本地数据时跳过）
def test_all_loaded_periods_exist_in_dim_trading_period(con):
    if not list(PRICES_GLOB.parent.glob("*.csv")):
        pytest.skip("no local price files")
    missing = con.execute(
        f"""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT
                CAST(strftime(CAST(TradingDate AS DATE), '%Y%m%d') AS BIGINT) * 100
                    + TradingPeriod AS period_key
            FROM read_csv_auto('{PRICES_GLOB}')
        ) AS p
        LEFT JOIN dim_trading_period AS d ON d.period_key = p.period_key
        WHERE d.period_key IS NULL
        """
    ).fetchone()[0]
    assert missing == 0
