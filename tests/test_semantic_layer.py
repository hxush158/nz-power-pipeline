# tests/test_semantic_layer.py
# 语义层（semantic/nz_power_metrics.yaml）与 dbt 模型（dbt/models/marts/_marts.yml）的一致性检查。
# 每个 check_* 函数返回问题列表；空列表表示通过。
# 每条用例都有两个测试：真实文件应通过；故意改错的副本应报出对应问题。
import copy
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SEMANTIC_PATH = ROOT / "semantic" / "nz_power_metrics.yaml"
MARTS_PATH = ROOT / "dbt" / "models" / "marts" / "_marts.yml"


def _load(path):
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dbt_columns(marts):
    """{模型名: {列名, ...}}"""
    return {m["name"]: {c["name"] for c in m.get("columns", [])} for m in marts["models"]}


def check_columns_exist(semantic, marts):
    """用例 a：每个指标的 view.column 都能在 _marts.yml 里找到。"""
    dbt = _dbt_columns(marts)
    problems = []
    for m in semantic["metrics"]:
        view, col = m["view"], m["column"]
        if view not in dbt:
            problems.append(f"{m['en']}: 视图 {view} 不在 dbt 项目里")
        elif col not in dbt[view]:
            problems.append(f"{m['en']}: 列 {view}.{col} 不在 dbt 项目里")
    return problems


def check_views_are_marts(semantic, marts):
    """用例 b：views 里只能是 mart_* 或 v_* 视图（不含 fact_/dim_），且都存在于 dbt 项目。
    指标引用的视图也必须在 views 中声明。"""
    dbt = _dbt_columns(marts)
    declared = [v["view"] for v in semantic["views"]]
    problems = []
    for v in declared:
        if v.startswith(("fact_", "dim_")):
            problems.append(f"{v}: 不允许把事实表或维度表暴露给模型")
        if v not in dbt:
            problems.append(f"{v}: 不在 dbt 项目里")
    for m in semantic["metrics"]:
        if m["view"] not in declared:
            problems.append(f"{m['en']}: 引用了未在 views 中声明的视图 {m['view']}")
    return problems


def check_metric_fields(semantic, marts):
    """用例 c：definition 非空、unit 字段存在、en 不重复。
    unit 允许为空字符串（如价格版本），但字段必须写出来，避免漏填。"""
    problems = []
    seen = set()
    for m in semantic["metrics"]:
        en = m.get("en")
        if not en:
            problems.append("有指标缺少 en")
            continue
        if en in seen:
            problems.append(f"{en}: en 重复")
        seen.add(en)
        if not str(m.get("definition", "")).strip():
            problems.append(f"{en}: definition 为空")
        if "unit" not in m:
            problems.append(f"{en}: 缺少 unit 字段")
    return problems


@pytest.fixture(scope="module")
def semantic():
    return _load(SEMANTIC_PATH)


@pytest.fixture(scope="module")
def marts():
    return _load(MARTS_PATH)


def _metric(sem, en):
    return next(m for m in sem["metrics"] if m["en"] == en)


# ---- 用例 a ----
def test_a_columns_exist(semantic, marts):
    assert check_columns_exist(semantic, marts) == []


def test_a_misspelled_column_is_reported(semantic, marts):
    bad = copy.deepcopy(semantic)
    _metric(bad, "avg_price")["column"] = "avg_priec"
    problems = check_columns_exist(bad, marts)
    assert len(problems) == 1
    assert "avg_priec" in problems[0]


# ---- 用例 b ----
def test_b_views_are_marts(semantic, marts):
    assert check_views_are_marts(semantic, marts) == []


def test_b_fact_table_is_rejected(semantic, marts):
    bad = copy.deepcopy(semantic)
    bad["views"].append({"view": "fact_electricity_price", "grain": "x", "description": "x", "keys": []})
    problems = check_views_are_marts(bad, marts)
    assert any("fact_electricity_price" in p for p in problems)


def test_b_undeclared_view_is_reported(semantic, marts):
    bad = copy.deepcopy(semantic)
    bad["views"] = [v for v in bad["views"] if v["view"] != "mart_daily_price"]
    problems = check_views_are_marts(bad, marts)
    assert any("mart_daily_price" in p for p in problems)


# ---- 用例 c ----
def test_c_metric_fields(semantic, marts):
    assert check_metric_fields(semantic, marts) == []


def test_c_empty_definition_is_reported(semantic, marts):
    bad = copy.deepcopy(semantic)
    _metric(bad, "min_price")["definition"] = "  "
    problems = check_metric_fields(bad, marts)
    assert problems == ["min_price: definition 为空"]


def test_c_duplicate_en_is_reported(semantic, marts):
    bad = copy.deepcopy(semantic)
    bad["metrics"][1]["en"] = bad["metrics"][0]["en"]
    problems = check_metric_fields(bad, marts)
    assert any("en 重复" in p for p in problems)


# ---- 用例 d–g：发电数据进入语义层（2026-11-09）----
FUELS = ["Hydro", "Wind", "Geothermal", "Solar", "Gas", "Coal", "Diesel", "Wood", "Battery storage"]


def test_d_generation_views_and_metrics_are_declared(semantic):
    views = {v["view"]: v for v in semantic["views"]}
    assert views["mart_daily_generation"]["keys"] == ["trading_date", "island", "zone", "fuel"]
    assert views["mart_daily_generation_weighted_price"]["keys"] == ["trading_date", "island", "fuel"]
    pairs = {(m["view"], m["column"]) for m in semantic["metrics"]}
    assert ("mart_daily_generation", "generation_kwh") in pairs
    assert ("mart_daily_generation", "plant_count") in pairs
    assert ("mart_daily_generation_weighted_price", "generation_kwh") in pairs
    assert ("mart_daily_generation_weighted_price", "interim_generation_kwh") in pairs
    assert ("mart_daily_generation_weighted_price", "weighted_avg_price") in pairs


def test_e_not_available_no_longer_claims_missing_generation_but_keeps_demand(semantic):
    text = semantic["conventions"]["not_available"].lower()
    assert "no volume, demand or generation data" not in text
    assert "demand" in text  # 没有需求量数据这一点仍然要说清楚


def test_f_weighted_price_says_it_is_not_a_demand_side_price(semantic):
    m = _metric(semantic, "weighted_avg_price")
    text = (m["definition"] + " " + " ".join(m["pitfalls"])).lower()
    assert "demand" in text and "not" in text
    assert m["unit"] == "NZD/MWh"


def test_g_fuel_convention_lists_every_fuel(semantic):
    text = semantic["conventions"]["fuel"]
    for fuel in FUELS:
        assert fuel in text


def test_h_metric_names_are_unique_across_the_new_views(semantic, marts):
    # en 不能重复（用例 c），两个视图都有 generation_kwh 列，所以第二个指标要用不同的 en
    assert check_metric_fields(semantic, marts) == []
    assert check_columns_exist(semantic, marts) == []


# ---- 用例 i–m：跨节点平均的口径（2026-11-10）----
NODE_REFERENCE_PATH = ROOT / "dbt" / "seeds" / "node_reference.csv"


def test_i_avg_price_no_longer_says_cross_node_average_is_meaningless(semantic):
    m = _metric(semantic, "avg_price")
    text = " ".join(m["pitfalls"]).lower()
    assert "no clear business meaning" not in text      # 与 not_available 里"可以按岛分组"自相矛盾
    assert "unweighted" in text
    assert "cross_node_average" in text


def test_j_cross_node_average_convention_requires_the_caveats(semantic):
    text = semantic["conventions"]["cross_node_average"].lower()
    assert "unweighted" in text                           # 必须说明不加权
    assert "number of nodes" in text                      # 必须给出参与的节点数
    assert "market price" in text and "never" in text     # 不能说成市场价


def test_k_reference_nodes_convention_and_nodes_exist_with_expected_islands(semantic):
    import csv

    text = semantic["conventions"]["reference_nodes"]
    assert "OTA2201" in text and "BEN2201" in text
    assert "no single national price" in text.lower()
    with NODE_REFERENCE_PATH.open(encoding="utf-8") as f:
        islands = {r["node_id"]: r["island"] for r in csv.DictReader(f)}
    assert islands["OTA2201"] == "NI"
    assert islands["BEN2201"] == "SI"


def test_l_not_available_points_to_cross_node_average(semantic):
    assert "cross_node_average" in semantic["conventions"]["not_available"]


def test_m_version_is_bumped_for_the_new_conventions(semantic):
    assert semantic["version"] == "2026-11.4"


def test_n_cross_node_average_is_pooled_over_current_price_rows(semantic):
    """Decision 2026-11-10: average the mart_current_price rows directly (pooled),
    not an average of per-node daily averages."""
    text = semantic["conventions"]["cross_node_average"].lower()
    assert "mart_current_price" in text
    assert "every node counts equally" not in text
    assert "do not average" in text and "daily averages" in text
    assert "fewer rows" in text
    assert "date range" in text


def test_o_cross_node_average_carries_the_worked_example(semantic):
    """North Island, 2026-04-08: WHU1101 first appears with 27 of 48 periods."""
    text = semantic["conventions"]["cross_node_average"]
    for token in ("2026-04-08", "WHU1101", "162 nodes", "7,755", "162.08"):
        assert token in text, token


def test_p_fuel_convention_says_battery_storage_is_not_a_fuel(semantic):
    """Decision 2026-11-14: Battery storage is storage, excluded from totals, shares and fuel rankings."""
    text = semantic["conventions"]["fuel"].lower()
    assert "battery storage" in text and "not a fuel" in text
    for word in ("total generation", "share", "ranking", "unless", "say"):
        assert word in text, word


def test_q_generation_kwh_pitfall_excludes_battery_from_totals(semantic):
    text = " ".join(_metric(semantic, "generation_kwh")["pitfalls"]).lower()
    assert "battery storage" in text
    assert "exclude" in text and "total generation" in text
    assert "counted twice" in text  # the reason: energy was already counted when the battery charged


def test_r_weighted_avg_price_pitfall_leaves_battery_out_of_fuel_rankings(semantic):
    text = " ".join(_metric(semantic, "weighted_avg_price")["pitfalls"]).lower()
    assert "battery storage" in text and "not a fuel" in text
    assert "ranking" in text and "separately" in text


def _all_strings(node, skip_key=None):
    """Yield every string in the YAML tree except values under the key `en`."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k != "en":
                yield from _all_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _all_strings(v)
    elif isinstance(node, str):
        yield node


def test_s_metric_names_that_are_not_column_names_always_carry_the_real_column(semantic):
    """2026-11-15: the model read priced_generation_kwh as a column name (Binder Error).
    Wherever a metric whose en differs from its column is mentioned, the real column and view must follow."""
    problems = []
    for m in semantic["metrics"]:
        if m["en"] == m["column"]:
            continue
        hint = f"column {m['column']} in {m['view']}"
        for text in _all_strings(semantic):
            start = 0
            while (i := text.find(m["en"], start)) != -1:
                if hint not in text[i : i + len(m["en"]) + 80]:
                    problems.append(text[max(0, i - 30) : i + 60])
                start = i + 1
    assert problems == [], problems
