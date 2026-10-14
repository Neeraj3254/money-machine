
import pandas as pd
import pytest

from research.market import nse_ingest


def test_build_equity_universe_saves_valid_eq_records(
    tmp_path, monkeypatch
):
    master_path = tmp_path / "security_master.csv"
    universe_path = tmp_path / "equity_universe.csv"

    def fake_download(output_path):
        pd.DataFrame({
            "SYMBOL": ["RELIANCE", "TCS", "BOND1"],
            "SERIES": ["EQ", "EQ", "BE"],
            "ISIN": [
                "INE002A01018",
                "INE467B01029",
                "INE000A00000",
            ],
        }).to_csv(output_path, index=False)
        return output_path

    monkeypatch.setattr(
        nse_ingest,
        "download_security_master",
        fake_download,
    )

    summary = nse_ingest.build_equity_universe(
        str(master_path),
        str(universe_path),
    )

    saved = pd.read_csv(universe_path)

    assert summary["rows"] == 2
    assert saved["SYMBOL"].tolist() == ["RELIANCE", "TCS"]
    assert saved["SERIES"].eq("EQ").all()
    assert saved["ISIN"].is_unique


def test_build_equity_universe_rejects_invalid_master(
    tmp_path, monkeypatch
):
    master_path = tmp_path / "security_master.csv"
    universe_path = tmp_path / "equity_universe.csv"

    def fake_download(output_path):
        pd.DataFrame({
            "SYMBOL": ["RELIANCE", "TCS"],
            "SERIES": ["EQ", "EQ"],
            "ISIN": ["INE002A01018", None],
        }).to_csv(output_path, index=False)
        return output_path

    monkeypatch.setattr(
        nse_ingest,
        "download_security_master",
        fake_download,
    )

    with pytest.raises(ValueError, match="ISIN"):
        nse_ingest.build_equity_universe(
            str(master_path),
            str(universe_path),
        )

    assert not universe_path.exists()
