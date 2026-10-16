from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql" / "model"
PRICES_DIR = ROOT / "data" / "raw" / "prices"
DIM_NODE_SQL = (SQL_DIR / "04_dim_node.sql").read_text()


def build(rows):
    """用手工造的 stg_prices 构建 dim_node。

    rows: [(node_id, trading_date, price_version), ...]，其余列填固定值。
    """
    con = duckdb.connect(":memory:")
    con.execute(
        """
        CREATE TABLE stg_prices (
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
            "INSERT INTO stg_prices VALUES (?, 1, ?, 10.0, ?, ?)",
            [
                (day, node, version, f"{day.replace('-', '')}_{version}.csv")
                for node, day, version in rows
            ],
        )
    con.execute(DIM_NODE_SQL)
    return con


def node_ids(con):
    rows = con.execute("SELECT node_id FROM dim_node ORDER BY 1").fetchall()
    return [r[0] for r in rows]


def test_d1_same_node_in_many_rows_appears_once():
    con = build(
        [
            ("ABY0111", "2026-09-26", "final"),
            ("ABY0111", "2026-09-26", "interim"),
            ("ABY0111", "2026-09-27", "final"),
            ("ALB0331", "2026-09-26", "final"),
        ]
    )
    assert node_ids(con) == ["ABY0111", "ALB0331"]


def test_d2_node_appearing_on_a_later_day_is_included():
    con = build(
        [
            ("A", "2026-09-26", "final"),
            ("B", "2026-09-26", "final"),
            ("A", "2026-09-27", "final"),
            ("B", "2026-09-27", "final"),
            ("C", "2026-09-27", "final"),
        ]
    )
    assert node_ids(con) == ["A", "B", "C"]


def test_d3_null_empty_and_blank_node_ids_are_excluded():
    con = build(
        [
            (None, "2026-09-26", "final"),
            ("", "2026-09-26", "final"),
            ("   ", "2026-09-26", "final"),
            ("ABY0111", "2026-09-26", "final"),
        ]
    )
    assert node_ids(con) == ["ABY0111"]


def test_d4_non_empty_dirty_values_are_kept_as_is():
    con = build(
        [
            (" ABY0111", "2026-09-26", "final"),
            ("ABY0111", "2026-09-26", "final"),
        ]
    )
    assert node_ids(con) == [" ABY0111", "ABY0111"]


def test_d5_keys_are_unique_and_not_null():
    con = build([(n, "2026-09-26", "final") for n in ["A", "B", "C", "D"]])
    nulls = con.execute(
        "SELECT COUNT(*) FROM dim_node WHERE node_key IS NULL OR node_id IS NULL"
    ).fetchone()[0]
    distinct = con.execute(
        "SELECT COUNT(DISTINCT node_key), COUNT(DISTINCT node_id), COUNT(*) "
        "FROM dim_node"
    ).fetchone()
    assert nulls == 0
    assert distinct == (4, 4, 4)


def test_d6_node_key_is_stable_when_new_nodes_appear():
    first = build([(n, "2026-09-26", "final") for n in ["A", "B"]])
    second = build([(n, "2026-09-27", "final") for n in ["A", "B", "C"]])
    query = "SELECT node_id, node_key FROM dim_node WHERE node_id IN ('A', 'B')"
    assert first.execute(query).fetchall() == second.execute(query).fetchall()


def test_d7_attribute_columns_are_null():
    con = build([("ABY0111", "2026-09-26", "final")])
    row = con.execute("SELECT node_name, island, region FROM dim_node").fetchone()
    assert row == (None, None, None)


def test_d8_rebuild_is_idempotent():
    con = build([(n, "2026-09-26", "final") for n in ["B", "A", "C"]])
    before = con.execute("SELECT * FROM dim_node").fetchall()
    con.execute(DIM_NODE_SQL)
    assert con.execute("SELECT * FROM dim_node").fetchall() == before


def test_d9_empty_input_gives_empty_table():
    con = build([])
    assert con.execute("SELECT COUNT(*) FROM dim_node").fetchone()[0] == 0


def test_d10_column_types():
    con = build([("ABY0111", "2026-09-26", "final")])
    cols = [(c[0], c[1]) for c in con.execute("DESCRIBE dim_node").fetchall()]
    assert cols == [
        ("node_key", "BIGINT"),
        ("node_id", "VARCHAR"),
        ("node_name", "VARCHAR"),
        ("island", "VARCHAR"),
        ("region", "VARCHAR"),
    ]


def test_d11_node_id_is_case_insensitive_and_stored_upper():
    con = build(
        [
            ("aby0111", "2026-09-26", "final"),
            ("ABY0111", "2026-09-27", "final"),
            ("Aby0111", "2026-09-28", "final"),
        ]
    )
    assert node_ids(con) == ["ABY0111"]


# R: 与真实数据衔接（没有本地数据时跳过）
@pytest.fixture
def real_con(monkeypatch):
    if not list(PRICES_DIR.glob("*.csv")):
        pytest.skip("no local price files")
    monkeypatch.chdir(ROOT)
    con = duckdb.connect(":memory:")
    con.execute((SQL_DIR / "03_stg_prices.sql").read_text())
    con.execute(DIM_NODE_SQL)
    yield con
    con.close()


def test_r1_node_count_matches_distinct_nodes_in_files(real_con):
    expected = real_con.execute(
        "SELECT COUNT(DISTINCT upper(PointOfConnection)) "
        "FROM read_csv_auto('data/raw/prices/*.csv')"
    ).fetchone()[0]
    actual = real_con.execute("SELECT COUNT(*) FROM dim_node").fetchone()[0]
    assert actual == expected
    assert actual >= 246


def test_r2_all_nodes_of_the_2026_04_05_file_are_present(real_con):
    path = PRICES_DIR / "20260405_final.csv"
    if not path.exists():
        pytest.skip("20260405_final.csv not available")
    missing = real_con.execute(
        f"""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT upper(PointOfConnection) AS node_id
            FROM read_csv_auto('{path}')
        ) AS f
        LEFT JOIN dim_node AS d ON d.node_id = f.node_id
        WHERE d.node_key IS NULL
        """
    ).fetchone()[0]
    assert missing == 0


def test_r3_stg_prices_has_no_null_or_empty_node_id(real_con):
    bad = real_con.execute(
        "SELECT COUNT(*) FROM stg_prices "
        "WHERE node_id IS NULL OR trim(node_id) = ''"
    ).fetchone()[0]
    assert bad == 0
