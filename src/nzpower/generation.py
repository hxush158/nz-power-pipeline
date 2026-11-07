"""Download EMI Generation_MD files (estimated generation by plant, one CSV per month).

Rules are specified by tests/test_generation.py.
CLI:  uv run python -m nzpower.generation --start 2026-04 --end 2026-09 [--dest DIR]
Source: Electricity Authority EMI, Wholesale / Datasets / Generation / Generation_MD.
"""
import argparse
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from nzpower.ingest import (
    DownloadError,
    DownloadResult,
    DownloadSummary,
    InvalidContent,
    PartialDownloadError,
    _write_atomic,
)

GENERATION_HEADER = (
    "Site_Code,POC_Code,Nwk_Code,Gen_Code,Fuel_Code,Tech_Code,Trading_Date,"
    + ",".join(f"TP{i}" for i in range(1, 51))
)
BASE_URL = "https://www.emi.ea.govt.nz/Wholesale/Datasets/Generation/Generation_MD/"


class MissingMonth(Exception):
    pass


def _first_of_month(day):
    return date(day.year, day.month, 1)


def _months(start, end):
    month = _first_of_month(start)
    last = _first_of_month(end)
    while month <= last:
        yield month
        month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)


def _download_month(month, dest):
    name = f"{month:%Y%m}_Generation_MD.csv"
    try:
        response = requests.get(BASE_URL + name, timeout=30)
    except requests.RequestException as exc:
        raise DownloadError(f"{month:%Y-%m} generation: {type(exc).__name__}") from exc
    if response.status_code == 404:
        return DownloadResult("not_published", None)
    if response.status_code != 200:
        raise DownloadError(f"{month:%Y-%m} generation: HTTP {response.status_code}")
    lines = response.content.decode("utf-8", errors="replace").splitlines()
    if not lines or lines[0] != GENERATION_HEADER:
        raise InvalidContent(
            f"{month:%Y-%m} generation: unexpected header, expected {GENERATION_HEADER!r}"
        )
    path = Path(dest) / name
    if path.exists():
        if path.read_bytes() == response.content:
            return DownloadResult("unchanged", path)
        _write_atomic(path, response.content)
        return DownloadResult("updated", path)
    _write_atomic(path, response.content)
    return DownloadResult("downloaded", path)


def download_generation(start_month, end_month, dest="data/raw/generation", *, today=None):
    if _first_of_month(start_month) > _first_of_month(end_month):
        return DownloadSummary(
            results={},
            messages=[f"month range reversed: {start_month:%Y-%m} is after {end_month:%Y-%m}"],
        )
    if today is None:
        today = datetime.now(ZoneInfo("Pacific/Auckland")).date()
    this_month = _first_of_month(today)
    all_months = list(_months(start_month, end_month))
    future = [m for m in all_months if m > this_month]
    months = [m for m in all_months if m <= this_month]
    messages = []
    if future:
        messages.append("skipped future months: " + ", ".join(f"{m:%Y-%m}" for m in future))
    if not months:
        messages.append("no months to download")
    results, failures = {}, []
    for month in months:
        try:
            result = _download_month(month, Path(dest))
        except (DownloadError, InvalidContent) as exc:
            failures.append((month, exc))
            continue
        if result.status == "not_published" and month < this_month:
            failures.append((month, MissingMonth(f"{month:%Y-%m} generation: not published (404)")))
            continue
        results[month] = result
    summary = DownloadSummary(results=results, messages=messages)
    if failures:
        raise PartialDownloadError(failures, summary)
    return summary


def _month_arg(text):
    return datetime.strptime(text, "%Y-%m").date()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="nzpower.generation")
    parser.add_argument("--start", type=_month_arg, required=True, help="YYYY-MM")
    parser.add_argument("--end", type=_month_arg, required=True, help="YYYY-MM")
    parser.add_argument("--dest", default="data/raw/generation")
    args = parser.parse_args(argv)

    exit_code = 0
    try:
        summary = download_generation(args.start, args.end, args.dest)
    except PartialDownloadError as error:
        summary = error.summary
        for month, reason in error.failures:
            print(f"{month:%Y-%m}: {reason}", file=sys.stderr)
        exit_code = 1
    counts = Counter(result.status for result in summary.results.values())
    if counts:
        print(", ".join(f"{status}: {count}" for status, count in counts.items()))
    for message in summary.messages:
        print(message)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
