import pandas as pd
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

TRADE_FILE = Path(
    "data/processed/stateful_portfolio_trades_cost_0_0010.csv"
)

REGIME_FILE = Path(
    "data/processed/nifty50_regimes_leakage_free.csv"
)

OUTPUT_FILE = Path(
    "data/processed/leakage_free_portfolio_attribution.csv"
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
    "Return",
    "PnL",
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
# PREPARE REGIME LOOKUP
# ============================================================

regime_lookup = regimes[
    [
        "Date",
        "Market_Regime",
        "Vol_Low_Threshold",
        "Vol_High_Threshold",
        "Historical_Vol_Observations",
    ]
].copy()


# ============================================================
# JOIN REGIME TO PORTFOLIO TRADES
# ============================================================

data = trades.merge(
    regime_lookup,
    left_on="Entry_Date",
    right_on="Date",
    how="left",
)


# ============================================================
# VALIDATE JOIN
# ============================================================

missing_regimes = data["Market_Regime"].isna().sum()

if missing_regimes > 0:

    print(
        f"WARNING: {missing_regimes} trades "
        "have no leakage-free regime."
    )


# ============================================================
# REMOVE UNKNOWN REGIMES
# ============================================================

unknown_count = (
    data["Market_Regime"] == "UNKNOWN"
).sum()

if unknown_count > 0:

    print(
        f"WARNING: {unknown_count} trades "
        "occurred before the regime engine became valid."
    )


analysis_data = data[
    data["Market_Regime"].notna()
    & (data["Market_Regime"] != "UNKNOWN")
].copy()


# ============================================================
# REGIME ATTRIBUTION
# ============================================================

summary = (
    analysis_data
    .groupby("Market_Regime")
    .agg(
        Trades=("Return", "count"),

        Winning=(
            "Return",
            lambda x: (x > 0).sum()
        ),

        Losing=(
            "Return",
            lambda x: (x <= 0).sum()
        ),

        Total_PnL=(
            "PnL",
            "sum"
        ),

        Avg_Return=(
            "Return",
            "mean"
        ),

        Median_Return=(
            "Return",
            "median"
        ),

        Best_Return=(
            "Return",
            "max"
        ),

        Worst_Return=(
            "Return",
            "min"
        ),
    )
    .reset_index()
)


# ============================================================
# DERIVED METRICS
# ============================================================

summary["Win_Rate"] = (
    summary["Winning"]
    / summary["Trades"]
)


total_pnl = summary["Total_PnL"].sum()

summary["PnL_Contribution"] = (
    summary["Total_PnL"]
    / total_pnl
)


# ============================================================
# EVIDENCE QUALITY
# ============================================================

def evidence_quality(trades):

    if trades < 10:
        return "VERY LOW"

    elif trades < 30:
        return "LOW"

    elif trades < 50:
        return "PRELIMINARY"

    else:
        return "REASONABLE"


summary["Evidence"] = (
    summary["Trades"]
    .apply(evidence_quality)
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

print("\n" + "=" * 80)
print("LEAKAGE-FREE PORTFOLIO REGIME ATTRIBUTION")
print("=" * 80)

print(
    f"Original portfolio trades: {len(trades)}"
)

print(
    f"Trades with matched regime: "
    f"{data['Market_Regime'].notna().sum()}"
)

print(
    f"Unknown regime trades: {unknown_count}"
)

print(
    f"Trades included in analysis: "
    f"{len(analysis_data)}"
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
    "Evidence",
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

print("\n" + "=" * 80)
print("LEAKAGE-FREE ATTRIBUTION COMPLETE")
print("=" * 80)