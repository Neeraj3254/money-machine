import pandas as pd
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

STOCKS = {
    "RELIANCE": "reliance_features.csv",
    "TCS": "tcs_features.csv",
    "INFY": "infy_features.csv",
    "HDFCBANK": "hdfcbank_features.csv",
    "ICICIBANK": "icicibank_features.csv",
}

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "portfolio_signals.csv"
)


# ============================================================
# BUILD SIGNAL DATASET
# ============================================================

frames = []

for stock, filename in STOCKS.items():

    path = (
        BASE_DIR
        / "data"
        / "processed"
        / filename
    )

    df = pd.read_csv(path, parse_dates=["Date"])

    # V1 signal: frozen baseline
    df["Signal"] = (
        (df["Return_20D"] > 0)
        & (df["SMA_20"] > df["SMA_50"])
        & (df["Close"] > df["SMA_200"])
    )

    df["Stock"] = stock

    frames.append(
        df[
            [
                "Date",
                "Stock",
                "Open",
                "Close",
                "Signal",
                "Return_20D",
                "SMA_20",
                "SMA_50",
                "SMA_200",
                "Volatility_20D",
            ]
        ]
    )


portfolio = pd.concat(
    frames,
    ignore_index=True
)

portfolio = portfolio.sort_values(
    ["Date", "Stock"]
).reset_index(drop=True)


# ============================================================
# SAVE
# ============================================================

portfolio.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("=" * 70)
print("PORTFOLIO SIGNAL DATASET")
print("=" * 70)

print(f"Rows: {len(portfolio):,}")
print(f"Stocks: {portfolio['Stock'].nunique()}")
print(
    f"Date range: "
    f"{portfolio['Date'].min().date()} → "
    f"{portfolio['Date'].max().date()}"
)

print()

print("Signals by stock:")

print(
    portfolio.groupby("Stock")["Signal"]
    .agg(
        Observations="size",
        Signals="sum",
        Signal_Frequency="mean",
    )
    .to_string()
)

print()

print(f"Saved: {OUTPUT_FILE}")