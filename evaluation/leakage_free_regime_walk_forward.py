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
    "data/processed/leakage_free_regime_walk_forward.csv"
)


# ============================================================
# LOAD DATA
# ============================================================

trades = pd.read_csv(TRADE_FILE)
regimes = pd.read_csv(REGIME_FILE)


# ============================================================
# VALIDATE COLUMNS
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
# JOIN LEAKAGE-FREE REGIME
# ============================================================

regime_lookup = regimes[
    ["Date", "Market_Regime"]
].copy()

data = trades.merge(
    regime_lookup,
    left_on="Entry_Date",
    right_on="Date",
    how="left",
)


# ============================================================
# VALIDATE JOIN
# ============================================================

missing_regime = data["Market_Regime"].isna().sum()

unknown_regime = (
    data["Market_Regime"] == "UNKNOWN"
).sum()

print("\n" + "=" * 80)
print("LEAKAGE-FREE REGIME × TIME ANALYSIS")
print("=" * 80)

print(
    f"Original trades: {len(data)}"
)

print(
    f"Missing regime: {missing_regime}"
)

print(
    f"UNKNOWN regime: {unknown_regime}"
)


# ============================================================
# REMOVE INVALID REGIMES
# ============================================================

data = data[
    data["Market_Regime"].notna()
    & (data["Market_Regime"] != "UNKNOWN")
].copy()


# ============================================================
# DEFINE CHRONOLOGICAL PERIOD
# ============================================================

def assign_period(date):

    year = date.year

    if 2020 <= year <= 2021:
        return "2020-2021"

    elif 2022 <= year <= 2023:
        return "2022-2023"

    elif 2024 <= year <= 2025:
        return "2024-2025"

    else:
        return "OUTSIDE_TEST"


data["Period"] = data["Entry_Date"].apply(
    assign_period
)


data = data[
    data["Period"] != "OUTSIDE_TEST"
].copy()


# ============================================================
# REGIME × TIME ATTRIBUTION
# ============================================================

summary = (
    data
    .groupby(
        ["Period", "Market_Regime"]
    )
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


# ============================================================
# EVIDENCE QUALITY
# ============================================================

def evidence_quality(n):

    if n < 10:
        return "VERY LOW"

    elif n < 30:
        return "LOW"

    elif n < 50:
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
    ["Period", "Market_Regime"]
)


# ============================================================
# DISPLAY
# ============================================================

display_columns = [
    "Period",
    "Market_Regime",
    "Trades",
    "Winning",
    "Losing",
    "Win_Rate",
    "Total_PnL",
    "Avg_Return",
    "Median_Return",
    "Best_Return",
    "Worst_Return",
    "Evidence",
]

print("\n")

print(
    summary[display_columns].to_string(
        index=False,
        formatters={
            "Win_Rate": lambda x: f"{x:.2%}",
            "Total_PnL": lambda x: f"₹{x:,.2f}",
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
print("LEAKAGE-FREE REGIME × TIME COMPLETE")
print("=" * 80)