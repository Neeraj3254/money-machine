
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

from research.market import nse_ingest


def mock_response(csv_text):
    response = Mock()
    response.content = csv_text.encode("utf-8")
    response.raise_for_status.return_value = None
    return response


def test_download_security_master_saves_normalized_csv(
    tmp_path, monkeypatch
):
    csv_text = (
        "SYMBOL,SERIES,ISIN NUMBER,NAME OF COMPANY\n"
        "reliance,eq,INE002A01018,Reliance Industries\n"
        "tcs,eq,INE467B01029,Tata Consultancy Services\n"
    )

    monkeypatch.setattr(
        nse_ingest.requests,
        "get",
        lambda *args, **kwargs: mock_response(csv_text),
    )

    output = tmp_path / "master.csv"
    result = nse_ingest.download_security_master(str(output))

    assert result == output
    assert output.exists()

    saved = pd.read_csv(output)
    assert list(saved.columns) == ["SYMBOL", "SERIES", "ISIN"]
    assert saved["SYMBOL"].tolist() == ["RELIANCE", "TCS"]
    assert saved["SERIES"].tolist() == ["EQ", "EQ"]


def test_download_security_master_rejects_unexpected_schema(
    tmp_path, monkeypatch
):
    response = mock_response("WRONG,COLUMNS\nA,B\n")

    monkeypatch.setattr(
        nse_ingest.requests,
        "get",
        lambda *args, **kwargs: response,
    )

    output = tmp_path / "master.csv"

    with pytest.raises(ValueError, match="Unexpected NSE format"):
        nse_ingest.download_security_master(str(output))

    assert not output.exists()


def test_download_security_master_propagates_http_error(
    tmp_path, monkeypatch
):
    response = Mock()
    response.raise_for_status.side_effect = RuntimeError("HTTP failure")

    monkeypatch.setattr(
        nse_ingest.requests,
        "get",
        lambda *args, **kwargs: response,
    )

    output = tmp_path / "master.csv"

    with pytest.raises(RuntimeError, match="HTTP failure"):
        nse_ingest.download_security_master(str(output))

    assert not output.exists()


def test_invalid_download_preserves_existing_master(
    tmp_path, monkeypatch
):
    output = tmp_path / "master.csv"
    original = (
        "SYMBOL,SERIES,ISIN\n"
        "RELIANCE,EQ,INE002A01018\n"
    )
    output.write_text(original, encoding="utf-8")

    response = mock_response("WRONG,COLUMNS\nA,B\n")
    monkeypatch.setattr(
        nse_ingest.requests,
        "get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(ValueError, match="Unexpected NSE format"):
        nse_ingest.download_security_master(str(output))

    assert output.read_text(encoding="utf-8") == original


@pytest.mark.parametrize(
    "csv_text, expected_error",
    [
        (
            "SYMBOL,SERIES,ISIN NUMBER\n"
            "RELIANCE,EQ,\n",
            "invalid ISIN values",
        ),
        (
            "SYMBOL,SERIES,ISIN NUMBER\n"
            "RELIANCE,EQ,INE002A01018\n"
            "RELIANCE,EQ,INE467B01029\n",
            "duplicate symbols",
        ),
        (
            "SYMBOL,SERIES,ISIN NUMBER\n"
            "RELIANCE,EQ,INE002A01018\n"
            "TCS,EQ,INE002A01018\n",
            "duplicate ISINs",
        ),
    ],
)
def test_download_security_master_rejects_invalid_identifiers(
    tmp_path, monkeypatch, csv_text, expected_error
):
    response = mock_response(csv_text)
    monkeypatch.setattr(
        nse_ingest.requests,
        "get",
        lambda *args, **kwargs: response,
    )

    output = tmp_path / "master.csv"

    with pytest.raises(ValueError, match=expected_error):
        nse_ingest.download_security_master(str(output))

    assert not output.exists()


def test_duplicate_identifier_failure_preserves_existing_master(
    tmp_path, monkeypatch
):
    output = tmp_path / "master.csv"
    original = (
        "SYMBOL,SERIES,ISIN\n"
        "RELIANCE,EQ,INE002A01018\n"
    )
    output.write_text(original, encoding="utf-8")

    response = mock_response(
        "SYMBOL,SERIES,ISIN NUMBER\n"
        "RELIANCE,EQ,INE002A01018\n"
        "RELIANCE,EQ,INE467B01029\n"
    )
    monkeypatch.setattr(
        nse_ingest.requests,
        "get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(ValueError, match="duplicate symbols"):
        nse_ingest.download_security_master(str(output))

    assert output.read_text(encoding="utf-8") == original
