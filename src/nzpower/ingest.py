from dataclasses import dataclass
from pathlib import Path

import requests

# download_prices(start_date, end_date, kind, dest="data/raw/prices")
#
# 作用：下载 [start_date, end_date] 内每一天的一种 EMI 价格文件，保存为
#   YYYYMMDD_final.csv 或 YYYYMMDD_interim.csv（两种文件仍然并存，由 kind 决定下载哪一种）。
#   每个日期只请求一个文件。到底用 final 还是 interim，由调用方（例如 Airflow）决定。
#
# 输入：
#   start_date, end_date：含首尾的日期
#   kind："final" 或 "interim"，其他值抛 ValueError
#
# 返回：一个结果对象，包含
#   results：每个日期一条，状态为
#     downloaded   本地原来没有，新下载
#     unchanged    已存在，重新下载后逐行比较完全相同
#     updated      已存在，内容有差异，已覆盖，并附带差异统计
#   messages：提示信息列表（见下面"输入检查"）
#
# 差异统计（仅 updated）：按主键 (TradingDate, TradingPeriod, PointOfConnection)
#   逐行比较，返回 same / changed / only_old / only_new 的行数。
#   比较在覆盖之前完成，覆盖后旧内容不再保留。
#
# 输入检查（不抛异常，写入 messages 后返回）：
#   start_date 晚于 end_date -> 不下载，results 为空，提示"日期范围反向"
#   日期晚于今天（新西兰本地日期）-> 跳过这些日期，提示被跳过的日期
#   过滤后没有任何日期可下载 -> results 为空，提示"没有可下载的日期"
#
# 失败处理（继续处理其余日期，全部处理完再统一抛出）：
#   final 返回 404    -> 记为 FinalNotPublished
#   interim 返回 404  -> 记为 InterimNotAvailable（与 final 的 404 分开处理）
#   网络错误、超时、其他状态码 -> 记为 DownloadError
#   内容不是合法 CSV（如 HTML 错误页）-> 记为 InvalidContent
#   处理完所有日期后若有失败，抛出 PartialDownloadError，
#   其中包含每个失败的 (日期, 原因) 列表；已成功的文件不回滚。
#
# 边界与约定：
#   下载先写临时文件，校验通过后再改名，避免留下半个文件
#   并发运行同一日期：本版本不处理
def download_prices(start_date, end_date, kind, dest="data/raw/prices"):
    raise NotImplementedError

@dataclass(frozen=True)
class DownloadResult:
    status: str
    path: Path


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
# 本轮范围（用例 1）：
#   返回 200 且内容合法 -> 写入文件，返回 DownloadResult("downloaded", 保存路径)
# 之后各轮再加：404、网络错误、内容校验、已存在文件的比较
def _download_one(day, kind, dest):
    date_str = f"{day:%Y%m%d}"
    server_suffix = {"final": "", "interim": "_I"}[kind]
    url = (
        "https://www.emi.ea.govt.nz/Wholesale/Datasets/"
        f"DispatchAndPricing/FinalEnergyPrices/{date_str}_FinalEnergyPrices{server_suffix}.csv"
    )
    response = requests.get(url)
    path = Path(dest) / f"{date_str}_{kind}.csv"
    path.write_bytes(response.content)
    return DownloadResult("downloaded", path)
