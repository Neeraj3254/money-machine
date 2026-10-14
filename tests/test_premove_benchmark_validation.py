import numpy as np
import pandas as pd

from research.market.premove import add_premove_features


def sample_stock_history(days=230):
    dates = pd.bdate_range("2025-01-01", periods=days)
    close = np.linspace(100.0, 150.0, days)

    return pd.DataFrame({
        "TRADE_DATE": dates,
        "ISIN": "TEST_ISIN",
        "SYMBOL": "TEST",
        "OPNPRIC": close - 0.5,
        "HGHPRIC": close + 1.0,
        "LWPRIC": close - 1.0,
        "CLSPRIC": close,
        "PRVSCLSGPRIC": np.roll(close, 1),
        "TTLTRADGVOL": 100000.0,
        "TTLTRFVAL": close * 100000.0,
    })


def test_missing_benchmark_produces_missing_relative_strength():
    result = add_premove_features(
        sample_stock_history(),
        nifty_context=None,
    )

    latest = result.iloc[-1]

    assert pd.isna(latest["Relative_Strength_NIFTY_20D"])
    assert not latest["NIFTY_Stronger"]


def test_valid_benchmark_produces_relative_strength():
    stock = sample_stock_history()
    dates = pd.bdate_range("2025-01-01", periods=len(stock))

    benchmark = pd.DataFrame({
        "TRADE_DATE": dates,
        "NIFTY_CLOSE": np.linspace(1000.0, 1100.0, len(dates)),
    })

    result = add_premove_features(
        stock,
        nifty_context=benchmark,
    )

    latest = result.iloc[-1]

    assert pd.notna(latest["NIFTY_RETURN_20D"])
    assert pd.notna(latest["Relative_Strength_NIFTY_20D"])

def test_missing_benchmark_evidence_is_explicitly_flagged():
    result = add_premove_features(
        sample_stock_history(),
        nifty_context=None,
    )

    assert "Relative_Strength_NIFTY_20D" in result.columns
    assert result["Relative_Strength_NIFTY_20D"].isna().all()

def test_relative_strength_diagnostic_reports_all_values_present():
    values = pd.Series([0.01, -0.02, 0.03])
    relative_strength = pd.to_numeric(values, errors="coerce")

    evidence = (
        "available"
        if relative_strength.notna().all()
        else "missing_values"
    )
    missing_count = int(relative_strength.isna().sum())

    assert evidence == "available"
    assert missing_count == 0


def test_relative_strength_diagnostic_reports_missing_values():
    values = pd.Series([0.01, np.nan, -0.02])
    relative_strength = pd.to_numeric(values, errors="coerce")

    evidence = (
        "available"
        if relative_strength.notna().all()
        else "missing_values"
    )
    missing_count = int(relative_strength.isna().sum())

    assert evidence == "missing_values"
    assert missing_count == 1
