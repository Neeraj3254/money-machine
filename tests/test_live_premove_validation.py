import pandas as pd
from research.market.live_premove import _relative_strength_diagnostics
from research.market.live_premove import _one_symbol
def sample_history(volume):
    return pd.DataFrame(
        {
            "Open": [100.0],
            "High": [105.0],
            "Low": [95.0],
            "Close": [102.0],
            "Volume": [volume],
        },
        index=pd.DatetimeIndex(
            ["2026-10-08"],
            name="Date",
        ),
    )
def test_zero_volume_stock_row_is_rejected():
    result = _one_symbol(
        sample_history(0),
        "TEST.NS",
    )
    assert result.empty
def test_positive_volume_stock_row_is_retained():
    result = _one_symbol(
        sample_history(1000),
        "TEST.NS",
    )
    assert len(result) == 1
    assert result.iloc[0]["TTLTRADGVOL"] == 1000
    assert result.iloc[0]["CLSPRIC"] == 102.0


def test_relative_strength_diagnostics_all_values_present():
    result = pd.DataFrame({
        "Relative_Strength_NIFTY_20D": [0.01, -0.02, 0.03],
    })

    diagnostics = _relative_strength_diagnostics(result)

    assert diagnostics["relative_strength_evidence"] == "available"
    assert diagnostics["missing_relative_strength_count"] == 0


def test_relative_strength_diagnostics_counts_missing_values():
    result = pd.DataFrame({
        "Relative_Strength_NIFTY_20D": [0.01, float("nan"), -0.02],
    })

    diagnostics = _relative_strength_diagnostics(result)

    assert diagnostics["relative_strength_evidence"] == "missing_values"
    assert diagnostics["missing_relative_strength_count"] == 1


def test_relative_strength_diagnostics_handles_missing_column():
    result = pd.DataFrame({"SYMBOL": ["TEST"]})

    diagnostics = _relative_strength_diagnostics(result)

    assert diagnostics["relative_strength_evidence"] == "unavailable"
    assert diagnostics["missing_relative_strength_count"] is None
