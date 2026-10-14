import pandas as pd
import pytest

from research.v2_engine.stability import evaluate_period


def test_period_compares_signal_with_non_signal_control():
    df = pd.DataFrame({
        "V2_002_Signal": [True, False, True, False],
        "Forward_Return_20D": [0.10, 0.02, 0.06, -0.02],
    })

    result = evaluate_period(
        df,
        signal_column="V2_002_Signal",
        forward_return_column="Forward_Return_20D",
    )

    assert result["signal_return"] == pytest.approx(0.08)
    assert result["baseline_return"] == pytest.approx(0.0)
    assert result["incremental_return"] == pytest.approx(0.08)
    assert result["control_sample_size"] == 2


def test_period_excludes_rows_with_missing_forward_returns():
    df = pd.DataFrame({
        "V2_002_Signal": [True, False, True, False],
        "Forward_Return_20D": [0.10, 0.02, None, -0.02],
    })

    result = evaluate_period(
        df,
        signal_column="V2_002_Signal",
        forward_return_column="Forward_Return_20D",
    )

    assert result["signal_return"] == pytest.approx(0.10)
    assert result["baseline_return"] == pytest.approx(0.0)
    assert result["control_sample_size"] == 2


def test_period_rejects_missing_control_observations():
    df = pd.DataFrame({
        "V2_002_Signal": [True, True],
        "Forward_Return_20D": [0.10, 0.06],
    })

    with pytest.raises(ValueError, match="control"):
        evaluate_period(
            df,
            signal_column="V2_002_Signal",
            forward_return_column="Forward_Return_20D",
        )