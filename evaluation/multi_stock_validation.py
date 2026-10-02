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


def evaluate_stock(ticker):

    path = DATA_DIR / f"{ticker}_features.csv"

    df = pd.read_csv(
        path,
        index_col=0,
        parse_dates=True
    )

    # --------------------------------------------------
    # FROZEN STRATEGY
    # --------------------------------------------------

    df["Signal"] = (
        (df["Return_20D"] > 0)
        & (df["SMA_20"] > df["SMA_50"])
        & (df["Close"] > df["SMA_200"])
    )

    # Forward 20-day return
    df["Forward_20D_Return"] = (
        df["Close"].shift(-20) / df["Close"] - 1
    )

    # Remove rows where future return is unavailable
    df = df.dropna(subset=["Forward_20D_Return"])

    signal = df[df["Signal"]]

    signal_return = signal["Forward_20D_Return"].mean()
    signal_positive_rate = (
        signal["Forward_20D_Return"] > 0
    ).mean()

    baseline_return = df["Forward_20D_Return"].mean()

    baseline_positive_rate = (
        df["Forward_20D_Return"] > 0
    ).mean()

    return {
        "Stock": ticker.upper(),
        "Observations": len(df),
        "Signal_Observations": len(signal),
        "Signal_Frequency": len(signal) / len(df),
        "Signal_Avg_20D_Return": signal_return,
        "Baseline_Avg_20D_Return": baseline_return,
        "Return_Difference": signal_return - baseline_return,
        "Signal_Positive_Rate": signal_positive_rate,
        "Baseline_Positive_Rate": baseline_positive_rate,
        "Positive_Rate_Difference": (
            signal_positive_rate - baseline_positive_rate
        )
    }


print("=" * 80)
print("MULTI-STOCK STRATEGY VALIDATION")
print("=" * 80)

results = []

for ticker in TICKERS:

    print(f"\nEvaluating {ticker.upper()}...")

    result = evaluate_stock(ticker)

    results.append(result)


results_df = pd.DataFrame(results)

print("\n")
print("=" * 80)
print("RESULTS")
print("=" * 80)

display_df = results_df.copy()

for column in [
    "Signal_Frequency",
    "Signal_Avg_20D_Return",
    "Baseline_Avg_20D_Return",
    "Return_Difference",
    "Signal_Positive_Rate",
    "Baseline_Positive_Rate",
    "Positive_Rate_Difference"
]:

    display_df[column] = display_df[column] * 100


print(display_df.round(2).to_string(index=False))


output_path = DATA_DIR / "multi_stock_validation.csv"

results_df.to_csv(output_path, index=False)

print("\nSaved to:")
print(output_path)

print("\n" + "=" * 80)
print("VALIDATION COMPLETE")
print("=" * 80)