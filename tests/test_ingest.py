# tests/test_ingest.py
from datetime import date
from pathlib import Path

import pytest
import requests

from nzpower.ingest import (
    DiffStats,
    DownloadError,
    FinalOverdue,
    InvalidContent,
    PartialDownloadError,
    _download_one,
    download_prices,
    main,
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
        date(2026, 9, 25),
        date(2026, 9, 24),
        "final",
        tmp_path,
        final_grace_days=7,
        today=TODAY,
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
        date(2026, 9, 25),
        date(2026, 9, 28),
        "final",
        tmp_path,
        final_grace_days=7,
        today=TODAY,
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
        date(2026, 9, 27),
        date(2026, 9, 28),
        "final",
        tmp_path,
        final_grace_days=7,
        today=TODAY,
    )

    assert summary.results == {}
    assert len(summary.messages) == 2
    assert "2026-09-27" in summary.messages[0]
    assert "2026-09-28" in summary.messages[0]
    assert "no dates" in summary.messages[1]
    assert list(tmp_path.iterdir()) == []


# test case D
def test_normal_range_downloads_every_date_without_messages(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(200, CSV_BODY.encode()),
    )

    summary = download_prices(
        date(2026, 9, 24),
        date(2026, 9, 26),
        "final",
        tmp_path,
        final_grace_days=7,
        today=TODAY,
    )

    assert list(summary.results) == [
        date(2026, 9, 24),
        date(2026, 9, 25),
        date(2026, 9, 26),
    ]
    assert all(r.status == "downloaded" for r in summary.results.values())
    assert summary.messages == []


# test case E
def test_failed_date_does_not_stop_others_and_raises_partial_error(
    tmp_path, monkeypatch
):
    def fake_get(url, *args, **kwargs):
        if "20260925" in url:
            return FakeResponse(500, b"Server Error")
        return FakeResponse(200, CSV_BODY.encode())

    monkeypatch.setattr("requests.get", fake_get)

    with pytest.raises(PartialDownloadError) as excinfo:
        download_prices(
            date(2026, 9, 24),
            date(2026, 9, 26),
            "final",
            tmp_path,
            final_grace_days=7,
            today=TODAY,
        )

    error = excinfo.value
    assert [day for day, _ in error.failures] == [date(2026, 9, 25)]
    assert isinstance(error.failures[0][1], DownloadError)
    assert list(error.summary.results) == [date(2026, 9, 24), date(2026, 9, 26)]
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "20260924_final.csv",
        "20260926_final.csv",
    ]


# test case F
def test_final_404_beyond_grace_days_is_overdue_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(404, b"<html>Not Found</html>"),
    )

    with pytest.raises(PartialDownloadError) as excinfo:
        download_prices(
            date(2026, 9, 18),
            date(2026, 9, 19),
            "final",
            tmp_path,
            final_grace_days=7,
            today=TODAY,
        )

    error = excinfo.value
    # 09-18 is 8 days before today: overdue. 09-19 is exactly 7: still waiting.
    assert [day for day, _ in error.failures] == [date(2026, 9, 18)]
    assert isinstance(error.failures[0][1], FinalOverdue)
    message = str(error.failures[0][1])
    assert "2026-09-18" in message
    assert "final" in message
    assert "7" in message
    assert list(error.summary.results) == [date(2026, 9, 19)]
    assert error.summary.results[date(2026, 9, 19)].status == "final_not_published"
    assert list(tmp_path.iterdir()) == []


# test case G
def test_interim_404_is_never_overdue(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(404, b"<html>Not Found</html>"),
    )

    summary = download_prices(
        date(2026, 9, 1),
        date(2026, 9, 2),
        "interim",
        tmp_path,
        final_grace_days=7,
        today=TODAY,
    )

    assert list(summary.results) == [date(2026, 9, 1), date(2026, 9, 2)]
    assert all(r.status == "interim_withdrawn" for r in summary.results.values())
    assert summary.messages == []

# test case H
def test_invalid_kind_raises_value_error_even_for_empty_range(tmp_path, monkeypatch):
    monkeypatch.setattr("requests.get", fail_if_called)

    with pytest.raises(ValueError) as excinfo:
        download_prices(
            date(2026, 9, 25),
            date(2026, 9, 24),
            "draft",
            tmp_path,
            final_grace_days=7,
            today=TODAY,
        )

    assert "draft" in str(excinfo.value)


# test case 16
def test_failed_write_keeps_existing_file_and_leaves_no_temp_file(
    tmp_path, monkeypatch
):
    old_body = CSV_BODY.encode()
    new_body = (HEADER + ROW_1).encode()
    existing = tmp_path / "20260926_final.csv"
    existing.write_bytes(old_body)
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(200, new_body),
    )
    original_write_bytes = Path.write_bytes

    def broken_write_bytes(self, data):
        original_write_bytes(self, data[:10])
        raise OSError("disk full")

    monkeypatch.setattr("pathlib.Path.write_bytes", broken_write_bytes)

    with pytest.raises(OSError):
        _download_one(date(2026, 9, 26), "final", tmp_path)

    assert existing.read_bytes() == old_body
    assert list(tmp_path.iterdir()) == [existing]


# CLI tests (use the real clock; the dates used are in the past)
def cli_args(tmp_path, start, end):
    return [
        "--start", start,
        "--end", end,
        "--kind", "final",
        "--final-grace-days", "7",
        "--dest", str(tmp_path),
    ]


# test case CLI-1
def test_cli_success_prints_counts_and_exits_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(200, CSV_BODY.encode()),
    )

    exit_code = main(cli_args(tmp_path, "2026-09-25", "2026-09-26"))

    assert exit_code == 0
    assert "downloaded: 2" in capsys.readouterr().out
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "20260925_final.csv",
        "20260926_final.csv",
    ]

# test case CLI-2
def test_cli_partial_failure_exits_one_and_reports_failures(
    tmp_path, monkeypatch, capsys
):
    def fake_get(url, *args, **kwargs):
        if "20260925" in url:
            return FakeResponse(500, b"Server Error")
        return FakeResponse(200, CSV_BODY.encode())

    monkeypatch.setattr("requests.get", fake_get)

    exit_code = main(cli_args(tmp_path, "2026-09-25", "2026-09-26"))

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "downloaded: 1" in captured.out
    assert "2026-09-25" in captured.err
    assert "HTTP 500" in captured.err

# test case CLI-3
def test_cli_reversed_range_prints_message_and_exits_zero(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr("requests.get", fail_if_called)

    exit_code = main(cli_args(tmp_path, "2026-09-26", "2026-09-25"))

    assert exit_code == 0
    assert "reversed" in capsys.readouterr().out

# test case CLI-4
def test_cli_invalid_date_format_exits_with_code_two(tmp_path, monkeypatch):
    monkeypatch.setattr("requests.get", fail_if_called)

    with pytest.raises(SystemExit) as excinfo:
        main(cli_args(tmp_path, "26-09-2026", "2026-09-26"))

    assert excinfo.value.code == 2


# test case 17
def test_missing_dest_directory_is_created(tmp_path, monkeypatch):
    dest = tmp_path / "a" / "b"
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(200, CSV_BODY.encode()),
    )

    result = _download_one(date(2026, 9, 26), "final", dest)

    assert result.status == "downloaded"
    assert result.path == dest / "20260926_final.csv"
    assert result.path.read_bytes() == CSV_BODY.encode()

# test case 18
def test_missing_dest_directory_is_not_created_when_nothing_to_write(
    tmp_path, monkeypatch
):
    dest = tmp_path / "a"
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse(404, b"<html>Not Found</html>"),
    )

    result = _download_one(date(2026, 9, 26), "final", dest)

    assert result.status == "final_not_published"
    assert not dest.exists()
