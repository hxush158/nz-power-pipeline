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
