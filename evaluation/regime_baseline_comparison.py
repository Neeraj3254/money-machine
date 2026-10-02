import pandas as pd
from pathlib import Path


DATA_DIR = Path("data/processed")

TICKERS = [
    "reliance",
    "tcs",
    "infy",
    "hdfcbank",
    "icicibank"
]


results = []


for ticker in TICKERS:

    stock = pd.read_csv(
        DATA_DIR / f"{ticker}_features.csv",
        index_col=0,
        parse_dates=True
    )

    market = pd.read_csv(
        DATA_DIR / "nifty50_regimes.csv",
        index_col=0,
        parse_dates=True
    )

    stock["Signal"] = (
        (stock["Return_20D"] > 0)
        & (stock["SMA_20"] > stock["SMA_50"])
        & (stock["Close"] > stock["SMA_200"])
    )

    stock["Forward_20D_Return"] = (
        stock["Close"].shift(-20)
        / stock["Close"]
        - 1
    )

    df = stock.join(
        market[["Market_Regime"]],
        how="inner"
    )

    df = df.dropna(
        subset=["Forward_20D_Return"]
    )

    for regime, group in df.groupby(
        "Market_Regime"
    ):

        signal_returns = group.loc[
            group["Signal"],
            "Forward_20D_Return"
        ]

        baseline_returns = group[
            "Forward_20D_Return"
        ]

        if len(signal_returns) == 0:
            continue

        signal_mean = signal_returns.mean()
        baseline_mean = baseline_returns.mean()

        results.append({
            "Stock": ticker.upper(),
            "Market_Regime": regime,
            "Signal_Observations": len(signal_returns),
            "Baseline_Observations": len(baseline_returns),
            "Signal_Return": signal_mean,
            "Baseline_Return": baseline_mean,
            "Difference": (
                signal_mean - baseline_mean
            )
        })


results_df = pd.DataFrame(results)


print("=" * 90)
print("REGIME-ADJUSTED BASELINE COMPARISON")
print("=" * 90)


display_df = results_df.copy()

for column in [
    "Signal_Return",
    "Baseline_Return",
    "Difference"
]:

    display_df[column] *= 100


print(
    display_df.round(2)
    .to_string(index=False)
)


output_path = (
    DATA_DIR /
    "regime_baseline_comparison.csv"
)

results_df.to_csv(
    output_path,
    index=False
)

print(f"\nSaved to: {output_path}")

print("\n" + "=" * 90)
print("REGIME BASELINE COMPARISON COMPLETE")
print("=" * 90)