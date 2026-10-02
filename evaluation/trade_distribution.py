import pandas as pd
import numpy as np
from pathlib import Path


DATA_DIR = Path("data/processed")

TICKERS = [
    "reliance",
    "tcs",
    "infy",
    "hdfcbank",
    "icicibank"
]

HOLDING_PERIOD = 20


def analyze_stock(ticker):

    path = DATA_DIR / f"{ticker}_features.csv"

    df = pd.read_csv(
        path,
        index_col=0,
        parse_dates=True
    )

    # Frozen strategy
    df["Signal"] = (
        (df["Return_20D"] > 0)
        & (df["SMA_20"] > df["SMA_50"])
        & (df["Close"] > df["SMA_200"])
    )

    # Forward return
    df["Forward_20D_Return"] = (
        df["Close"].shift(-HOLDING_PERIOD)
        / df["Close"]
        - 1
    )

    df = df.dropna(
        subset=["Forward_20D_Return"]
    )

    # Same non-overlapping sampling
    sampled = df.iloc[::HOLDING_PERIOD].copy()

    signal = sampled[
        sampled["Signal"]
    ]["Forward_20D_Return"]

    if len(signal) == 0:
        return None

    return {
        "Stock": ticker.upper(),
        "N": len(signal),
        "Mean": signal.mean(),
        "Median": signal.median(),
        "Std": signal.std(),
        "Min": signal.min(),
        "Max": signal.max(),
        "Positive_Rate": (signal > 0).mean(),
        "25th_Percentile": signal.quantile(0.25),
        "75th_Percentile": signal.quantile(0.75)
    }


print("=" * 80)
print("SIGNAL RETURN DISTRIBUTION")
print("=" * 80)


results = []

for ticker in TICKERS:

    print(f"\nAnalyzing {ticker.upper()}...")

    result = analyze_stock(ticker)

    if result:
        results.append(result)


results_df = pd.DataFrame(results)


display_df = results_df.copy()

percentage_columns = [
    "Mean",
    "Median",
    "Std",
    "Min",
    "Max",
    "Positive_Rate",
    "25th_Percentile",
    "75th_Percentile"
]

for column in percentage_columns:
    display_df[column] *= 100


print("\n")
print("=" * 80)
print("RESULTS")
print("=" * 80)

print(
    display_df.round(2).to_string(
        index=False
    )
)


output_path = (
    DATA_DIR /
    "trade_distribution.csv"
)

results_df.to_csv(
    output_path,
    index=False
)


print("\nSaved to:")
print(output_path)

print("\n" + "=" * 80)
print("DISTRIBUTION ANALYSIS COMPLETE")
print("=" * 80)