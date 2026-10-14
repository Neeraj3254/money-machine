
from pathlib import Path
import io
import zipfile
from unittest.mock import Mock, patch

import pytest

import research.market.data_expansion as expansion
from research.market.data_expansion import (
    date_range,
    expected_zip_path,
)


def test_date_range():
    result = list(
        date_range(
            "2026-01-01",
            "2026-01-03",
        )
    )

    assert result == [
        "2026-01-01",
        "2026-01-02",
        "2026-01-03",
    ]


def test_date_range_rejects_invalid_order():
    with pytest.raises(ValueError):
        list(
            date_range(
                "2026-01-03",
                "2026-01-01",
            )
        )


def test_expected_zip_path():
    path = expected_zip_path("2026-01-02")

    assert path == Path(
        "data/market/raw/"
        "BhavCopy_NSE_CM_0_0_0_20260102_F_0000.csv.zip"
    )


def test_expected_zip_path_uses_nse_filename():
    path = expected_zip_path("2021-01-04")

    assert path.name == (
        "BhavCopy_NSE_CM_0_0_0_20210104_F_0000.csv.zip"
    )


def make_valid_zip():
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "sample.csv",
            "SYMBOL,CLSPRIC\nTEST,100\n",
        )

    return buffer.getvalue()


def test_download_rejects_invalid_zip_without_saving(tmp_path):
    response = Mock()
    response.status_code = 200
    response.content = b"this is not a zip archive"
    response.raise_for_status.return_value = None

    with (
        patch.object(expansion, "RAW_DATA_DIR", tmp_path),
        patch.object(
            expansion,
            "MANIFEST_DIR",
            tmp_path / "manifests",
        ),
        patch.object(
            expansion,
            "MANIFEST_PATH",
            tmp_path / "manifests" / "manifest.json",
        ),
        patch.object(
            expansion.requests,
            "get",
            return_value=response,
        ),
    ):
        with pytest.raises(zipfile.BadZipFile):
            expansion.download_nse_equity_day("2026-01-05")

    assert not list(tmp_path.glob("*.zip"))


def test_download_accepts_valid_zip(tmp_path):
    response = Mock()
    response.status_code = 200
    response.content = make_valid_zip()
    response.raise_for_status.return_value = None

    with (
        patch.object(expansion, "RAW_DATA_DIR", tmp_path),
        patch.object(
            expansion,
            "MANIFEST_DIR",
            tmp_path / "manifests",
        ),
        patch.object(
            expansion,
            "MANIFEST_PATH",
            tmp_path / "manifests" / "manifest.json",
        ),
        patch.object(
            expansion.requests,
            "get",
            return_value=response,
        ),
    ):
        result = expansion.download_nse_equity_day("2026-01-05")

    assert result["status"] == "DOWNLOADED"
    assert zipfile.is_zipfile(result["path"])


def test_download_rejects_corrupt_cached_zip(tmp_path):
    output_path = tmp_path / expected_zip_path(
        "2026-01-05"
    ).name
    output_path.write_bytes(b"not a valid zip")

    with (
        patch.object(expansion, "RAW_DATA_DIR", tmp_path),
        patch.object(
            expansion,
            "MANIFEST_DIR",
            tmp_path / "manifests",
        ),
        patch.object(
            expansion,
            "MANIFEST_PATH",
            tmp_path / "manifests" / "manifest.json",
        ),
        patch.object(expansion.requests, "get") as mock_get,
    ):
        with pytest.raises(zipfile.BadZipFile):
            expansion.download_nse_equity_day("2026-01-05")

        mock_get.assert_not_called()
