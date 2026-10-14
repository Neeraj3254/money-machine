import pandas as pd
import pytest
from research.v2_engine.oos import evaluate_oos
def test_oos_reports_signal_vs_non_signal_control():
    df = pd.DataFrame(
        {
            "V2_002_Signal": [True, False, True, False],
            "Forward_Return_20D": [0.10, 0.02, 0.06, -0.02],
        }
    )
    result = evaluate_oos(
        test_df=df,
        signal_column="V2_002_Signal",
        forward_return_column="Forward_Return_20D",
    )
    # Signal mean: (10% + 6%) / 2 = 8%
    assert result["oos_return"] == pytest.approx(0.08)
    # All-observations mean: (10% + 2% + 6% - 2%) / 4 = 4%
    assert result["baseline_return"] == pytest.approx(0.04)
    assert result["oos_incremental_return"] == pytest.approx(0.04)
    # Non-signal control mean: (2% - 2%) / 2 = 0%
    assert result["control_return"] == pytest.approx(0.0)
    assert result["signal_vs_control_incremental_return"] == pytest.approx(0.08)
    assert result["control_sample_size"] == 2
    assert result["sample_size"] == 2
def test_oos_rejects_missing_signal_group_or_control_group():
    df = pd.DataFrame(
        {
            "V2_002_Signal": [True, True],
            "Forward_Return_20D": [0.10, 0.06],
        }
    )
    with pytest.raises(ValueError, match="control"):
        evaluate_oos(
            test_df=df,
            signal_column="V2_002_Signal",
            forward_return_column="Forward_Return_20D",
        )
def test_oos_rejects_missing_signal_column():
    df = pd.DataFrame({"Forward_Return_20D": [0.10, 0.02]})
    with pytest.raises(ValueError, match="signal column"):
        evaluate_oos(
            test_df=df,
            signal_column="V2_002_Signal",
            forward_return_column="Forward_Return_20D",
        )
def test_oos_rejects_missing_forward_return_column():
    df = pd.DataFrame({"V2_002_Signal": [True, False]})
    with pytest.raises(ValueError, match="forward-return column"):
        evaluate_oos(
            test_df=df,
            signal_column="V2_002_Signal",
            forward_return_column="Forward_Return_20D",
        )
