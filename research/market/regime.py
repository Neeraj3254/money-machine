import numpy as np
import pandas as pd


def load_nifty(path="data/raw/nifty50_daily_unified.csv"):
    """
    Load and validate NIFTY 50 daily data.
    """

    df = pd.read_csv(path)

    required = [
        "Date",
        "Close",
        "High",
        "Low",
        "Open",
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing NIFTY columns: {missing}"
        )

    df["Date"] = pd.to_datetime(df["Date"])

    df = df.sort_values("Date").reset_index(
        drop=True
    )

    return df


def build_regime_features(df):
    """
    Build descriptive NIFTY market-regime features.
    """

    result = df.copy()

    result["Return_20D"] = (
        result["Close"].pct_change(20)
    )

    result["Return_60D"] = (
        result["Close"].pct_change(60)
    )

    result["SMA_20"] = (
        result["Close"]
        .rolling(20)
        .mean()
    )

    result["SMA_50"] = (
        result["Close"]
        .rolling(50)
        .mean()
    )

    result["SMA_200"] = (
        result["Close"]
        .rolling(200)
        .mean()
    )

    result["Price_vs_SMA20"] = (
        result["Close"]
        / result["SMA_20"]
    ) - 1

    result["Price_vs_SMA50"] = (
        result["Close"]
        / result["SMA_50"]
    ) - 1

    result["Price_vs_SMA200"] = (
        result["Close"]
        / result["SMA_200"]
    ) - 1

    daily_return = result["Close"].pct_change()

    result["Volatility_20D"] = (
        daily_return
        .rolling(20)
        .std()
        * np.sqrt(252)
    )

    result["Rolling_252D_High"] = (
        result["Close"]
        .rolling(252)
        .max()
    )

    result["Drawdown_252D"] = (
        result["Close"]
        / result["Rolling_252D_High"]
    ) - 1

    return result


def classify_regime(df):
    """
    Assign a transparent descriptive market regime.

    This is infrastructure, not a validated
    predictive trading signal.
    """

    result = df.copy()

    conditions = [
        (
            (result["Close"] > result["SMA_200"])
            & (result["SMA_50"] > result["SMA_200"])
            & (result["Return_60D"] > 0)
        ),

        (
            (result["Close"] < result["SMA_200"])
            & (result["SMA_50"] < result["SMA_200"])
            & (result["Return_60D"] < 0)
        ),
    ]

    choices = [
        "BULL",
        "BEAR",
    ]

    result["Trend_Regime"] = np.select(
        conditions,
        choices,
        default="SIDEWAYS",
    )

    # Volatility state is relative to its
    # own historical distribution.
    volatility_median = (
        result["Volatility_20D"]
        .rolling(252)
        .median()
    )

    result["Volatility_Regime"] = np.where(
        result["Volatility_20D"]
        > volatility_median,
        "HIGH_VOL",
        "LOW_VOL",
    )

    result["Regime"] = (
        result["Trend_Regime"]
        + "_"
        + result["Volatility_Regime"]
    )

    return result

def build_regime_context(
    path="data/raw/nifty50_daily_unified.csv",
) -> pd.DataFrame:
    """
    Build the market-regime context table used by
    the stock research engine.
    """

    nifty = load_nifty(path)

    nifty = build_regime_features(nifty)

    nifty = classify_regime(nifty)

    context = nifty[
        [
            "Date",
            "Close",
            "Return_20D",
            "Return_60D",
            "SMA_20",
            "SMA_50",
            "SMA_200",
            "Price_vs_SMA20",
            "Price_vs_SMA50",
            "Price_vs_SMA200",
            "Volatility_20D",
            "Drawdown_252D",
            "Trend_Regime",
            "Volatility_Regime",
            "Regime",
        ]
    ].copy()

    context = context.rename(
        columns={
            "Date": "TRADE_DATE",
            "Close": "NIFTY_CLOSE",
            "Return_20D": "NIFTY_RETURN_20D",
            "Return_60D": "NIFTY_RETURN_60D",
            "SMA_20": "NIFTY_SMA20",
            "SMA_50": "NIFTY_SMA50",
            "SMA_200": "NIFTY_SMA200",
            "Price_vs_SMA20": "NIFTY_PRICE_VS_SMA20",
            "Price_vs_SMA50": "NIFTY_PRICE_VS_SMA50",
            "Price_vs_SMA200": "NIFTY_PRICE_VS_SMA200",
            "Volatility_20D": "NIFTY_VOLATILITY_20D",
            "Drawdown_252D": "NIFTY_DRAWDOWN_252D",
        }
    )

    return context