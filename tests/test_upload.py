# tests/test_upload.py
from nzpower.upload import main, upload_prices

HEADER = "TradingDate,TradingPeriod,PointOfConnection,DollarsPerMegawattHour\n"
BODY_SEP = (HEADER + "2026-09-26,1,ABY0111,23.86\n").encode()
BODY_OCT = (HEADER + "2026-10-01,1,ABY0111,30.00\n").encode()


class FakeContainer:
    """Stands in for azure ContainerClient.upload_blob; mimics overwrite rules."""

    def __init__(self):
        self.blobs = {}

    def upload_blob(self, name, data, overwrite=False):
        if name in self.blobs and not overwrite:
            raise RuntimeError(f"BlobAlreadyExists: {name}")
        self.blobs[name] = data


# test case U1
def test_files_are_uploaded_into_month_partitions(tmp_path):
    (tmp_path / "20260926_final.csv").write_bytes(BODY_SEP)
    (tmp_path / "20260926_interim.csv").write_bytes(BODY_SEP)
    (tmp_path / "20261001_final.csv").write_bytes(BODY_OCT)
    container = FakeContainer()

    summary = upload_prices(tmp_path, container)

    assert container.blobs == {
        "prices/2026-09/20260926_final.csv": BODY_SEP,
        "prices/2026-09/20260926_interim.csv": BODY_SEP,
        "prices/2026-10/20261001_final.csv": BODY_OCT,
    }
    assert summary.uploaded == sorted(container.blobs)
    assert summary.skipped == []

# test case U2
def test_uploading_twice_does_not_duplicate_or_fail(tmp_path):
    (tmp_path / "20260926_final.csv").write_bytes(BODY_SEP)
    container = FakeContainer()

    upload_prices(tmp_path, container)
    upload_prices(tmp_path, container)

    assert list(container.blobs) == ["prices/2026-09/20260926_final.csv"]
    assert container.blobs["prices/2026-09/20260926_final.csv"] == BODY_SEP

# test case U3
def test_unrecognised_files_are_skipped_and_listed(tmp_path):
    (tmp_path / "20260926_final.csv").write_bytes(BODY_SEP)
    (tmp_path / "notes.txt").write_bytes(b"hello")
    (tmp_path / "20260926_final.csv.tmp").write_bytes(b"partial")
    (tmp_path / "subdir").mkdir()
    container = FakeContainer()

    summary = upload_prices(tmp_path, container)

    assert list(container.blobs) == ["prices/2026-09/20260926_final.csv"]
    assert summary.skipped == ["20260926_final.csv.tmp", "notes.txt"]


# CLI tests
ENV_NAME = "AZURE_STORAGE_CONNECTION_STRING"


def patch_client(monkeypatch, container):
    calls = []

    def fake_create(connection_string, container_name):
        calls.append((connection_string, container_name))
        return container

    monkeypatch.setattr("nzpower.upload._create_container_client", fake_create)
    return calls

# test case CLI-U1
def test_cli_uploads_and_prints_counts(tmp_path, monkeypatch, capsys):
    (tmp_path / "20260926_final.csv").write_bytes(BODY_SEP)
    container = FakeContainer()
    calls = patch_client(monkeypatch, container)
    monkeypatch.setenv(ENV_NAME, "fake-connection-string")

    exit_code = main(["--source", str(tmp_path)])

    assert exit_code == 0
    assert "uploaded: 1, skipped: 0" in capsys.readouterr().out
    assert list(container.blobs) == ["prices/2026-09/20260926_final.csv"]
    assert calls == [("fake-connection-string", "raw")]

# test case CLI-U2
def test_cli_without_connection_string_exits_one(tmp_path, monkeypatch, capsys):
    calls = patch_client(monkeypatch, FakeContainer())
    monkeypatch.delenv(ENV_NAME, raising=False)

    exit_code = main(["--source", str(tmp_path)])

    assert exit_code == 1
    assert ENV_NAME in capsys.readouterr().err
    assert calls == []

# test case CLI-U3
def test_cli_lists_skipped_files(tmp_path, monkeypatch, capsys):
    (tmp_path / "20260926_final.csv").write_bytes(BODY_SEP)
    (tmp_path / "notes.txt").write_bytes(b"hello")
    patch_client(monkeypatch, FakeContainer())
    monkeypatch.setenv(ENV_NAME, "fake")

    exit_code = main(["--source", str(tmp_path)])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "uploaded: 1, skipped: 1" in out
    assert "notes.txt" in out

# test case CLI-U4
def test_cli_missing_source_directory_exits_one(tmp_path, monkeypatch, capsys):
    missing = tmp_path / "nope"
    calls = patch_client(monkeypatch, FakeContainer())
    monkeypatch.setenv(ENV_NAME, "fake")

    exit_code = main(["--source", str(missing)])

    assert exit_code == 1
    assert str(missing) in capsys.readouterr().err
    assert calls == []
