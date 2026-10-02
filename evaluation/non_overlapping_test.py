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


def evaluate_stock(ticker):

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

    # Forward 20-day return
    df["Forward_20D_Return"] = (
        df["Close"].shift(-HOLDING_PERIOD)
        / df["Close"]
        - 1
    )

    df = df.dropna(
        subset=["Forward_20D_Return"]
    )

    # Select every 20th observation.
    # This creates non-overlapping evaluation windows.
    sampled = df.iloc[::HOLDING_PERIOD].copy()

    signal = sampled[
        sampled["Signal"]
    ]

    signal_return = (
        signal["Forward_20D_Return"].mean()
    )

    baseline_return = (
        sampled["Forward_20D_Return"].mean()
    )

    difference = (
        signal_return
        - baseline_return
    )

    return {
        "Stock": ticker.upper(),
        "Evaluation_Periods": len(sampled),
        "Signal_Periods": len(signal),
        "Signal_Avg_Return": signal_return,
        "Baseline_Avg_Return": baseline_return,
        "Return_Difference": difference
    }


print("=" * 80)
print("NON-OVERLAPPING 20-DAY TEST")
print("=" * 80)


results = []

for ticker in TICKERS:

    print(f"\nTesting {ticker.upper()}...")

    results.append(
        evaluate_stock(ticker)
    )


results_df = pd.DataFrame(results)


print("\n")
print("=" * 80)
print("RESULTS")
print("=" * 80)


display_df = results_df.copy()

for column in [
    "Signal_Avg_Return",
    "Baseline_Avg_Return",
    "Return_Difference"
]:
    display_df[column] *= 100


print(
    display_df.round(3).to_string(
        index=False
    )
)


output_path = (
    DATA_DIR /
    "non_overlapping_test.csv"
)

results_df.to_csv(
    output_path,
    index=False
)


print("\nSaved to:")
print(output_path)

print("\n" + "=" * 80)
print("NON-OVERLAPPING TEST COMPLETE")
print("=" * 80)