from pathlib import Path

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)

COST = 0.001

COST_TAG = (
    f"{COST:.4f}"
    .replace(".", "_")
)

INPUT_FILE = (
    PROCESSED_DIR
    / (
        "stateful_portfolio_trades_"
        f"cost_{COST_TAG}.csv"
    )
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / (
        "portfolio_time_attribution_"
        f"cost_{COST_TAG}.csv"
    )
)


# ============================================================
# LOAD TRADE LEDGER
# ============================================================

if not INPUT_FILE.exists():

    raise FileNotFoundError(
        f"Trade ledger not found:\n{INPUT_FILE}"
    )


trades = pd.read_csv(
    INPUT_FILE,
    parse_dates=[
        "Signal_Date",
        "Entry_Date",
        "Exit_Date",
    ],
)


# ============================================================
# VALIDATE REQUIRED COLUMNS
# ============================================================

required_columns = {
    "Stock",
    "Entry_Date",
    "Exit_Date",
    "Return",
    "PnL",
    "Capital",
}

missing_columns = (
    required_columns
    - set(trades.columns)
)

if missing_columns:

    raise ValueError(
        "Missing required columns: "
        f"{sorted(missing_columns)}"
    )


if trades.empty:

    raise ValueError(
        "Trade ledger is empty."
    )


# ============================================================
# BASIC VALIDATION
# ============================================================

if (trades["Capital"] <= 0).any():

    raise ValueError(
        "Non-positive trade capital detected."
    )


# ============================================================
# CREATE TIME PERIOD
# ============================================================
#
# We use ENTRY YEAR because the trade's capital
# was actually deployed during that year.
#
# Example:
#
# Entry_Date = 2024-03-15
# Period     = 2024
#
# ============================================================

trades["Year"] = (
    trades["Entry_Date"]
    .dt.year
)


# ============================================================
# GROUP BY YEAR
# ============================================================

time_summary = (
    trades
    .groupby("Year")
    .agg(
        Trades=(
            "Stock",
            "size",
        ),

        Total_Capital_Deployed=(
            "Capital",
            "sum",
        ),

        Total_PnL=(
            "PnL",
            "sum",
        ),

        Average_Trade_Return=(
            "Return",
            "mean",
        ),

        Median_Trade_Return=(
            "Return",
            "median",
        ),

        Best_Trade=(
            "Return",
            "max",
        ),

        Worst_Trade=(
            "Return",
            "min",
        ),
    )
    .reset_index()
)


# ============================================================
# WIN / LOSS COUNTS
# ============================================================

win_counts = (
    trades
    .assign(
        Win=trades["Return"] > 0
    )
    .groupby("Year")["Win"]
    .agg(
        Winning_Trades="sum",
        Total_Trades="count",
    )
    .reset_index()
)


time_summary = time_summary.merge(
    win_counts,
    on="Year",
    how="left",
)


# ============================================================
# LOSING TRADES
# ============================================================

time_summary["Losing_Trades"] = (
    time_summary["Total_Trades"]
    - time_summary["Winning_Trades"]
)


# ============================================================
# WIN RATE
# ============================================================

time_summary["Win_Rate"] = (
    time_summary["Winning_Trades"]
    / time_summary["Total_Trades"]
)


# ============================================================
# TOTAL PORTFOLIO TRADE P&L
# ============================================================

portfolio_total_pnl = (
    time_summary["Total_PnL"]
    .sum()
)


# ============================================================
# CONTRIBUTION TO TOTAL TRADE P&L
# ============================================================

if portfolio_total_pnl != 0:

    time_summary[
        "PnL_Contribution"
    ] = (
        time_summary["Total_PnL"]
        / portfolio_total_pnl
    )

else:

    time_summary[
        "PnL_Contribution"
    ] = 0.0


# ============================================================
# POSITIVE / NEGATIVE PERIOD
# ============================================================

time_summary["Period_Direction"] = (
    time_summary["Total_PnL"]
    .apply(
        lambda x:
            "Positive"
            if x > 0
            else (
                "Negative"
                if x < 0
                else "Flat"
            )
    )
)


# ============================================================
# SORT CHRONOLOGICALLY
# ============================================================

time_summary = (
    time_summary
    .sort_values("Year")
    .reset_index(drop=True)
)


# ============================================================
# SAVE
# ============================================================

time_summary.to_csv(
    OUTPUT_FILE,
    index=False,
)


# ============================================================
# DISPLAY
# ============================================================

print()
print("=" * 105)
print(
    "PORTFOLIO TIME-PERIOD ATTRIBUTION"
)
print("=" * 105)

print()

print(
    f"Transaction cost/side: "
    f"{COST:.2%}"
)

print(
    f"Completed trades: "
    f"{len(trades)}"
)

print(
    f"Total trade P&L: "
    f"₹{portfolio_total_pnl:,.2f}"
)

print()


display_columns = [
    "Year",
    "Trades",
    "Winning_Trades",
    "Losing_Trades",
    "Win_Rate",
    "Total_PnL",
    "PnL_Contribution",
    "Average_Trade_Return",
    "Median_Trade_Return",
    "Best_Trade",
    "Worst_Trade",
    "Period_Direction",
]


display_df = time_summary[
    display_columns
].copy()


# ============================================================
# FORMAT OUTPUT
# ============================================================

display_df["Win_Rate"] = (
    display_df["Win_Rate"]
    .map(
        lambda x: f"{x:.2%}"
    )
)


display_df["Total_PnL"] = (
    display_df["Total_PnL"]
    .map(
        lambda x: f"₹{x:,.2f}"
    )
)


display_df["PnL_Contribution"] = (
    display_df["PnL_Contribution"]
    .map(
        lambda x: f"{x:.2%}"
    )
)


for column in [
    "Average_Trade_Return",
    "Median_Trade_Return",
    "Best_Trade",
    "Worst_Trade",
]:

    display_df[column] = (
        display_df[column]
        .map(
            lambda x: f"{x:.2%}"
        )
    )


print(
    display_df.to_string(
        index=False
    )
)


# ============================================================
# VALIDATION
# ============================================================

assert (
    abs(
        time_summary["Total_PnL"].sum()
        - portfolio_total_pnl
    )
    < 1e-6
)


assert (
    time_summary["Trades"].sum()
    == len(trades)
)


print()

print(
    "Validation: yearly P&L sums "
    "to portfolio trade P&L."
)

print(
    "Validation: yearly trade counts "
    "sum to total completed trades."
)

print()

print(
    f"Results saved to:\n{OUTPUT_FILE}"
)

print("=" * 105)