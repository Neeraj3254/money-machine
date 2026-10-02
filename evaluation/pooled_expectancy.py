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


all_trades = []


for ticker in TICKERS:

    path = DATA_DIR / f"{ticker}_features.csv"

    df = pd.read_csv(
        path,
        index_col=0,
        parse_dates=True
    )

    df["Signal"] = (
        (df["Return_20D"] > 0)
        & (df["SMA_20"] > df["SMA_50"])
        & (df["Close"] > df["SMA_200"])
    )

    df["Forward_20D_Return"] = (
        df["Close"].shift(-HOLDING_PERIOD)
        / df["Close"]
        - 1
    )

    df = df.dropna(
        subset=["Forward_20D_Return"]
    )

    sampled = df.iloc[::HOLDING_PERIOD].copy()

    trades = sampled.loc[
        sampled["Signal"],
        "Forward_20D_Return"
    ]

    for value in trades:
        all_trades.append({
            "Stock": ticker.upper(),
            "Return": value
        })


trades_df = pd.DataFrame(all_trades)

winners = trades_df[
    trades_df["Return"] > 0
]["Return"]

losers = trades_df[
    trades_df["Return"] < 0
]["Return"]


win_rate = len(winners) / len(trades_df)
loss_rate = len(losers) / len(trades_df)

average_win = winners.mean()
average_loss = abs(losers.mean())

expectancy = (
    win_rate * average_win
    - loss_rate * average_loss
)

profit_factor = (
    winners.sum()
    / abs(losers.sum())
)


print("=" * 70)
print("POOLED EXPECTANCY")
print("=" * 70)

print(f"Total signal periods: {len(trades_df)}")
print(f"Winners: {len(winners)}")
print(f"Losers: {len(losers)}")
print(f"Win rate: {win_rate:.2%}")
print(f"Average win: {average_win:.2%}")
print(f"Average loss: {average_loss:.2%}")
print(f"Expectancy: {expectancy:.2%}")
print(f"Profit factor: {profit_factor:.2f}")

print("\nBy stock:")
print(
    trades_df.groupby("Stock")["Return"]
    .agg(["count", "mean", "median"])
    .round(4)
)

output_path = DATA_DIR / "pooled_expectancy.csv"
trades_df.to_csv(output_path, index=False)

print(f"\nSaved to: {output_path}")
print("\n" + "=" * 70)
print("POOLED EXPECTANCY COMPLETE")
print("=" * 70)