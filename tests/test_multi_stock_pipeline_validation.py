import pandas as pd
import pytest

from data.multi_stock_pipeline import validate_market_data


def valid_market_data():
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": [103.0, 104.0, 105.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [102.0, 103.0, 104.0],
            "Volume": [1000, 1100, 1200],
        },
        index=pd.date_range("2025-01-01", periods=3, freq="D"),
    )


def test_valid_market_data_is_accepted():
    validate_market_data(valid_market_data(), "TEST")


def test_unsorted_dates_are_rejected():
    df = valid_market_data().iloc[::-1]

    with pytest.raises(ValueError, match="sorted"):
        validate_market_data(df, "TEST")


def test_duplicate_dates_are_rejected():
    df = valid_market_data()
    df.index = pd.DatetimeIndex(
        ["2025-01-01", "2025-01-02", "2025-01-02"]
    )

    with pytest.raises(ValueError, match="duplicate"):
        validate_market_data(df, "TEST")


def test_missing_close_column_is_rejected():
    df = valid_market_data().drop(columns=["Close"])

    with pytest.raises(ValueError, match="missing required columns"):
        validate_market_data(df, "TEST")


def test_non_positive_close_is_rejected():
    df = valid_market_data()
    df.loc[df.index[0], "Close"] = 0

    with pytest.raises(ValueError, match="Close must be positive"):
        validate_market_data(df, "TEST")


def test_negative_volume_is_rejected():
    df = valid_market_data()
    df.loc[df.index[0], "Volume"] = -1

    with pytest.raises(ValueError, match="Volume cannot be negative"):
        validate_market_data(df, "TEST")


def test_high_below_low_is_rejected():
    df = valid_market_data()
    df.loc[df.index[0], "High"] = 98

    with pytest.raises(ValueError, match="High cannot be below Low"):
        validate_market_data(df, "TEST")