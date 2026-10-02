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


all_results = []


for ticker in TICKERS:

    stock_path = (
        DATA_DIR /
        f"{ticker}_features.csv"
    )

    stock = pd.read_csv(
        stock_path,
        index_col=0,
        parse_dates=True
    )

    market = pd.read_csv(
        DATA_DIR /
        "nifty50_regimes.csv",
        index_col=0,
        parse_dates=True
    )

    # ------------------------------------------------
    # FROZEN SIGNAL
    # ------------------------------------------------

    stock["Signal"] = (
        (stock["Return_20D"] > 0)
        & (stock["SMA_20"] > stock["SMA_50"])
        & (stock["Close"] > stock["SMA_200"])
    )

    # ------------------------------------------------
    # FORWARD RETURN
    # ------------------------------------------------

    stock["Forward_20D_Return"] = (
        stock["Close"].shift(-20)
        / stock["Close"]
        - 1
    )

    # ------------------------------------------------
    # ALIGN STOCK + MARKET
    # ------------------------------------------------

    combined = stock.join(
        market[["Market_Regime"]],
        how="inner"
    )

    combined = combined.dropna(
        subset=["Forward_20D_Return"]
    )

    signal_data = combined[
        combined["Signal"]
    ]

    # ------------------------------------------------
    # REGIME RESULTS
    # ------------------------------------------------

    for regime, group in signal_data.groupby(
        "Market_Regime"
    ):

        returns = group[
            "Forward_20D_Return"
        ]

        all_results.append({
            "Stock": ticker.upper(),
            "Market_Regime": regime,
            "Observations": len(returns),
            "Average_Return": returns.mean(),
            "Median_Return": returns.median(),
            "Positive_Rate": (
                returns > 0
            ).mean()
        })


results_df = pd.DataFrame(
    all_results
)


print("=" * 90)
print("STRATEGY PERFORMANCE BY MARKET REGIME")
print("=" * 90)


display_df = results_df.copy()

for column in [
    "Average_Return",
    "Median_Return",
    "Positive_Rate"
]:

    display_df[column] *= 100


print(
    display_df.round(2)
    .to_string(index=False)
)


output_path = (
    DATA_DIR /
    "strategy_market_regime.csv"
)

results_df.to_csv(
    output_path,
    index=False
)


print("\nSaved to:")
print(output_path)

print("\n" + "=" * 90)
print("STRATEGY MARKET REGIME ANALYSIS COMPLETE")
print("=" * 90)