
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


@pytest.mark.parametrize(
    "invalid_isin",
    [None, "", "   ", "NAN", "NULL"],
    ids=["missing", "blank", "whitespace", "nan-placeholder", "null-placeholder"],
)
def test_build_equity_universe_rejects_malformed_isin_before_filtering(
    tmp_path, monkeypatch, invalid_isin
):
    master_path = tmp_path / "security_master.csv"
    universe_path = tmp_path / "equity_universe.csv"

    def fake_download(output_path):
        pd.DataFrame({
            "SYMBOL": ["RELIANCE", "BOND1"],
            "SERIES": ["EQ", "BE"],
            "ISIN": ["INE002A01018", invalid_isin],
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


@pytest.mark.parametrize(
    "invalid_column, invalid_value",
    [("SYMBOL", ""), ("SERIES", None)],
    ids=["blank-symbol", "missing-series"],
)
def test_build_equity_universe_rejects_malformed_required_master_fields(
    tmp_path, monkeypatch, invalid_column, invalid_value
):
    master_path = tmp_path / "security_master.csv"
    universe_path = tmp_path / "equity_universe.csv"
    master = pd.DataFrame({
        "SYMBOL": ["RELIANCE", "TCS"],
        "SERIES": ["EQ", "EQ"],
        "ISIN": ["INE002A01018", "INE467B01029"],
    })
    master.loc[1, invalid_column] = invalid_value

    def fake_download(output_path):
        master.to_csv(output_path, index=False)
        return output_path

    monkeypatch.setattr(
        nse_ingest,
        "download_security_master",
        fake_download,
    )

    with pytest.raises(ValueError, match=invalid_column):
        nse_ingest.build_equity_universe(
            str(master_path),
            str(universe_path),
        )

    assert not universe_path.exists()
