import numpy as np
import pandas as pd


def add_price_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build price, momentum, trend, volatility,
    volume and drawdown features.

    Calculations are performed separately for
    each security and sorted chronologically.
    """

    required_columns = [
        "TRADE_DATE",
        "ISIN",
        "SYMBOL",
        "CLSPRIC",
        "TTLTRADGVOL",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    result = df.copy()

    result["TRADE_DATE"] = pd.to_datetime(
        result["TRADE_DATE"]
    )

    result["CLSPRIC"] = pd.to_numeric(
        result["CLSPRIC"],
        errors="coerce",
    )

    result["TTLTRADGVOL"] = pd.to_numeric(
        result["TTLTRADGVOL"],
        errors="coerce",
    )

    result = result.sort_values(
        ["ISIN", "TRADE_DATE"]
    ).reset_index(drop=True)

    grouped = result.groupby(
        "ISIN",
        group_keys=False,
    )

    # -------------------------
    # Momentum
    # -------------------------

    result["Return_1D"] = grouped["CLSPRIC"].pct_change(
    1,
    fill_method=None,
)

    result["Return_5D"] = grouped["CLSPRIC"].pct_change(
    5,
    fill_method=None,
)

    result["Return_20D"] = grouped["CLSPRIC"].pct_change(
    20,
    fill_method=None,
)

    result["Return_60D"] = grouped["CLSPRIC"].pct_change(
    60,
    fill_method=None,
)

    # -------------------------
    # Moving averages
    # -------------------------

    result["SMA_20"] = grouped["CLSPRIC"].transform(
        lambda x: x.rolling(20).mean()
    )

    result["SMA_50"] = grouped["CLSPRIC"].transform(
        lambda x: x.rolling(50).mean()
    )

    result["SMA_120"] = grouped["CLSPRIC"].transform(
        lambda x: x.rolling(120).mean()
    )

    # -------------------------
    # Price vs trend
    # -------------------------

    result["Price_vs_SMA20"] = (
        result["CLSPRIC"] / result["SMA_20"]
    ) - 1

    result["Price_vs_SMA50"] = (
        result["CLSPRIC"] / result["SMA_50"]
    ) - 1

    result["Price_vs_SMA120"] = (
        result["CLSPRIC"] / result["SMA_120"]
    ) - 1

    # -------------------------
    # Volatility
    # -------------------------

    result["Volatility_20D"] = grouped[
        "Return_1D"
    ].transform(
        lambda x: x.rolling(20).std()
    ) * np.sqrt(252)

    result["Volatility_60D"] = grouped[
        "Return_1D"
    ].transform(
        lambda x: x.rolling(60).std()
    ) * np.sqrt(252)

    # -------------------------
    # Volume
    # -------------------------

    result["Volume_SMA20"] = grouped[
        "TTLTRADGVOL"
    ].transform(
        lambda x: x.rolling(20).mean()
    )

    result["Volume_Ratio"] = (
        result["TTLTRADGVOL"]
        / result["Volume_SMA20"]
    )

    # -------------------------
    # Drawdown
    # -------------------------

    result["Rolling_60D_High"] = grouped[
        "CLSPRIC"
    ].transform(
        lambda x: x.rolling(60).max()
    )

    result["Drawdown_60D"] = (
        result["CLSPRIC"]
        / result["Rolling_60D_High"]
    ) - 1

    return result