import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# upload_prices(source_dir, container_client, prefix="prices") -> UploadSummary
#
# 作用：把 source_dir 里的价格 CSV 上传到 Azure 容器（ADLS Gen2），按文件名里的年月分区。
# 输入：
#   source_dir：本地目录（只看目录下的文件，不递归子目录）
#   container_client：已创建好的 Azure ContainerClient（测试里传入假对象，函数本身不读凭证）
#   prefix：容器内的路径前缀，默认 "prices"
# 路径映射：本地 20260926_final.csv -> 容器内 prices/2026-09/20260926_final.csv
#   final 与 interim 两种文件并存，文件名保持不变
# 幂等：同名文件直接覆盖（overwrite=True），重复运行后容器里的文件数不变
# 文件名不符合 YYYYMMDD_final.csv 或 YYYYMMDD_interim.csv 的文件：
#   不上传，不报错，在返回值里列出
# 返回：UploadSummary
#   uploaded：已上传的容器内路径列表（按路径排序）
#   skipped：被跳过的本地文件名列表（按文件名排序）
FILENAME_PATTERN = re.compile(r"^\d{8}_(final|interim)\.csv$")


@dataclass(frozen=True)
class UploadSummary:
    uploaded: list
    skipped: list


def upload_prices(source_dir, container_client, prefix="prices"):
    uploaded = []
    skipped = []
    for path in sorted(Path(source_dir).iterdir()):
        if not path.is_file():
            continue
        if not FILENAME_PATTERN.match(path.name):
            skipped.append(path.name)
            continue
        year, month = path.name[0:4], path.name[4:6]
        blob_name = f"{prefix}/{year}-{month}/{path.name}"
        container_client.upload_blob(blob_name, path.read_bytes(), overwrite=True)
        uploaded.append(blob_name)
    return UploadSummary(uploaded=sorted(uploaded), skipped=sorted(skipped))


# 命令行入口：uv run python -m nzpower.upload [--source 目录] [--container 名称]
#   --source 默认 data/raw/prices；--container 默认 raw
# 凭证：环境变量 AZURE_STORAGE_CONNECTION_STRING（不写进代码、不提交）
# main(argv=None) -> 退出码
#   成功 -> 标准输出 "uploaded: N, skipped: M"，每个被跳过的文件另起一行列出，退出码 0
#   环境变量未设置 -> 标准错误提示变量名，不创建客户端，退出码 1
#   source 目录不存在 -> 标准错误提示目录路径，退出码 1
# _create_container_client(connection_string, container_name)：
#   在这里才导入 azure 库并创建客户端，测试里整体替换，不连真实云
def _create_container_client(connection_string, container_name):
    from azure.storage.blob import BlobServiceClient

    service = BlobServiceClient.from_connection_string(connection_string)
    return service.get_container_client(container_name)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="nzpower.upload")
    parser.add_argument("--source", default="data/raw/prices")
    parser.add_argument("--container", default="raw")
    args = parser.parse_args(argv)

    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        print(
            "environment variable AZURE_STORAGE_CONNECTION_STRING is not set",
            file=sys.stderr,
        )
        return 1

    source = Path(args.source)
    if not source.is_dir():
        print(f"source directory not found: {source}", file=sys.stderr)
        return 1

    container_client = _create_container_client(connection_string, args.container)
    summary = upload_prices(source, container_client)
    print(f"uploaded: {len(summary.uploaded)}, skipped: {len(summary.skipped)}")
    for name in summary.skipped:
        print(f"  skipped file: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
