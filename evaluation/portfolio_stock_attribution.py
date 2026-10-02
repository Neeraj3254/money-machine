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
        "portfolio_stock_attribution_"
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
    "Capital",
    "Return",
    "PnL",
    "Entry_Date",
    "Exit_Date",
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


# ============================================================
# BASIC VALIDATION
# ============================================================

if trades.empty:

    raise ValueError(
        "Trade ledger is empty."
    )


if (trades["Capital"] <= 0).any():

    raise ValueError(
        "Invalid non-positive trade capital found."
    )


# ============================================================
# STOCK-LEVEL GROUPING
# ============================================================

stock_summary = (
    trades
    .groupby("Stock")
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
    .groupby("Stock")["Win"]
    .agg(
        Winning_Trades="sum",
        Total_Trades="count",
    )
    .reset_index()
)


stock_summary = stock_summary.merge(
    win_counts,
    on="Stock",
    how="left",
)


# ============================================================
# WIN RATE
# ============================================================

stock_summary["Win_Rate"] = (
    stock_summary["Winning_Trades"]
    / stock_summary["Total_Trades"]
)


# ============================================================
# LOSING TRADES
# ============================================================

stock_summary["Losing_Trades"] = (
    stock_summary["Total_Trades"]
    - stock_summary["Winning_Trades"]
)


# ============================================================
# PORTFOLIO TOTAL P&L
# ============================================================

portfolio_total_pnl = (
    stock_summary["Total_PnL"]
    .sum()
)


# ============================================================
# CONTRIBUTION TO TOTAL P&L
# ============================================================

if portfolio_total_pnl != 0:

    stock_summary[
        "PnL_Contribution"
    ] = (
        stock_summary["Total_PnL"]
        / portfolio_total_pnl
    )

else:

    stock_summary[
        "PnL_Contribution"
    ] = 0.0


# ============================================================
# POSITIVE / NEGATIVE CONTRIBUTION FLAG
# ============================================================

stock_summary["Contribution_Direction"] = (
    stock_summary["Total_PnL"]
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
# SORT BY TOTAL P&L
# ============================================================

stock_summary = (
    stock_summary
    .sort_values(
        "Total_PnL",
        ascending=False,
    )
    .reset_index(drop=True)
)


# ============================================================
# SAVE
# ============================================================

stock_summary.to_csv(
    OUTPUT_FILE,
    index=False,
)


# ============================================================
# DISPLAY
# ============================================================

print()
print("=" * 100)
print(
    "PORTFOLIO STOCK ATTRIBUTION"
)
print("=" * 100)

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
    f"Portfolio trade P&L: "
    f"₹{portfolio_total_pnl:,.2f}"
)

print()

display_columns = [
    "Stock",
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
]

display_df = stock_summary[
    display_columns
].copy()


# ------------------------------------------------------------
# FORMAT DISPLAY
# ------------------------------------------------------------

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
        stock_summary["Total_PnL"].sum()
        - portfolio_total_pnl
    )
    < 1e-6
)


print()

print(
    "Validation: stock P&L sums "
    "to portfolio trade P&L."
)

print()

print(
    f"Results saved to:\n{OUTPUT_FILE}"
)

print("=" * 100)