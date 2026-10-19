import pandas as pd
import pytest

from research.market.universe import save_universe, validate_universe

@pytest.fixture
def valid_universe():
    return pd.DataFrame({
        "SYMBOL": ["RELIANCE", "TCS"],
        "SERIES": ["EQ", "EQ"],
        "ISIN": ["INE002A01018", "INE467B01029"],
    })


def test_valid_universe_passes(valid_universe):
    result = validate_universe(valid_universe)

    assert result["rows"] == 2
    assert result["unique_symbols"] == 2
    assert result["unique_isins"] == 2


def test_missing_column_is_rejected(valid_universe):
    with pytest.raises(ValueError, match="missing columns"):
        validate_universe(valid_universe.drop(columns=["ISIN"]))


def test_missing_isin_is_rejected(valid_universe):
    valid_universe.loc[1, "ISIN"] = None

    with pytest.raises(ValueError, match="ISIN"):
        validate_universe(valid_universe)


def test_blank_symbol_is_rejected(valid_universe):
    valid_universe.loc[0, "SYMBOL"] = " "

    with pytest.raises(ValueError, match="SYMBOL"):
        validate_universe(valid_universe)


def test_non_eq_series_is_rejected(valid_universe):
    valid_universe.loc[1, "SERIES"] = "BE"

    with pytest.raises(ValueError, match="EQ"):
        validate_universe(valid_universe)


def test_duplicate_symbol_is_rejected(valid_universe):
    valid_universe.loc[1, "SYMBOL"] = "RELIANCE"

    with pytest.raises(ValueError, match="duplicate symbols"):
        validate_universe(valid_universe)


def test_duplicate_isin_is_rejected(valid_universe):
    valid_universe.loc[1, "ISIN"] = "INE002A01018"

    with pytest.raises(ValueError, match="duplicate ISINs"):
        validate_universe(valid_universe)

def test_save_universe_rejects_invalid_data_without_overwriting(
    tmp_path, valid_universe
):
    output = tmp_path / "equity_universe.csv"
    original = "existing universe content\n"
    output.write_text(original, encoding="utf-8")

    invalid_universe = valid_universe.copy()
    invalid_universe.loc[0, "ISIN"] = None

    with pytest.raises(ValueError, match="ISIN"):
        save_universe(invalid_universe, str(output))

    assert output.read_text(encoding="utf-8") == original
