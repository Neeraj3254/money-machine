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

N_BOOTSTRAPS = 5000
RANDOM_SEED = 42


def bootstrap_difference(signal_returns, baseline_returns):

    rng = np.random.default_rng(RANDOM_SEED)

    signal_returns = np.asarray(signal_returns)
    baseline_returns = np.asarray(baseline_returns)

    observed_difference = (
        signal_returns.mean()
        - baseline_returns.mean()
    )

    bootstrap_differences = []

    for _ in range(N_BOOTSTRAPS):

        signal_sample = rng.choice(
            signal_returns,
            size=len(signal_returns),
            replace=True
        )

        baseline_sample = rng.choice(
            baseline_returns,
            size=len(baseline_returns),
            replace=True
        )

        difference = (
            signal_sample.mean()
            - baseline_sample.mean()
        )

        bootstrap_differences.append(difference)

    bootstrap_differences = np.array(
        bootstrap_differences
    )

    lower = np.percentile(
        bootstrap_differences,
        2.5
    )

    upper = np.percentile(
        bootstrap_differences,
        97.5
    )

    return (
        observed_difference,
        lower,
        upper
    )


print("=" * 80)
print("STATISTICAL SIGNIFICANCE TEST")
print("=" * 80)

results = []


for ticker in TICKERS:

    print(f"\nTesting {ticker.upper()}...")

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
        df["Close"].shift(-20)
        / df["Close"]
        - 1
    )

    df = df.dropna(
        subset=["Forward_20D_Return"]
    )

    signal_returns = df.loc[
        df["Signal"],
        "Forward_20D_Return"
    ]

    baseline_returns = df[
        "Forward_20D_Return"
    ]

    difference, lower, upper = bootstrap_difference(
        signal_returns,
        baseline_returns
    )

    results.append({
        "Stock": ticker.upper(),
        "Signal_Observations": len(signal_returns),
        "Observed_Difference": difference,
        "CI_Lower": lower,
        "CI_Upper": upper,
        "CI_Contains_Zero": (
            lower <= 0 <= upper
        )
    })


results_df = pd.DataFrame(results)


print("\n")
print("=" * 80)
print("BOOTSTRAP RESULTS")
print("=" * 80)

display_df = results_df.copy()

for column in [
    "Observed_Difference",
    "CI_Lower",
    "CI_Upper"
]:

    display_df[column] *= 100


print(
    display_df.round(3).to_string(
        index=False
    )
)


output_path = (
    DATA_DIR /
    "statistical_test.csv"
)

results_df.to_csv(
    output_path,
    index=False
)


print("\nSaved to:")
print(output_path)

print("\n" + "=" * 80)
print("STATISTICAL TEST COMPLETE")
print("=" * 80)