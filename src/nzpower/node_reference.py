"""Build per-node reference data (name, island, zone, distribution region) from the EMI
Network Supply Points (NSP) table. Rules are documented in tests/test_node_reference.py.

CLI:  uv run python -m nzpower.node_reference
Source: Electricity Authority EMI, NetworkSupplyPointsTable (snapshot date in the file name).
"""
import csv
import glob
import re
import sys
from pathlib import Path

FIELDS = ["node_id", "node_name", "island", "zone", "region", "mapping_source", "nsp_snapshot_date"]


def _clean(value):
    value = (value or "").strip()
    return value or None


def _effective_rows(rows):
    """Current rows if any exist, else all rows; newest start date first, NSP code ascending."""
    if not rows:
        return []
    current = [r for r in rows if (r.get("Current flag") or "").strip() == "1"]
    chosen = current or rows
    return sorted(
        chosen,
        key=lambda r: (_neg_date(r.get("Start date")), (r.get("NSP") or "")),
    )


def _neg_date(s):
    # ISO dates compare as strings; invert by mapping digits so newest sorts first.
    s = (s or "").strip()
    return tuple(-ord(c) for c in s)


def _first(rows, column):
    for r in rows:
        v = _clean(r.get(column))
        if v:
            return v
    return None


def _unique_or_none(rows, column):
    values = {_clean(r.get(column)) for r in rows} - {None}
    return values.pop() if len(values) == 1 else None


def build_node_reference(nsp_rows, nodes, snapshot_date):
    by_poc = {}
    for r in nsp_rows:
        poc = (r.get("POC code") or "").strip().upper()
        if poc:
            by_poc.setdefault(poc, []).append(r)

    by_site = {}
    for poc in by_poc:
        by_site.setdefault(poc[:3], []).append(poc)

    out = []
    for node in sorted({n.strip().upper() for n in nodes if n and n.strip()}):
        direct = _effective_rows(by_poc.get(node, []))
        if direct:
            rec = dict(
                node_name=_first(direct, "Description"),
                island=_first(direct, "Island"),
                zone=_first(direct, "Zone"),
                region=_first(direct, "Network reporting region"),
                mapping_source="nsp",
            )
        else:
            sibling_rows = []
            for poc in sorted(by_site.get(node[:3], [])):
                sibling_rows.extend(_effective_rows(by_poc[poc]))
            if sibling_rows:
                rec = dict(
                    node_name=_first(_effective_rows_flat(sibling_rows), "Description"),
                    island=_unique_or_none(sibling_rows, "Island"),
                    zone=_unique_or_none(sibling_rows, "Zone"),
                    region=None,
                    mapping_source="derived_from_site",
                )
            else:
                rec = dict(node_name=None, island=None, zone=None, region=None,
                           mapping_source="unmatched")
        out.append({"node_id": node, **rec, "nsp_snapshot_date": snapshot_date})
    return out


def _effective_rows_flat(rows):
    return sorted(rows, key=lambda r: (_neg_date(r.get("Start date")), (r.get("NSP") or "")))


def main(root=None):
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    snaps = sorted(glob.glob(str(root / "data/raw/reference/*_NetworkSupplyPointsTable.csv")))
    if not snaps:
        sys.exit("No NSP snapshot found in data/raw/reference/")
    snap = Path(snaps[-1])
    d = re.match(r"(\d{4})(\d{2})(\d{2})_", snap.name)
    date = "-".join(d.groups())
    with snap.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    nodes = set()
    for p in glob.glob(str(root / "data/raw/prices/*.csv")):
        with open(p, encoding="utf-8-sig") as f:
            nodes.update(r["PointOfConnection"] for r in csv.DictReader(f))
    result = build_node_reference(rows, nodes, date)
    target = root / "dbt/seeds/node_reference.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows({k: ("" if v is None else v) for k, v in r.items()} for r in result)
    print(f"wrote {target} ({len(result)} rows, snapshot {date})")


if __name__ == "__main__":
    main()
