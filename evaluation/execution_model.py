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


def evaluate_stock(ticker):

    path = DATA_DIR / f"{ticker}_features.csv"

    df = pd.read_csv(
        path,
        index_col=0,
        parse_dates=True
    )

    # Signal is known at today's close
    df["Signal"] = (
        (df["Return_20D"] > 0)
        & (df["SMA_20"] > df["SMA_50"])
        & (df["Close"] > df["SMA_200"])
    )

    # Enter at NEXT day's open
    df["Entry_Price"] = df["Open"].shift(-1)

    # Exit 20 trading days after entry
    df["Exit_Price"] = df["Open"].shift(-21)

    df["Trade_Return"] = (
        df["Exit_Price"]
        / df["Entry_Price"]
        - 1
    )

    df = df.dropna(
        subset=[
            "Entry_Price",
            "Exit_Price",
            "Trade_Return"
        ]
    )

    trades = df.loc[
        df["Signal"],
        "Trade_Return"
    ]

    return {
        "Stock": ticker.upper(),
        "Trades": len(trades),
        "Average_Return": trades.mean(),
        "Median_Return": trades.median(),
        "Win_Rate": (trades > 0).mean(),
        "Best": trades.max(),
        "Worst": trades.min()
    }


results = []

print("=" * 70)
print("NEXT-OPEN EXECUTION MODEL")
print("=" * 70)

for ticker in TICKERS:

    result = evaluate_stock(ticker)
    results.append(result)

results_df = pd.DataFrame(results)

display_df = results_df.copy()

for column in [
    "Average_Return",
    "Median_Return",
    "Win_Rate",
    "Best",
    "Worst"
]:
    display_df[column] *= 100

print(
    display_df.round(2).to_string(
        index=False
    )
)

output_path = (
    DATA_DIR /
    "execution_model.csv"
)

results_df.to_csv(
    output_path,
    index=False
)

print(f"\nSaved to: {output_path}")

print("\n" + "=" * 70)
print("EXECUTION MODEL COMPLETE")
print("=" * 70)