import pandas as pd
import numpy as np
from pathlib import Path


RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def build_features(ticker):

    input_path = RAW_DIR / f"{ticker.lower()}_daily.csv"

    print(f"\nProcessing {ticker}...")
    print("-" * 40)

    df = pd.read_csv(
        input_path,
        index_col=0,
        parse_dates=True
    )

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