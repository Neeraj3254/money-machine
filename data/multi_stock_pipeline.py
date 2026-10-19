import pandas as pd
import numpy as np
from pathlib import Path


RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

def validate_market_data(df: pd.DataFrame, ticker: str) -> None:
    """Reject malformed market data before feature generation."""

    required_columns = ["Open", "High", "Low", "Close", "Volume"]
    missing = [column for column in required_columns if column not in df.columns]

    if missing:
        raise ValueError(f"{ticker}: missing required columns: {missing}")

    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(f"{ticker}: dates must be a DatetimeIndex")

    if df.index.hasnans:
        raise ValueError(f"{ticker}: dates contain invalid values")

    if not df.index.is_monotonic_increasing:
        raise ValueError(f"{ticker}: dates must be sorted ascending")

    if df.index.has_duplicates:
        raise ValueError(f"{ticker}: duplicate dates detected")

    numeric = df[required_columns].apply(pd.to_numeric, errors="coerce")

    if numeric.isna().any().any():
        raise ValueError(
            f"{ticker}: required market columns contain missing or "
            "non-numeric values"
        )

    if (numeric["Close"] <= 0).any():
        raise ValueError(f"{ticker}: Close must be positive")

    if (numeric["Volume"] < 0).any():
        raise ValueError(f"{ticker}: Volume cannot be negative")

    if (numeric[["Open", "High", "Low"]] <= 0).any().any():
        raise ValueError(f"{ticker}: Open, High, and Low must be positive")

    if (numeric["High"] < numeric["Low"]).any():
        raise ValueError(f"{ticker}: High cannot be below Low")

    if (numeric["High"] < numeric["Open"]).any() or (
        numeric["High"] < numeric["Close"]
    ).any():
        raise ValueError(f"{ticker}: High is below Open or Close")

    if (numeric["Low"] > numeric["Open"]).any() or (
        numeric["Low"] > numeric["Close"]
    ).any():
        raise ValueError(f"{ticker}: Low is above Open or Close")

    df.loc[:, required_columns] = numeric


def build_features(ticker):

    input_path = RAW_DIR / f"{ticker.lower()}_daily.csv"

    print(f"\nProcessing {ticker}...")
    print("-" * 40)

    df = pd.read_csv(
        input_path,
        index_col=0,
        parse_dates=True
    )

    # Validate input before calculating any features.
    required_columns = ["Open", "High", "Low", "Close", "Volume"]
    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{ticker}: missing required columns: {missing_columns}"
        )

    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(f"{ticker}: dates must parse as a DatetimeIndex")

    if df.index.hasnans:
        raise ValueError(f"{ticker}: dates contain invalid values")

    if not df.index.is_monotonic_increasing:
        raise ValueError(f"{ticker}: dates must be sorted ascending")

    if df.index.has_duplicates:
        raise ValueError(f"{ticker}: duplicate dates detected")

    for column in required_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    if df[required_columns].isna().any().any():
        raise ValueError(
            f"{ticker}: required market columns contain missing or "
            "non-numeric values"
        )

    if (df["Close"] <= 0).any():
        raise ValueError(f"{ticker}: Close must be positive")

    if (df["Volume"] < 0).any():
        raise ValueError(f"{ticker}: Volume cannot be negative")

    if (df[["Open", "High", "Low"]] <= 0).any().any():
        raise ValueError(
            f"{ticker}: Open, High, and Low must be positive"
        )

    if (df["High"] < df["Low"]).any():
        raise ValueError(f"{ticker}: High cannot be below Low")

    # Basic returns
    df["Daily_Return"] = df["Close"].pct_change()

    df["Return_5D"] = df["Close"].pct_change(5)
    df["Return_20D"] = df["Close"].pct_change(20)
    df["Return_60D"] = df["Close"].pct_change(60)

    # Moving averages
    df["SMA_20"] = df["Close"].rolling(20).mean()
    df["SMA_50"] = df["Close"].rolling(50).mean()
    df["SMA_200"] = df["Close"].rolling(200).mean()

    # Price relative to moving averages
    df["Price_vs_SMA20"] = df["Close"] / df["SMA_20"] - 1
    df["Price_vs_SMA50"] = df["Close"] / df["SMA_50"] - 1
    df["Price_vs_SMA200"] = df["Close"] / df["SMA_200"] - 1

    # Volatility
    df["Volatility_20D"] = df["Daily_Return"].rolling(20).std()
    df["Volatility_60D"] = df["Daily_Return"].rolling(60).std()

    # Volume
    df["Volume_SMA20"] = df["Volume"].rolling(20).mean()
    df["Volume_Ratio"] = df["Volume"] / df["Volume_SMA20"]

    # Trend conditions
    df["Trend_20_50"] = df["SMA_20"] > df["SMA_50"]
    df["Trend_50_200"] = df["SMA_50"] > df["SMA_200"]

    # Remove warm-up period
    df = df.dropna()

    output_path = PROCESSED_DIR / f"{ticker.lower()}_features.csv"

    df.to_csv(output_path)

    print(f"Rows: {len(df):,}")
    print(f"Saved: {output_path}")


TICKERS = [
    "reliance",
    "tcs",
    "infy",
    "hdfcbank",
    "icicibank"
]


print("=" * 60)
print("MULTI-STOCK FEATURE PIPELINE")
print("=" * 60)


for ticker in TICKERS:
    build_features(ticker)


print("\n" + "=" * 60)
print("FEATURE PIPELINE COMPLETE")
print("=" * 60)