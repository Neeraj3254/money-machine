import pandas as pd
import pytest
from research.market.premove import add_premove_scores
@pytest.mark.parametrize(
    ("name", "column", "value", "near_high", "expected"),
    [
        ("One-day rise", "Return_1D", 0.08, False, 3.0),
        ("Large gap", "Gap_Pct", 0.05, False, 2.0),
        ("Volume surge", "RVOL_5D", 5.0, False, 1.5),
        ("Range expansion", "ATR_Range_Ratio", 3.0, False, 1.5),
        ("Rise near 20-day high", "Return_1D", 0.05, True, 1.5),
    ],
)
def test_chase_risk_rules(name, column, value, near_high, expected):
    row = {
        "RVOL_5D": 1.0,
        "RVOL_20D": 1.0,
        "ATR_Range_Ratio": 1.0,
        "Above_EMA_20": False,
        "EMA_Bullish_20_50": False,
        "EMA_Bullish_50_200": False,
        "Return_5D": 0.0,
        "Return_20D": 0.0,
        "Breakout_5D": False,
        "Breakout_20D": False,
        "Breakout_50D": False,
        "Breakout_52W": False,
        "RSI_14": 40.0,
        "MACD_Bullish": False,
        "Relative_Strength_NIFTY_20D": 0.0,
        "Liquid_Stock": False,
        "Near_20D_High": near_high,
        "Return_1D": 0.0,
        "Gap_Pct": 0.0,
    }
    row[column] = value
    result = add_premove_scores(pd.DataFrame([row]))
    actual = float(result["Chase_Risk"].iloc[0])
    assert actual == pytest.approx(expected), (
        f"{name}: expected {expected}, got {actual}"
    )
