# tests/test_node_reference.py
# 节点参考数据：从 EMI 的 Network Supply Points（NSP）表生成每个价格节点的名称、岛、分区、配电区域。
# 规则（2026-11-07 定）：
#   1. 按节点代码（POC code）直接匹配；有 Current flag = 1 的行就只看这些行，否则看全部历史行。
#   2. 每个字段取"非空值"：开始日期最晚的行优先；同一天按 NSP 代码升序，保证结果可复现。空值跳过，不算冲突。
#   3. 找不到的节点，按站点（代码前三个字母）推出：只给岛和分区，且站点内的非空值必须一致，否则留空；
#      配电区域一律留空（输电网节点不属于任何配电网）。来源标为 derived_from_site。
#   4. 站点也找不到：全部留空，来源标为 unmatched（由 dbt 测试拦下，提醒更新参考数据）。
import csv
import glob
from pathlib import Path

import pytest

from nzpower.node_reference import build_node_reference

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "data" / "raw" / "reference" / "20261106_NetworkSupplyPointsTable.csv"
PRICES_GLOB = str(ROOT / "data" / "raw" / "prices" / "*.csv")


def nsp(poc, *, current="1", start="2010-01-01", island="NI", zone="CNI",
        region="Waikato (WEL Networks)", desc="TESTVILLE", code=None):
    """造一行 NSP 表（只含用到的列）。"""
    return {
        "POC code": poc,
        "NSP": code or f"{poc}AAAAGN",
        "Current flag": current,
        "Start date": start,
        "Island": island,
        "Zone": zone,
        "Network reporting region": region,
        "Description": desc,
    }


def build(rows, nodes, date="2026-11-06"):
    return {r["node_id"]: r for r in build_node_reference(rows, nodes, date)}


# ---------- 直接匹配 ----------

def test_direct_match_returns_all_fields():
    out = build(
        [nsp("ABY0111", island="SI", zone="LSI", region="South Canterbury (Alpine Energy)", desc="ALBURY")],
        ["ABY0111"],
    )
    r = out["ABY0111"]
    assert (r["node_name"], r["island"], r["zone"], r["region"]) == (
        "ALBURY", "SI", "LSI", "South Canterbury (Alpine Energy)")
    assert r["mapping_source"] == "nsp"


def test_current_row_preferred_over_historical():
    out = build(
        [
            nsp("AAA0111", current="0", start="2000-01-01", island="SI", zone="LSI", region="Old"),
            nsp("AAA0111", current="1", start="2010-01-01", island="NI", zone="CNI", region="New"),
        ],
        ["AAA0111"],
    )
    assert (out["AAA0111"]["island"], out["AAA0111"]["zone"], out["AAA0111"]["region"]) == ("NI", "CNI", "New")


def test_no_current_row_falls_back_to_latest_historical():
    out = build(
        [
            nsp("MDN1101", current="0", start="2002-08-16", zone="UNI", region="Whangārei and Kaipara (Northpower)"),
            nsp("MDN1101", current="0", start="1999-01-01", zone="LNI", region="Older"),
        ],
        ["MDN1101"],
    )
    assert (out["MDN1101"]["zone"], out["MDN1101"]["region"]) == ("UNI", "Whangārei and Kaipara (Northpower)")


def test_empty_values_are_skipped_not_treated_as_conflict():
    # 例：HAM0331 有两条当前行，较新的一条有值、较旧的一条分区和区域为空 —— 结果取非空的。
    out = build(
        [
            nsp("HAM0331", start="2026-05-01", zone="", region="", code="HAM0331RUAKGN"),
            nsp("HAM0331", start="2026-11-01", zone="CNI", region="Waikato (WEL Networks)", code="HAM0331WAIKGN"),
        ],
        ["HAM0331"],
    )
    assert (out["HAM0331"]["zone"], out["HAM0331"]["region"]) == ("CNI", "Waikato (WEL Networks)")


def test_empty_value_in_newest_row_uses_next_non_empty_value():
    out = build(
        [
            nsp("AAA0111", start="2020-01-01", zone="UNI"),
            nsp("AAA0111", start="2026-01-01", zone="", code="AAA0111BBBBGN"),
        ],
        ["AAA0111"],
    )
    assert out["AAA0111"]["zone"] == "UNI"


def test_two_current_rows_with_different_region_take_latest_start_date():
    out = build(
        [
            nsp("TWZ0331", start="2010-01-01", region="Waitaki (Network Waitaki)"),
            nsp("TWZ0331", start="2020-06-01", region="South Canterbury (Alpine Energy)", code="TWZ0331ALPEGN"),
        ],
        ["TWZ0331"],
    )
    assert out["TWZ0331"]["region"] == "South Canterbury (Alpine Energy)"


def test_same_start_date_is_broken_by_nsp_code_ascending():
    rows = [
        nsp("AAA0111", start="2020-01-01", region="B region", code="AAA0111ZZZZGN"),
        nsp("AAA0111", start="2020-01-01", region="A region", code="AAA0111AAAAGN"),
    ]
    assert build(rows, ["AAA0111"])["AAA0111"]["region"] == "A region"
    assert build(list(reversed(rows)), ["AAA0111"])["AAA0111"]["region"] == "A region"  # 与输入顺序无关


def test_zone_empty_everywhere_stays_empty_but_island_is_kept():
    # 例：KAW2201 的分区在源数据里就是空的。
    out = build([nsp("KAW2201", island="NI", zone="")], ["KAW2201"])
    assert out["KAW2201"]["island"] == "NI"
    assert out["KAW2201"]["zone"] is None


# ---------- 按站点推出（输电网节点） ----------

def test_missing_node_is_derived_from_same_site():
    out = build(
        [nsp("BEN2202", island="SI", zone="LSI", region="Waitaki (Network Waitaki)", desc="BENMORE")],
        ["BEN2201"],
    )
    r = out["BEN2201"]
    assert (r["island"], r["zone"], r["node_name"]) == ("SI", "LSI", "BENMORE")
    assert r["region"] is None                      # 输电网节点不属于任何配电网
    assert r["mapping_source"] == "derived_from_site"


def test_derived_zone_ignores_empty_sibling_values():
    out = build(
        [
            nsp("HAM0111", zone="CNI"),
            nsp("HAM0331", zone="", code="HAM0331RUAKGN"),
        ],
        ["HAM2201"],
    )
    assert out["HAM2201"]["zone"] == "CNI"


def test_derived_conflicting_values_stay_empty():
    out = build(
        [
            nsp("XYZ0111", island="NI", zone="CNI"),
            nsp("XYZ0331", island="SI", zone="LSI"),
        ],
        ["XYZ2201"],
    )
    r = out["XYZ2201"]
    assert r["island"] is None and r["zone"] is None
    assert r["mapping_source"] == "derived_from_site"


def test_direct_match_wins_over_site_siblings():
    out = build(
        [nsp("HAY0111", island="NI", zone="LNI", region="Wellington"), nsp("HAY2201", island="NI", zone="LNI", region="Direct")],
        ["HAY2201"],
    )
    assert out["HAY2201"]["mapping_source"] == "nsp"
    assert out["HAY2201"]["region"] == "Direct"


def test_unknown_site_is_unmatched_with_all_fields_empty():
    out = build([nsp("ABY0111")], ["QQQ9999"])
    r = out["QQQ9999"]
    assert r["mapping_source"] == "unmatched"
    assert (r["node_name"], r["island"], r["zone"], r["region"]) == (None, None, None, None)


# ---------- 输出形状 ----------

def test_one_row_per_node_sorted_and_uppercased():
    out = build_node_reference([nsp("ABY0111"), nsp("HLY2201")], ["hly2201", "ABY0111", "ABY0111", "  "], "2026-11-06")
    assert [r["node_id"] for r in out] == ["ABY0111", "HLY2201"]


def test_snapshot_date_is_recorded_on_every_row():
    out = build_node_reference([nsp("ABY0111")], ["ABY0111", "QQQ9999"], "2026-11-06")
    assert {r["nsp_snapshot_date"] for r in out} == {"2026-11-06"}


# ---------- 真实快照（本地有 data/ 时才跑） ----------

needs_snapshot = pytest.mark.skipif(not SNAPSHOT.exists(), reason="NSP snapshot not downloaded")


def _real_rows():
    with SNAPSHOT.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


@needs_snapshot
@pytest.mark.parametrize(
    "node,island,zone,region,source",
    [
        ("ABY0111", "SI", "LSI", "South Canterbury (Alpine Energy)", "nsp"),
        ("HLY2201", "NI", "CNI", "Waikato (WEL Networks)", "nsp"),
        ("WHU1101", "NI", "CNI", "Thames Valley (Powerco)", "nsp"),
        ("OHG1101", "NI", "LNI", "Taranaki (Powerco)", "nsp"),
        ("BEN2201", "SI", "LSI", None, "derived_from_site"),
        ("HAY2201", "NI", "LNI", None, "derived_from_site"),
    ],
)
def test_real_snapshot_known_nodes(node, island, zone, region, source):
    r = build(_real_rows(), [node])[node]
    assert (r["island"], r["zone"], r["region"], r["mapping_source"]) == (island, zone, region, source)


@needs_snapshot
@pytest.mark.skipif(not glob.glob(PRICES_GLOB), reason="price files not downloaded")
def test_real_snapshot_covers_every_price_node():
    nodes = set()
    for path in glob.glob(PRICES_GLOB):
        with open(path, encoding="utf-8-sig") as f:
            nodes.update(row["PointOfConnection"] for row in csv.DictReader(f))
    out = build_node_reference(_real_rows(), nodes, "2026-11-06")
    assert len(out) == 246
    assert all(r["island"] in ("NI", "SI") for r in out)
    assert all(r["zone"] in (None, "UNI", "LNI", "CNI", "USI", "LSI") for r in out)
    # 已知缺口：分区为空的节点恰好是 KAW2201（源数据里就是空的）；出现别的节点就说明要更新规则或参考数据
    assert [r["node_id"] for r in out if r["zone"] is None] == ["KAW2201"]
    counts = {}
    for r in out:
        counts[r["mapping_source"]] = counts.get(r["mapping_source"], 0) + 1
    assert counts == {"nsp": 228, "derived_from_site": 18}
