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

    # Non-overlapping observations
    sampled = df.iloc[::HOLDING_PERIOD].copy()

    trades = sampled[
        sampled["Signal"]
    ]["Forward_20D_Return"]

    if len(trades) == 0:
        return None

    winners = trades[trades > 0]
    losers = trades[trades < 0]

    win_rate = (
        len(winners) / len(trades)
    )

    loss_rate = (
        len(losers) / len(trades)
    )

    average_win = (
        winners.mean()
        if len(winners) > 0
        else 0
    )

    average_loss = (
        abs(losers.mean())
        if len(losers) > 0
        else 0
    )

    expectancy = (
        win_rate * average_win
        - loss_rate * average_loss
    )

    gross_profit = winners.sum()
    gross_loss = abs(losers.sum())

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else np.inf
    )

    return {
        "Stock": ticker.upper(),
        "Trades": len(trades),
        "Win_Rate": win_rate,
        "Loss_Rate": loss_rate,
        "Average_Win": average_win,
        "Average_Loss": average_loss,
        "Expectancy": expectancy,
        "Profit_Factor": profit_factor,
        "Best_Trade": trades.max(),
        "Worst_Trade": trades.min()
    }


print("=" * 80)
print("TRADE EXPECTANCY ANALYSIS")
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
    "Win_Rate",
    "Loss_Rate",
    "Average_Win",
    "Average_Loss",
    "Expectancy",
    "Best_Trade",
    "Worst_Trade"
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
    "expectancy_analysis.csv"
)

results_df.to_csv(
    output_path,
    index=False
)


print("\nSaved to:")
print(output_path)

print("\n" + "=" * 80)
print("EXPECTANCY ANALYSIS COMPLETE")
print("=" * 80)