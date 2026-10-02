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


def evaluate_period(df, start, end):

    period = df.loc[
        (df.index >= start)
        & (df.index <= end)
    ].copy()

    period["Signal"] = (
        (period["Return_20D"] > 0)
        & (period["SMA_20"] > period["SMA_50"])
        & (period["Close"] > period["SMA_200"])
    )

    period["Forward_20D_Return"] = (
        period["Close"].shift(-20)
        / period["Close"]
        - 1
    )

    period = period.dropna(
        subset=["Forward_20D_Return"]
    )

    trades = period.loc[
        period["Signal"],
        "Forward_20D_Return"
    ]

    if len(trades) == 0:
        return None

    return {
        "Trades": len(trades),
        "Mean_Return": trades.mean(),
        "Median_Return": trades.median(),
        "Win_Rate": (trades > 0).mean()
    }


periods = [
    ("2019-10-01", "2021-12-31"),
    ("2022-01-01", "2023-12-31"),
    ("2024-01-01", "2025-12-31")
]


results = []

print("=" * 80)
print("CHRONOLOGICAL WALK-FORWARD DIAGNOSTIC")
print("=" * 80)


for ticker in TICKERS:

    path = DATA_DIR / f"{ticker}_features.csv"

    df = pd.read_csv(
        path,
        index_col=0,
        parse_dates=True
    )

    for start, end in periods:

        result = evaluate_period(
            df,
            start,
            end
        )

        if result:

            results.append({
                "Stock": ticker.upper(),
                "Period": f"{start} to {end}",
                **result
            })


results_df = pd.DataFrame(results)

display_df = results_df.copy()

for column in [
    "Mean_Return",
    "Median_Return",
    "Win_Rate"
]:
    display_df[column] *= 100

print(
    display_df.round(2).to_string(
        index=False
    )
)

output_path = (
    DATA_DIR /
    "walk_forward.csv"
)

results_df.to_csv(
    output_path,
    index=False
)

print(f"\nSaved to: {output_path}")

print("\n" + "=" * 80)
print("WALK-FORWARD DIAGNOSTIC COMPLETE")
print("=" * 80)