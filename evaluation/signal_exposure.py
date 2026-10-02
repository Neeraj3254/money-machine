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

    df = stock.join(
        market[["Market_Regime"]],
        how="inner"
    )

    for regime, group in df.groupby(
        "Market_Regime"
    ):

        total_days = len(group)
        signal_days = group["Signal"].sum()

        results.append({
            "Stock": ticker.upper(),
            "Market_Regime": regime,
            "Total_Days": total_days,
            "Signal_Days": signal_days,
            "Signal_Frequency": (
                signal_days / total_days
            )
        })


results_df = pd.DataFrame(results)


print("=" * 90)
print("SIGNAL EXPOSURE BY MARKET REGIME")
print("=" * 90)


display_df = results_df.copy()

display_df["Signal_Frequency"] *= 100


print(
    display_df.round(2)
    .to_string(index=False)
)


output_path = (
    DATA_DIR /
    "signal_exposure.csv"
)

results_df.to_csv(
    output_path,
    index=False
)

print(f"\nSaved to: {output_path}")

print("\n" + "=" * 90)
print("SIGNAL EXPOSURE COMPLETE")
print("=" * 90)