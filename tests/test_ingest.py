# tests/test_ingest.py
from datetime import date
from nzpower.ingest import _download_one

HEADER = "TradingDate,TradingPeriod,PointOfConnection,DollarsPerMegawattHour\n"
ROW_1 = "2026-09-26,1,ABY0111,23.86\n"    # 你来写第 1 行，格式同 HEADER
ROW_2 = "2026-09-26,2,ABY0111,20.84\n"    # 你来写第 2 行

CSV_BODY = HEADER + ROW_1 + ROW_2


class FakeResponse:
    def __init__(self, status_code, content):
        self.status_code = status_code
        self.content = content


def test_final_200_valid_csv_is_downloaded(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(200, CSV_BODY.encode()),
    )

    result = _download_one(date(2026, 9, 26), "final", tmp_path)

    assert result.status == "downloaded"
    assert result.path == tmp_path / "20260926_final.csv"   # 文件名由你确认
    assert result.path.read_bytes() == CSV_BODY.encode()