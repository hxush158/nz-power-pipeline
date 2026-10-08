import argparse
import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests


# download_prices(start_date, end_date, kind, dest="data/raw/prices", *, final_grace_days, today=None)
#
# 作用：下载 [start_date, end_date] 内每一天的一种 EMI 价格文件，保存为
#   YYYYMMDD_final.csv 或 YYYYMMDD_interim.csv（两种文件仍然并存，由 kind 决定下载哪一种）。
#   每个日期只请求一个文件。到底用 final 还是 interim，由调用方（例如 Airflow）决定。
#
# 输入：
#   start_date, end_date：含首尾的日期
#   kind："final" 或 "interim"，其他值抛 ValueError
#   final_grace_days：final 允许的发布延迟天数，按新西兰本地日期计算；
#     必须显式传入（仅限关键字参数），暂不设默认值；待观察一两周发布日志后再决定
#   today：可选，默认取新西兰本地（Pacific/Auckland）的今天；测试里传入固定日期
#
# 返回：DownloadSummary，包含
#   results：dict，键是日期，值是 DownloadResult（每个被处理的日期一条），状态为
#     downloaded   本地原来没有，新下载
#     unchanged    已存在，重新下载后逐行比较完全相同
#     updated      已存在，内容有差异，已覆盖，并附带差异统计
#     interim_withdrawn  interim 文件已被撤掉，属正常现象
#     final_not_published  final 文件尚未发布（返回 404），仍在等待窗口内，属正常现象
#   messages：提示信息列表（见下面"输入检查"），没有提示时为空列表
#
# 差异统计（仅 updated）：按主键 (TradingDate, TradingPeriod, PointOfConnection)
#   逐行比较，返回 same / changed / only_old / only_new 的行数。
#   比较在覆盖之前完成，覆盖后旧内容不再保留。
#
# 输入检查（不抛异常，写入 messages 后返回）：
#   提示用英文，测试只检查关键字：
#   start_date 晚于 end_date -> 不下载（不发请求），results 为空，一条提示含 "reversed"
#   日期晚于今天（新西兰本地日期）-> 跳过这些日期，一条提示列出被跳过的日期
#   过滤后没有任何日期可下载 -> results 为空，除上一条（如有）外再加一条提示含 "no dates"
#
# 失败处理（继续处理其余日期，全部处理完再统一抛出）：
#   final 返回 404：
#     今天 - 该日期 <= final_grace_days -> 不算失败，状态记为 final_not_published
#     今天 - 该日期 >  final_grace_days -> 算失败，记为 FinalOverdue（逾期未发布，疑似数据缺口）
#     FinalOverdue 是异常类（继承 Exception），收进 failures；消息含日期、kind 和宽限天数
#   interim 返回 404 -> 不算失败，状态记为 interim_withdrawn（final 发布后 interim 被撤掉，属正常现象）
#   网络错误、超时、其他状态码 -> 记为 DownloadError
#   内容不是合法 CSV（如 HTML 错误页）-> 记为 InvalidContent
#   处理完所有日期后若有失败，抛出 PartialDownloadError，
#   其中包含每个失败的 (日期, 原因) 列表；已成功的文件不回滚。
#   PartialDownloadError 的属性：
#     failures：[(日期, 异常对象)]，按日期顺序；原因直接存异常对象（DownloadError、InvalidContent 等）
#     summary：DownloadSummary，包含已成功处理的日期结果和提示信息
#
# 边界与约定：
#   下载先写临时文件，校验通过后再改名，避免留下半个文件
#   并发运行同一日期：本版本不处理
#   final 逾期的判断在 download_prices 内完成；_download_one 只如实返回 final_not_published
#   interim 没有逾期的概念（404 一律是 interim_withdrawn）；
#     较早的日期应请求 kind="final"，才能发现数据缺口
def download_prices(
    start_date, end_date, kind, dest="data/raw/prices", *, final_grace_days, today=None
):
    _check_kind(kind)
    if start_date > end_date:
        return DownloadSummary(
            results={},
            messages=[f"date range reversed: {start_date} is after {end_date}"],
        )
    if today is None:
        today = datetime.now(ZoneInfo("Pacific/Auckland")).date()
    all_days = [
        start_date + timedelta(days=offset)
        for offset in range((end_date - start_date).days + 1)
    ]
    future_days = [day for day in all_days if day > today]
    days = [day for day in all_days if day <= today]
    messages = []
    if future_days:
        skipped = ", ".join(f"{day:%Y-%m-%d}" for day in future_days)
        messages.append(f"skipped future dates: {skipped}")
    if not days:
        messages.append("no dates to download")
    results = {}
    failures = []
    for day in days:
        try:
            result = _download_one(day, kind, Path(dest))
        except (DownloadError, InvalidContent) as exc:
            failures.append((day, exc))
            continue
        if result.status == "final_not_published" and (
            (today - day).days > final_grace_days
        ):
            failures.append(
                (
                    day,
                    FinalOverdue(
                        f"{day:%Y-%m-%d} final: not published after "
                        f"{final_grace_days} grace days"
                    ),
                )
            )
            continue
        results[day] = result
    summary = DownloadSummary(results=results, messages=messages)
    if failures:
        raise PartialDownloadError(failures, summary)
    return summary

class DownloadError(Exception):
    pass


class InvalidContent(Exception):
    pass


class FinalOverdue(Exception):
    pass


class PartialDownloadError(Exception):
    def __init__(self, failures, summary):
        self.failures = failures
        self.summary = summary
        details = "; ".join(f"{day:%Y-%m-%d}: {exc}" for day, exc in failures)
        super().__init__(f"{len(failures)} date(s) failed: {details}")


EXPECTED_HEADER = (
    "TradingDate,TradingPeriod,PointOfConnection,DollarsPerMegawattHour"
)


@dataclass(frozen=True)
class DiffStats:
    same: int
    changed: int
    only_old: int
    only_new: int


@dataclass(frozen=True)
class DownloadResult:
    status: str
    path: Path | None = None
    diff: DiffStats | None = None


@dataclass(frozen=True)
class DownloadSummary:
    results: dict
    messages: list


# @dataclass(frozen=True)
# class DownloadResult:
#     status: str    # "downloaded" 等
#     path: Path     # 保存的文件路径
#
# _download_one(day, kind, dest) -> DownloadResult
#
# 作用：下载一个日期的一种价格文件，保存为 dest/<文件名>。
# 输入：day（date）、kind（"final" 或 "interim"）、dest（Path，保存目录）
# 下载地址：
# final: https://www.emi.ea.govt.nz/Wholesale/Datasets/DispatchAndPricing/FinalEnergyPrices/{YYYYMMDD}_FinalEnergyPrices.csv
# interim: https://www.emi.ea.govt.nz/Wholesale/Datasets/DispatchAndPricing/FinalEnergyPrices/{YYYYMMDD}_FinalEnergyPrices_I.csv
# 保存内容：响应的原始字节，不转码、不修改。
#
# 已定的规则：
#   返回 200 且内容合法 -> 写入文件，返回 DownloadResult("downloaded", 保存路径)
#   interim 返回 404 -> 不写文件，不抛异常，返回 DownloadResult("interim_withdrawn", None)；本地已有的旧 interim 文件保持不动
#   final 返回 404 -> 不写文件，不抛异常，返回 DownloadResult("final_not_published", None)；本地已有的 final 文件保持不动
#   返回其他状态码（不是 200，也不是上面已定的 404）-> 不写文件，抛 DownloadError，
#     信息里带日期（YYYY-MM-DD）、kind 和状态码
#   网络错误或超时（requests.RequestException）-> 不写文件，抛 DownloadError，
#     信息里带日期（YYYY-MM-DD）、kind 和原始异常的类型名（如 Timeout、ConnectionError）
#   请求超时时间：15 秒（requests.get 的 timeout 参数）
#   kind 不是 "final" 或 "interim" -> 不发请求、不写文件，抛 ValueError，信息里带传入的 kind 值
#   返回 200 但内容不合法 -> 不写文件（本地已有的旧文件保持不动），抛 InvalidContent，信息里带日期、kind 和原因
#     合法的标准：第一行必须正好是这 4 个列名（顺序也要一致）：
#       TradingDate,TradingPeriod,PointOfConnection,DollarsPerMegawattHour
#     只有表头、没有数据行 -> 合法；空文件、没有表头、表头不对（如 HTML 错误页）-> 不合法
#   写文件时先写同目录下的临时文件，写完再改名替换正式文件；写入中途出错 ->
#     抛出原始错误（OSError），本地已有的旧文件保持原样，不留下临时文件
#   本地已有同名文件，且新下载的内容与它完全相同（字节一致）-> 不改动文件，
#     返回 DownloadResult("unchanged", 该文件路径)
#   本地已有同名文件，且新内容有差异 -> 用新内容覆盖，返回 DownloadResult("updated", 文件路径, diff=...)
#     diff 只在 updated 时有值，其他状态为 None；内容为 same / changed / only_old / only_new 四个行数
#     按主键 (TradingDate, TradingPeriod, PointOfConnection) 对应同一行：
#       same = 主键和价格都相同；changed = 主键相同、价格不同；
#       only_old = 只在旧文件；only_new = 只在新文件；先比较后覆盖
def _download_one(day, kind, dest):
    _check_kind(kind)
    date_str = f"{day:%Y%m%d}"
    server_suffix = {"final": "", "interim": "_I"}[kind]
    url = (
        "https://www.emi.ea.govt.nz/Wholesale/Datasets/"
        f"DispatchAndPricing/FinalEnergyPrices/{date_str}_FinalEnergyPrices{server_suffix}.csv"
    )
    try:
        response = requests.get(url, timeout=15)
    except requests.RequestException as exc:
        raise DownloadError(
            f"{day:%Y-%m-%d} {kind}: {type(exc).__name__}"
        ) from exc
    if kind == "interim" and response.status_code == 404:
        return DownloadResult("interim_withdrawn", None)
    if kind == "final" and response.status_code == 404:
        return DownloadResult("final_not_published", None)
    if response.status_code != 200:
        raise DownloadError(
            f"{day:%Y-%m-%d} {kind}: HTTP {response.status_code}"
        )
    lines = response.content.decode("utf-8", errors="replace").splitlines()
    if not lines or lines[0] != EXPECTED_HEADER:
        raise InvalidContent(
            f"{day:%Y-%m-%d} {kind}: unexpected header, expected {EXPECTED_HEADER!r}"
        )
    path = Path(dest) / f"{date_str}_{kind}.csv"
    if path.exists():
        old_content = path.read_bytes()
        if old_content == response.content:
            return DownloadResult("unchanged", path)
        diff = _compare_rows(old_content, response.content)
        _write_atomic(path, response.content)
        return DownloadResult("updated", path, diff)
    _write_atomic(path, response.content)
    return DownloadResult("downloaded", path)


def _write_atomic(path, content):
    temp_path = path.with_name(path.name + ".tmp")
    try:
        temp_path.write_bytes(content)
        os.replace(temp_path, path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def _check_kind(kind):
    if kind not in ("final", "interim"):
        raise ValueError(f"kind must be 'final' or 'interim', got {kind!r}")


def _rows_by_key(content):
    rows = {}
    for line in content.decode("utf-8", errors="replace").splitlines()[1:]:
        trading_date, period, node, price = line.split(",")
        rows[(trading_date, period, node)] = price
    return rows


def _compare_rows(old_content, new_content):
    old_rows = _rows_by_key(old_content)
    new_rows = _rows_by_key(new_content)
    common = old_rows.keys() & new_rows.keys()
    same = sum(1 for key in common if old_rows[key] == new_rows[key])
    return DiffStats(
        same=same,
        changed=len(common) - same,
        only_old=len(old_rows.keys() - new_rows.keys()),
        only_new=len(new_rows.keys() - old_rows.keys()),
    )


# 命令行入口：uv run python -m nzpower.ingest --start YYYY-MM-DD --end YYYY-MM-DD
#   --kind final|interim --final-grace-days N [--dest 目录]
# main(argv=None) -> 退出码；argv 可传入参数列表，便于测试
#   参数缺失、日期格式不对、kind 不合法 -> argparse 报错，退出码 2
#   成功 -> 标准输出打印各状态计数（如 "downloaded: 3, unchanged: 1"）和所有提示信息，退出码 0
#   提示信息（如日期范围反向）不算失败，退出码仍为 0
#   部分失败（PartialDownloadError）-> 成功的计数仍打印到标准输出；
#     每个失败的 "日期: 原因" 打印到标准错误；退出码 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="nzpower.ingest")
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--kind", choices=["final", "interim"], required=True)
    parser.add_argument("--final-grace-days", type=int, required=True)
    parser.add_argument("--dest", default="data/raw/prices")
    args = parser.parse_args(argv)

    exit_code = 0
    try:
        summary = download_prices(
            args.start,
            args.end,
            args.kind,
            args.dest,
            final_grace_days=args.final_grace_days,
        )
    except PartialDownloadError as error:
        summary = error.summary
        for day, reason in error.failures:
            print(f"{day:%Y-%m-%d}: {reason}", file=sys.stderr)
        exit_code = 1

    counts = Counter(result.status for result in summary.results.values())
    if counts:
        print(", ".join(f"{status}: {count}" for status, count in counts.items()))
    for message in summary.messages:
        print(message)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
