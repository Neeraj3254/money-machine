import pandas as pd
from research.v2_engine.outcomes import add_forward_return
def test_forward_return_20d_uses_close_20_rows_ahead():
    dates = pd.bdate_range("2025-01-01", periods=25)
    df = pd.DataFrame({
        "Date": dates,
        "Close": range(100, 125),
    })
    result = add_forward_return(df, horizon_days=20)
    assert result.loc[0, "Forward_Return_20D"] == 120 / 100 - 1
    assert result.loc[4, "Forward_Return_20D"] == 124 / 104 - 1
    assert result["Forward_Return_20D"].iloc[-20:].isna().all()
def test_forward_return_rejects_unsorted_dates():
    df = pd.DataFrame({
        "Date": pd.to_datetime(["2025-01-03", "2025-01-02"]),
        "Close": [102.0, 101.0],
    })
    try:
        add_forward_return(df, horizon_days=1)
    except ValueError as exc:
        assert "chronological" in str(exc)
    else:
        raise AssertionError("Expected unsorted dates to be rejected")
