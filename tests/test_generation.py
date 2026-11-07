# tests/test_generation.py
# EMI Generation_MD（按电厂估算的发电量，每月一个文件）的下载与上传。
# 决定（2026-11-08）：
#   - 按月份下载，文件名 YYYYMM_Generation_MD.csv，原样保存；表头必须与 GENERATION_HEADER 完全一致。
#   - 404：当月或之后的月份 = 还没发布，不算失败（not_published）；更早的月份 = 数据缺口，算失败。
#   - 晚于当月的月份直接跳过并提示；开始月晚于结束月不请求、给提示。
#   - 异常类、原子写入复用 nzpower.ingest。
from datetime import date

import pytest
import requests

from nzpower.generation import (
    GENERATION_HEADER,
    MissingMonth,
    _download_month,
    download_generation,
    main,
)
from nzpower.ingest import DownloadError, InvalidContent, PartialDownloadError
from nzpower.upload import upload_generation
from nzpower.upload import main as upload_main

ROW_A = "ARA,ARA2201,MRPL,aratiatia,Hydro,Hydro,2026-04-01," + ",".join(["9040"] * 48) + ",,\n"
ROW_B = "ARA,ARA2201,MRPL,aratiatia,Hydro,Hydro,2026-04-02," + ",".join(["18660"] * 48) + ",,\n"
BODY = (GENERATION_HEADER + "\n" + ROW_A + ROW_B).encode()
BASE_URL = "https://www.emi.ea.govt.nz/Wholesale/Datasets/Generation/Generation_MD/"
TODAY = date(2026, 11, 8)


class FakeResponse:
    def __init__(self, status_code, content=b""):
        self.status_code = status_code
        self.content = content


def serve(monkeypatch, responses):
    """responses: {url_suffix: FakeResponse}；返回被请求过的 URL 列表。"""
    urls = []

    def fake_get(url, *args, **kwargs):
        urls.append(url)
        return responses.get(url.rsplit("/", 1)[-1], FakeResponse(404))

    monkeypatch.setattr("requests.get", fake_get)
    return urls


def test_header_matches_the_real_file_layout():
    columns = GENERATION_HEADER.split(",")
    assert columns[:7] == ["Site_Code", "POC_Code", "Nwk_Code", "Gen_Code", "Fuel_Code", "Tech_Code", "Trading_Date"]
    assert columns[7:] == [f"TP{i}" for i in range(1, 51)]
    assert len(columns) == 57


# ---------- 单个月份 ----------

def test_valid_month_is_downloaded_and_saved_unchanged(tmp_path, monkeypatch):
    urls = serve(monkeypatch, {"202604_Generation_MD.csv": FakeResponse(200, BODY)})
    result = _download_month(date(2026, 4, 1), tmp_path)
    assert result.status == "downloaded"
    assert result.path == tmp_path / "202604_Generation_MD.csv"
    assert result.path.read_bytes() == BODY
    assert urls == [BASE_URL + "202604_Generation_MD.csv"]


def test_same_content_is_unchanged_and_file_is_not_touched(tmp_path, monkeypatch):
    (tmp_path / "202604_Generation_MD.csv").write_bytes(BODY)
    serve(monkeypatch, {"202604_Generation_MD.csv": FakeResponse(200, BODY)})
    assert _download_month(date(2026, 4, 1), tmp_path).status == "unchanged"


def test_different_content_overwrites_and_reports_updated(tmp_path, monkeypatch):
    (tmp_path / "202604_Generation_MD.csv").write_bytes(GENERATION_HEADER.encode() + b"\n" + ROW_A.encode())
    serve(monkeypatch, {"202604_Generation_MD.csv": FakeResponse(200, BODY)})
    result = _download_month(date(2026, 4, 1), tmp_path)
    assert result.status == "updated"
    assert result.path.read_bytes() == BODY


def test_404_returns_not_published_and_writes_nothing(tmp_path, monkeypatch):
    serve(monkeypatch, {})
    result = _download_month(date(2026, 4, 1), tmp_path / "gen")
    assert (result.status, result.path) == ("not_published", None)
    assert not (tmp_path / "gen").exists()


@pytest.mark.parametrize("content", [b"", b"<html>error</html>", b"Site_Code,POC_Code\nARA,ARA2201\n"])
def test_wrong_header_is_invalid_content_and_keeps_old_file(tmp_path, monkeypatch, content):
    old = tmp_path / "202604_Generation_MD.csv"
    old.write_bytes(BODY)
    serve(monkeypatch, {"202604_Generation_MD.csv": FakeResponse(200, content)})
    with pytest.raises(InvalidContent, match="2026-04"):
        _download_month(date(2026, 4, 1), tmp_path)
    assert old.read_bytes() == BODY


def test_other_status_code_is_download_error(tmp_path, monkeypatch):
    serve(monkeypatch, {"202604_Generation_MD.csv": FakeResponse(500)})
    with pytest.raises(DownloadError, match="500"):
        _download_month(date(2026, 4, 1), tmp_path)


def test_network_error_is_download_error_with_type_name(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise requests.Timeout()

    monkeypatch.setattr("requests.get", boom)
    with pytest.raises(DownloadError, match="Timeout"):
        _download_month(date(2026, 4, 1), tmp_path)


# ---------- 多个月份 ----------

def test_range_is_inclusive_and_crosses_year_end(tmp_path, monkeypatch):
    names = ["202511_Generation_MD.csv", "202512_Generation_MD.csv", "202601_Generation_MD.csv"]
    urls = serve(monkeypatch, {n: FakeResponse(200, BODY) for n in names})
    summary = download_generation(date(2025, 11, 15), date(2026, 1, 3), tmp_path, today=TODAY)
    assert [u.rsplit("/", 1)[-1] for u in urls] == names
    assert sorted(summary.results) == [date(2025, 11, 1), date(2025, 12, 1), date(2026, 1, 1)]


def test_current_month_404_is_not_a_failure(tmp_path, monkeypatch):
    serve(monkeypatch, {"202610_Generation_MD.csv": FakeResponse(200, BODY)})
    summary = download_generation(date(2026, 10, 1), date(2026, 11, 1), tmp_path, today=TODAY)
    assert summary.results[date(2026, 10, 1)].status == "downloaded"
    assert summary.results[date(2026, 11, 1)].status == "not_published"


def test_past_month_404_is_a_failure_after_the_others_finish(tmp_path, monkeypatch):
    serve(monkeypatch, {"202605_Generation_MD.csv": FakeResponse(200, BODY)})
    with pytest.raises(PartialDownloadError) as info:
        download_generation(date(2026, 4, 1), date(2026, 5, 1), tmp_path, today=TODAY)
    assert [m for m, _ in info.value.failures] == [date(2026, 4, 1)]
    assert isinstance(info.value.failures[0][1], MissingMonth)
    assert info.value.summary.results[date(2026, 5, 1)].status == "downloaded"
    assert (tmp_path / "202605_Generation_MD.csv").exists()


def test_future_months_are_skipped_with_a_message(tmp_path, monkeypatch):
    urls = serve(monkeypatch, {"202611_Generation_MD.csv": FakeResponse(200, BODY)})
    summary = download_generation(date(2026, 11, 1), date(2027, 1, 1), tmp_path, today=TODAY)
    assert [u.rsplit("/", 1)[-1] for u in urls] == ["202611_Generation_MD.csv"]
    assert any("skipped future" in m and "2026-12" in m and "2027-01" in m for m in summary.messages)


def test_reversed_range_makes_no_request(tmp_path, monkeypatch):
    urls = serve(monkeypatch, {})
    summary = download_generation(date(2026, 9, 1), date(2026, 4, 1), tmp_path, today=TODAY)
    assert urls == [] and summary.results == {}
    assert any("reversed" in m for m in summary.messages)


# ---------- 命令行 ----------

def test_main_prints_counts_and_exits_zero(tmp_path, monkeypatch, capsys):
    serve(monkeypatch, {"202604_Generation_MD.csv": FakeResponse(200, BODY)})
    code = main(["--start", "2026-04", "--end", "2026-04", "--dest", str(tmp_path)])
    assert code == 0
    assert "downloaded: 1" in capsys.readouterr().out


def test_main_exit_code_1_and_reason_on_stderr_when_a_month_is_missing(tmp_path, monkeypatch, capsys):
    serve(monkeypatch, {})
    code = main(["--start", "2026-04", "--end", "2026-04", "--dest", str(tmp_path)])
    assert code == 1
    assert "2026-04" in capsys.readouterr().err


def test_main_rejects_bad_month_format(tmp_path):
    with pytest.raises(SystemExit) as info:
        main(["--start", "2026-04-01", "--end", "2026-04", "--dest", str(tmp_path)])
    assert info.value.code == 2


# ---------- 上传 ----------

class FakeContainer:
    def __init__(self):
        self.blobs = {}

    def upload_blob(self, name, data, overwrite=False):
        if name in self.blobs and not overwrite:
            raise RuntimeError(f"BlobAlreadyExists: {name}")
        self.blobs[name] = data


def test_generation_files_go_into_month_partitions(tmp_path):
    (tmp_path / "202604_Generation_MD.csv").write_bytes(BODY)
    (tmp_path / "202609_Generation_MD.csv").write_bytes(BODY)
    container = FakeContainer()
    summary = upload_generation(tmp_path, container)
    assert container.blobs == {
        "generation/2026-04/202604_Generation_MD.csv": BODY,
        "generation/2026-09/202609_Generation_MD.csv": BODY,
    }
    assert summary.uploaded == sorted(container.blobs) and summary.skipped == []


def test_generation_upload_twice_does_not_duplicate(tmp_path):
    (tmp_path / "202604_Generation_MD.csv").write_bytes(BODY)
    container = FakeContainer()
    upload_generation(tmp_path, container)
    upload_generation(tmp_path, container)
    assert list(container.blobs) == ["generation/2026-04/202604_Generation_MD.csv"]


def test_generation_upload_skips_price_files_and_other_names(tmp_path):
    for name in ["20260926_final.csv", "202604_Generation_MD.csv.tmp", "notes.txt", "202613_Generation_MD.csv"]:
        (tmp_path / name).write_bytes(b"x")
    container = FakeContainer()
    summary = upload_generation(tmp_path, container)
    assert container.blobs == {}
    assert summary.skipped == sorted(["20260926_final.csv", "202604_Generation_MD.csv.tmp", "notes.txt", "202613_Generation_MD.csv"])


def test_upload_cli_dataset_generation_uses_generation_defaults(tmp_path, monkeypatch, capsys):
    (tmp_path / "202604_Generation_MD.csv").write_bytes(BODY)
    container = FakeContainer()
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "x")
    monkeypatch.setattr("nzpower.upload._create_container_client", lambda cs, name: container)
    code = upload_main(["--dataset", "generation", "--source", str(tmp_path)])
    assert code == 0
    assert list(container.blobs) == ["generation/2026-04/202604_Generation_MD.csv"]
    assert "uploaded: 1, skipped: 0" in capsys.readouterr().out
