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
    "data/processed/regime_effect_by_period.csv"
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
# REMOVE INVALID REGIMES
# ============================================================

data = data[
    data["Market_Regime"].notna()
    & (data["Market_Regime"] != "UNKNOWN")
].copy()


# ============================================================
# DEFINE TIME PERIOD
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
# CALCULATE REGIME EFFECT
# ============================================================

results = []

for period in sorted(data["Period"].unique()):

    period_data = data[
        data["Period"] == period
    ].copy()

    period_baseline = (
        period_data["Return"].mean()
    )

    for regime in sorted(
        period_data["Market_Regime"].unique()
    ):

        regime_data = period_data[
            period_data["Market_Regime"] == regime
        ]

        other_data = period_data[
            period_data["Market_Regime"] != regime
        ]

        regime_trades = len(regime_data)
        other_trades = len(other_data)

        regime_avg = (
            regime_data["Return"].mean()
        )

        other_avg = (
            other_data["Return"].mean()
            if other_trades > 0
            else float("nan")
        )

        effect = (
            regime_avg - other_avg
            if other_trades > 0
            else float("nan")
        )

        total_pnl = (
            regime_data["PnL"].sum()
        )

        win_rate = (
            (regime_data["Return"] > 0).mean()
        )

        # ----------------------------------------------------
        # Evidence classification
        # ----------------------------------------------------

        if regime_trades < 10:
            evidence = "VERY LOW"

        elif regime_trades < 30:
            evidence = "LOW"

        elif regime_trades < 50:
            evidence = "PRELIMINARY"

        else:
            evidence = "REASONABLE"

        results.append(
            {
                "Period": period,
                "Market_Regime": regime,
                "Trades": regime_trades,
                "Other_Trades": other_trades,
                "Win_Rate": win_rate,
                "Regime_Avg_Return": regime_avg,
                "Other_Avg_Return": other_avg,
                "Regime_Effect": effect,
                "Total_PnL": total_pnl,
                "Evidence": evidence,
            }
        )


# ============================================================
# CREATE RESULT DATAFRAME
# ============================================================

summary = pd.DataFrame(results)


# ============================================================
# DISPLAY
# ============================================================

print("\n" + "=" * 100)
print("LEAKAGE-FREE REGIME EFFECT BY PERIOD")
print("=" * 100)

print(
    "\nDefinition:"
)

print(
    "Regime Effect = Regime Average Return "
    "- Same-Period Other-Regime Average Return"
)

print("\n")

print(
    summary.to_string(
        index=False,
        formatters={
            "Win_Rate": lambda x: f"{x:.2%}",
            "Regime_Avg_Return": lambda x: f"{x:.2%}",
            "Other_Avg_Return": lambda x: f"{x:.2%}",
            "Regime_Effect": lambda x: f"{x:.2%}",
            "Total_PnL": lambda x: f"₹{x:,.2f}",
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

print("\n" + "=" * 100)
print("REGIME EFFECT ANALYSIS COMPLETE")
print("=" * 100)