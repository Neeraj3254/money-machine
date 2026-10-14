import pandas as pd
import pytest
from research.validation.leakage import check_temporal_leakage
def test_temporal_leakage_passes_when_target_is_after_signal():
    df = pd.DataFrame({
        "TRADE_DATE": ["2025-01-01", "2025-01-02"],
        "TARGET_DATE": ["2025-01-21", "2025-01-22"],
    })
    result = check_temporal_leakage(df)
    assert result.status == "PASS"
    assert result.passed is True
    assert result.evidence["leakage_rows"] == 0
def test_temporal_leakage_fails_when_target_is_same_day():
    df = pd.DataFrame({
        "TRADE_DATE": ["2025-01-01"],
        "TARGET_DATE": ["2025-01-01"],
    })
    result = check_temporal_leakage(df)
    assert result.status == "FAIL"
    assert result.passed is False
    assert result.evidence["leakage_rows"] == 1
def test_temporal_leakage_fails_when_target_precedes_signal():
    df = pd.DataFrame({
        "TRADE_DATE": ["2025-01-10"],
        "TARGET_DATE": ["2025-01-09"],
    })
    result = check_temporal_leakage(df)
    assert result.status == "FAIL"
    assert result.passed is False
def test_temporal_leakage_is_inconclusive_when_columns_are_missing():
    df = pd.DataFrame({"TRADE_DATE": ["2025-01-01"]})
    result = check_temporal_leakage(df)
    assert result.status == "INCONCLUSIVE"
    assert result.passed is None
def test_temporal_leakage_is_inconclusive_for_invalid_signal_date():
    df = pd.DataFrame({
        "TRADE_DATE": ["not-a-date"],
        "TARGET_DATE": ["2025-01-21"],
    })
    result = check_temporal_leakage(df)
    assert result.status == "INCONCLUSIVE"
    assert result.passed is None
def test_missing_target_date_does_not_count_as_a_pass_for_all_rows():
    df = pd.DataFrame({
        "TRADE_DATE": ["2025-01-01", "2025-01-02"],
        "TARGET_DATE": ["2025-01-21", None],
    })
    result = check_temporal_leakage(df)
    assert result.status == "PASS"
    assert result.evidence["missing_target_dates"] == 1
    assert result.evidence["rows_checked"] == 1
