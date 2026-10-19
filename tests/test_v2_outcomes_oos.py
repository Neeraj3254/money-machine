import pandas as pd
import pytest
from research.v2_engine.outcomes import add_forward_return
from research.v2_engine.features import build_trend_strength
from research.v2_engine.oos import split_train_test
def test_forward_return_uses_future_close():
    df = pd.DataFrame({"Close": [100.0, 110.0, 121.0, 133.1]})
    result = add_forward_return(df, horizon_days=2)
    assert result.loc[0, "Forward_Return_2D"] == pytest.approx(0.21)
    assert pd.isna(result.loc[2, "Forward_Return_2D"])
    assert pd.isna(result.loc[3, "Forward_Return_2D"])
def test_forward_return_rejects_unsorted_dates():
    df = pd.DataFrame({
        "Date": ["2024-01-03", "2024-01-01", "2024-01-02"],
        "Close": [103.0, 100.0, 101.0],
    })
    with pytest.raises(ValueError, match="chronological"):
        add_forward_return(df, horizon_days=1)
def test_oos_split_purges_overlapping_training_outcomes():
    df = pd.DataFrame({
        "Date": pd.date_range("2024-01-01", periods=10),
        "Close": range(100, 110),
        "Forward_Return_2D": [0.01] * 8 + [float("nan")] * 2,
    })
    train, test = split_train_test(
        df,
        train_ratio=0.7,
        purge_periods=2,
    )
    assert len(train) == 5
    assert len(test) == 3
    assert train["Date"].max() < test["Date"].min()
def test_oos_split_rejects_invalid_purge_periods():
    df = pd.DataFrame({"Close": range(10)})
    with pytest.raises(ValueError, match="purge"):
        split_train_test(df, train_ratio=0.7, purge_periods=-1)

def test_oos_split_rejects_purge_shorter_than_label_horizon():
    df = pd.DataFrame({"Close": range(100, 120)})

    with pytest.raises(ValueError, match="at least label_horizon"):
        split_train_test(
            df,
            train_ratio=0.7,
            purge_periods=5,
            label_horizon=20,
        )


def test_trend_signal_before_cutoff_is_independent_of_future_rows():
    df = pd.DataFrame({
        "Close": [100, 102, 101, 105, 108, 110, 107, 112],
        "Price_vs_SMA20": [-0.02, 0.01, 0.00, 0.03, 0.04, 0.05, -0.01, 0.06],
        "Price_vs_SMA50": [-0.03, 0.00, 0.01, 0.02, 0.03, 0.04, -0.02, 0.05],
        "Price_vs_SMA200": [-0.04, -0.01, 0.02, 0.01, 0.02, 0.03, -0.03, 0.04],
    })

    cutoff = 4
    original = build_trend_strength(df)

    changed = df.copy()
    future_rows = changed.index > cutoff
    changed.loc[future_rows, "Close"] *= 3
    changed.loc[future_rows, "Price_vs_SMA20"] *= -10
    changed.loc[future_rows, "Price_vs_SMA50"] *= -10
    changed.loc[future_rows, "Price_vs_SMA200"] *= -10

    modified = build_trend_strength(changed)

    pd.testing.assert_series_equal(
        original.loc[:cutoff, "V2_002_Signal"],
        modified.loc[:cutoff, "V2_002_Signal"],
    )
def test_trend_strength_does_not_use_forward_return_column():
    from research.v2_engine.features import build_trend_strength
    df = pd.DataFrame({
        "Close": [100.0, 102.0, 104.0, 103.0],
        "Price_vs_SMA20": [0.01, 0.02, 0.03, 0.01],
        "Price_vs_SMA50": [0.01, 0.01, 0.02, 0.00],
        "Price_vs_SMA200": [0.00, 0.01, 0.01, -0.01],
        "Forward_Return_20D": [0.50, -0.40, 0.30, -0.20],
    })
    result = build_trend_strength(df)
    expected = (
        df["Price_vs_SMA20"]
        + df["Price_vs_SMA50"]
        + df["Price_vs_SMA200"]
    ) > 0
    pd.testing.assert_series_equal(
        result["V2_002_Signal"],
        expected.rename("V2_002_Signal"),
    )
