import pandas as pd
import pytest

from research.v2_engine.runner import run_dataframe_experiment


def test_runner_compares_signal_with_non_signal_control():
    df = pd.DataFrame({
        "V2_002_Signal": [True, False, True, False],
        "Forward_Return_20D": [0.10, 0.02, 0.06, -0.02],
    })

    result = run_dataframe_experiment(
        experiment_id="V2-002",
        df=df,
        signal_column="V2_002_Signal",
        forward_return_column="Forward_Return_20D",
        cost_per_trade=0.001,
    )

    assert result.signal_return == pytest.approx(0.08)
    assert result.baseline_return == pytest.approx(0.0)
    assert result.incremental_return == pytest.approx(0.08)


def test_runner_rejects_missing_control_group():
    df = pd.DataFrame({
        "V2_002_Signal": [True, True],
        "Forward_Return_20D": [0.10, 0.06],
    })

    with pytest.raises(ValueError, match="control"):
        run_dataframe_experiment(
            experiment_id="V2-002",
            df=df,
            signal_column="V2_002_Signal",
            forward_return_column="Forward_Return_20D",
        )