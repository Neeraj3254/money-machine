import pandas as pd
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

TRADE_FILE = Path(
    "data/processed/stateful_portfolio_trades_cost_0_0010.csv"
)

REGIME_FILE = Path(
    "data/processed/nifty50_regimes.csv"
)

OUTPUT_FILE = Path(
    "data/processed/portfolio_regime_attribution.csv"
)

# ============================================================
# LOAD DATA
# ============================================================

trades = pd.read_csv(TRADE_FILE)
regimes = pd.read_csv(REGIME_FILE)

# ============================================================
# VALIDATE REQUIRED COLUMNS
# ============================================================

required_trade_columns = [
    "Entry_Date",
    "PnL",
    "Return",
]

required_regime_columns = [
    "Date",
    "Market_Regime",
]

missing_trade = [
    col for col in required_trade_columns
    if col not in trades.columns
]

missing_regime = [
    col for col in required_regime_columns
    if col not in regimes.columns
]

if missing_trade:
    raise ValueError(
        f"Trade file is missing columns: {missing_trade}"
    )

if missing_regime:
    raise ValueError(
        f"Regime file is missing columns: {missing_regime}"
    )

# ============================================================
# NORMALIZE DATES
# ============================================================

trades["Entry_Date"] = pd.to_datetime(
    trades["Entry_Date"]
)

regimes["Date"] = pd.to_datetime(
    regimes["Date"]
)

# ============================================================
# KEEP ONLY DATE + REGIME
# ============================================================

regime_lookup = regimes[
    ["Date", "Market_Regime"]
].copy()

# ============================================================
# JOIN REGIME TO EACH TRADE
# ============================================================

attribution = trades.merge(
    regime_lookup,
    left_on="Entry_Date",
    right_on="Date",
    how="left",
)

# ============================================================
# VALIDATE JOIN
# ============================================================

missing_regime_rows = attribution[
    attribution["Market_Regime"].isna()
]

if len(missing_regime_rows) > 0:

    print(
        f"WARNING: {len(missing_regime_rows)} "
        "trades have no matching market regime."
    )

# ============================================================
# REGIME ATTRIBUTION
# ============================================================

summary = (
    attribution
    .dropna(subset=["Market_Regime"])
    .groupby("Market_Regime")
    .agg(
        Trades=("Return", "count"),
        Winning=("Return", lambda x: (x > 0).sum()),
        Losing=("Return", lambda x: (x <= 0).sum()),
        Total_PnL=("PnL", "sum"),
        Avg_Return=("Return", "mean"),
        Median_Return=("Return", "median"),
        Best_Return=("Return", "max"),
        Worst_Return=("Return", "min"),
    )
    .reset_index()
)

# ============================================================
# DERIVED METRICS
# ============================================================

summary["Win_Rate"] = (
    summary["Winning"] / summary["Trades"]
)

total_pnl = summary["Total_PnL"].sum()

summary["PnL_Contribution"] = (
    summary["Total_PnL"] / total_pnl
)

# ============================================================
# SORT
# ============================================================

summary = summary.sort_values(
    "Total_PnL",
    ascending=False
)

# ============================================================
# DISPLAY
# ============================================================

print("\n" + "=" * 70)
print("PORTFOLIO REGIME ATTRIBUTION")
print("=" * 70)

print(
    f"Completed trades: {len(attribution)}"
)

print(
    f"Matched regime trades: "
    f"{attribution['Market_Regime'].notna().sum()}"
)

print(
    f"Missing regime trades: "
    f"{attribution['Market_Regime'].isna().sum()}"
)

print("\n")

display_columns = [
    "Market_Regime",
    "Trades",
    "Winning",
    "Losing",
    "Win_Rate",
    "Total_PnL",
    "PnL_Contribution",
    "Avg_Return",
    "Median_Return",
    "Best_Return",
    "Worst_Return",
]

print(
    summary[display_columns].to_string(
        index=False,
        formatters={
            "Win_Rate": lambda x: f"{x:.2%}",
            "Total_PnL": lambda x: f"₹{x:,.2f}",
            "PnL_Contribution": lambda x: f"{x:.2%}",
            "Avg_Return": lambda x: f"{x:.2%}",
            "Median_Return": lambda x: f"{x:.2%}",
            "Best_Return": lambda x: f"{x:.2%}",
            "Worst_Return": lambda x: f"{x:.2%}",
        },
    )
)

# ============================================================
# SAVE
# ============================================================

summary.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\nSaved:")
print(OUTPUT_FILE)