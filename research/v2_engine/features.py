import pandas as pd


def build_trend_strength(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the V2-002 Trend Strength feature.

    The feature uses only information available at each timestamp.
    It does not use future returns.
    """

    required_columns = [
        "Close",
        "Price_vs_SMA20",
        "Price_vs_SMA50",
        "Price_vs_SMA200",
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

    result["Trend_Strength"] = (
        result["Price_vs_SMA20"]
        + result["Price_vs_SMA50"]
        + result["Price_vs_SMA200"]
    )

    result["V2_002_Signal"] = (
        result["Trend_Strength"] > 0
    )

    return result