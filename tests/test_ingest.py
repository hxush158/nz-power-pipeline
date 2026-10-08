# tests/test_ingest.py
from datetime import date

import pytest
import requests

from nzpower.ingest import (
    DiffStats,
    DownloadError,
    InvalidContent,
    _download_one,
    download_prices,
)

HEADER = "TradingDate,TradingPeriod,PointOfConnection,DollarsPerMegawattHour\n"
ROW_1 = "2026-09-26,1,ABY0111,23.86\n"    # 你来写第 1 行，格式同 HEADER
ROW_2 = "2026-09-26,2,ABY0111,20.84\n"    # 你来写第 2 行

CSV_BODY = HEADER + ROW_1 + ROW_2


class FakeResponse:
    def __init__(self, status_code, content):
        self.status_code = status_code
        self.content = content

# test case 1
def test_final_200_valid_csv_is_downloaded(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(200, CSV_BODY.encode()),
    )

    result = _download_one(date(2026, 9, 26), "final", tmp_path)

    assert result.status == "downloaded"
    assert result.path == tmp_path / "20260926_final.csv"   # 文件名由你确认
    assert result.path.read_bytes() == CSV_BODY.encode()


BASE_URL = (
    "https://www.emi.ea.govt.nz/Wholesale/Datasets/"
    "DispatchAndPricing/FinalEnergyPrices/"
)

# test case 13
def test_final_requests_final_energy_prices_url(tmp_path, monkeypatch):
    urls = []

    def fake_get(url, *args, **kwargs):
        urls.append(url)
        return FakeResponse(200, CSV_BODY.encode())

    monkeypatch.setattr("requests.get", fake_get)

    _download_one(date(2026, 9, 26), "final", tmp_path)

    assert urls == [BASE_URL + "20260926_FinalEnergyPrices.csv"]

# test case 14
def test_interim_requests_final_energy_prices_i_url(tmp_path, monkeypatch):
    urls = []

    def fake_get(url, *args, **kwargs):
        urls.append(url)
        return FakeResponse(200, CSV_BODY.encode())

    monkeypatch.setattr("requests.get", fake_get)

    _download_one(date(2026, 9, 26), "interim", tmp_path)

    assert urls == [BASE_URL + "20260926_FinalEnergyPrices_I.csv"]


def test_interim_404_returns_interim_withdrawn_without_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(404, b"<html>Not Found</html>"),
    )

    result = _download_one(date(2026, 9, 26), "interim", tmp_path)

    assert result.status == "interim_withdrawn"
    assert result.path is None
    assert list(tmp_path.iterdir()) == []

# test case 10
def test_interim_404_keeps_existing_local_interim_file(tmp_path, monkeypatch):
    old_file = tmp_path / "20260926_interim.csv"
    old_file.write_bytes(CSV_BODY.encode())
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(404, b"<html>Not Found</html>"),
    )

    result = _download_one(date(2026, 9, 26), "interim", tmp_path)

    assert result.status == "interim_withdrawn"
    assert result.path is None
    assert old_file.read_bytes() == CSV_BODY.encode()

# test case 3
def test_final_404_returns_final_not_published_without_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(404, b"<html>Not Found</html>"),
    )

    result = _download_one(date(2026, 9, 26), "final", tmp_path)

    assert result.status == "final_not_published"
    assert result.path is None
    assert list(tmp_path.iterdir()) == []

# test case 7
def test_status_500_raises_download_error_with_details(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(500, b"Server Error"),
    )

    with pytest.raises(DownloadError) as excinfo:
        _download_one(date(2026, 9, 26), "final", tmp_path)

    message = str(excinfo.value)
    assert "2026-09-26" in message
    assert "final" in message
    assert "500" in message
    assert list(tmp_path.iterdir()) == []


# test case 6
@pytest.mark.parametrize(
    "error_class", [requests.Timeout, requests.ConnectionError]
)
def test_network_error_raises_download_error_with_details(
    tmp_path, monkeypatch, error_class
):
    def fake_get(*args, **kwargs):
        raise error_class("boom")

    monkeypatch.setattr("requests.get", fake_get)

    with pytest.raises(DownloadError) as excinfo:
        _download_one(date(2026, 9, 26), "final", tmp_path)

    message = str(excinfo.value)
    assert "2026-09-26" in message
    assert "final" in message
    assert error_class.__name__ in message
    assert list(tmp_path.iterdir()) == []

# test case 6
def test_request_uses_15_second_timeout(tmp_path, monkeypatch):
    timeouts = []

    def fake_get(url, *args, **kwargs):
        timeouts.append(kwargs.get("timeout"))
        return FakeResponse(200, CSV_BODY.encode())

    monkeypatch.setattr("requests.get", fake_get)

    _download_one(date(2026, 9, 26), "final", tmp_path)

    assert timeouts == [15]


# test case 11
def test_invalid_kind_raises_value_error_without_request(tmp_path, monkeypatch):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append(args)
        return FakeResponse(200, CSV_BODY.encode())

    monkeypatch.setattr("requests.get", fake_get)

    with pytest.raises(ValueError) as excinfo:
        _download_one(date(2026, 9, 26), "draft", tmp_path)

    assert "draft" in str(excinfo.value)
    assert calls == []
    assert list(tmp_path.iterdir()) == []


# test case 5, 12
@pytest.mark.parametrize(
    "body",
    [
        b"<html><body>Error</body></html>",
        b"",
        b"TradingDate,TradingPeriod,PointOfConnection\n" + ROW_1.encode(),
        b"TradingPeriod,TradingDate,PointOfConnection,DollarsPerMegawattHour\n",
    ],
)
def test_invalid_content_raises_invalid_content_without_file(
    tmp_path, monkeypatch, body
):
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(200, body),
    )

    with pytest.raises(InvalidContent) as excinfo:
        _download_one(date(2026, 9, 26), "final", tmp_path)

    message = str(excinfo.value)
    assert "2026-09-26" in message
    assert "final" in message
    assert list(tmp_path.iterdir()) == []

# test case 12
def test_header_only_content_is_downloaded(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(200, HEADER.encode()),
    )

    result = _download_one(date(2026, 9, 26), "final", tmp_path)

    assert result.status == "downloaded"
    assert result.path.read_bytes() == HEADER.encode()


# test case 8
def test_existing_identical_file_returns_unchanged(tmp_path, monkeypatch):
    existing = tmp_path / "20260926_final.csv"
    existing.write_bytes(CSV_BODY.encode())
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(200, CSV_BODY.encode()),
    )

    result = _download_one(date(2026, 9, 26), "final", tmp_path)

    assert result.status == "unchanged"
    assert result.path == existing
    assert existing.read_bytes() == CSV_BODY.encode()


# test case 9
def test_existing_different_file_is_overwritten_and_returns_updated_with_diff(
    tmp_path, monkeypatch
):
    row_3_old = "2026-09-26,3,ABY0111,19.10\n"
    row_2_new = "2026-09-26,2,ABY0111,21.50\n"
    row_4_new = "2026-09-26,4,ABY0111,18.00\n"
    old_body = (HEADER + ROW_1 + ROW_2 + row_3_old).encode()
    new_body = (HEADER + ROW_1 + row_2_new + row_4_new).encode()
    existing = tmp_path / "20260926_final.csv"
    existing.write_bytes(old_body)
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(200, new_body),
    )

    result = _download_one(date(2026, 9, 26), "final", tmp_path)

    assert result.status == "updated"
    assert result.path == existing
    assert existing.read_bytes() == new_body
    assert result.diff == DiffStats(same=1, changed=1, only_old=1, only_new=1)


# download_prices: input checks (today is fixed at 2026-09-26)
TODAY = date(2026, 9, 26)


def fail_if_called(*args, **kwargs):
    raise AssertionError("requests.get must not be called")

# test case A
def test_reversed_range_returns_message_without_requests(tmp_path, monkeypatch):
    monkeypatch.setattr("requests.get", fail_if_called)

    summary = download_prices(
        date(2026, 9, 25), date(2026, 9, 24), "final", tmp_path, today=TODAY
    )

    assert summary.results == {}
    assert len(summary.messages) == 1
    assert "reversed" in summary.messages[0]
    assert list(tmp_path.iterdir()) == []


# test case B
def test_future_dates_are_skipped_with_message(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(200, CSV_BODY.encode()),
    )

    summary = download_prices(
        date(2026, 9, 25), date(2026, 9, 28), "final", tmp_path, today=TODAY
    )

    assert list(summary.results) == [date(2026, 9, 25), date(2026, 9, 26)]
    assert all(r.status == "downloaded" for r in summary.results.values())
    assert len(summary.messages) == 1
    assert "2026-09-27" in summary.messages[0]
    assert "2026-09-28" in summary.messages[0]
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "20260925_final.csv",
        "20260926_final.csv",
    ]


# test case C
def test_all_future_dates_returns_two_messages_without_requests(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("requests.get", fail_if_called)

    summary = download_prices(
        date(2026, 9, 27), date(2026, 9, 28), "final", tmp_path, today=TODAY
    )

    assert summary.results == {}
    assert len(summary.messages) == 2
    assert "2026-09-27" in summary.messages[0]
    assert "2026-09-28" in summary.messages[0]
    assert "no dates" in summary.messages[1]
    assert list(tmp_path.iterdir()) == []
