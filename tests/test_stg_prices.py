from datetime import date
from pathlib import Path

import duckdb
import pytest

SQL_FILE = Path(__file__).resolve().parents[1] / "sql" / "model" / "03_stg_prices.sql"
HEADER = "TradingDate,TradingPeriod,PointOfConnection,DollarsPerMegawattHour\n"


@pytest.fixture
def con(tmp_path, monkeypatch):
    """在临时目录里造 data/raw/prices，再从那里执行 SQL（路径是相对的）。"""
    prices = tmp_path / "data" / "raw" / "prices"
    prices.mkdir(parents=True)
    (prices / "20260926_final.csv").write_text(
        HEADER + "2026-09-26,1,ABY0111,15.55\n2026-09-26,2,0001,-0.19\n"
    )
    (prices / "20260926_interim.csv").write_text(
        HEADER + "2026-09-26,1,ABY0111,16.00\n"
    )
    (prices / "notes.csv").write_text(HEADER + "2026-09-26,1,XXX9999,1.00\n")
    monkeypatch.chdir(tmp_path)
    connection = duckdb.connect(":memory:")
    connection.execute(SQL_FILE.read_text())
    yield connection
    connection.close()


def test_columns_and_types(con):
    cols = con.execute("DESCRIBE stg_prices").fetchall()
    assert [(c[0], c[1]) for c in cols] == [
        ("trading_date", "DATE"),
        ("trading_period", "SMALLINT"),
        ("node_id", "VARCHAR"),
        ("price_nzd_per_mwh", "DOUBLE"),
        ("price_version", "VARCHAR"),
        ("source_file", "VARCHAR"),
    ]


def test_version_and_source_file_come_from_file_name(con):
    rows = con.execute(
        "SELECT price_version, source_file, COUNT(*) FROM stg_prices "
        "GROUP BY ALL ORDER BY price_version"
    ).fetchall()
    assert rows == [
        ("final", "20260926_final.csv", 2),
        ("interim", "20260926_interim.csv", 1),
    ]


def test_files_with_other_names_are_ignored(con):
    n = con.execute(
        "SELECT COUNT(*) FROM stg_prices WHERE node_id = 'XXX9999'"
    ).fetchone()[0]
    assert n == 0


def test_values_are_read_faithfully(con):
    row = con.execute(
        "SELECT trading_date, trading_period, node_id, price_nzd_per_mwh "
        "FROM stg_prices WHERE source_file = '20260926_final.csv' "
        "AND trading_period = 1"
    ).fetchone()
    assert row == (date(2026, 9, 26), 1, "ABY0111", 15.55)


def test_numeric_looking_node_id_keeps_leading_zeros(con):
    ids = con.execute(
        "SELECT node_id FROM stg_prices WHERE trading_period = 2"
    ).fetchall()
    assert ids == [("0001",)]


def test_no_matching_files_raises_error(tmp_path, monkeypatch):
    # 完全没有原始文件是故障，不是正常状态：必须报错，不能静默得到空表。
    (tmp_path / "data" / "raw" / "prices").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    connection = duckdb.connect(":memory:")
    with pytest.raises(duckdb.IOException):
        connection.execute(SQL_FILE.read_text())
        connection.execute("SELECT * FROM stg_prices").fetchall()
    connection.close()
