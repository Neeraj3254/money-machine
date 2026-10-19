from pathlib import Path

import numpy as np
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

OUTPUT_FILE = (
    PROCESSED_DIR
    / "portfolio_cost_risk_metrics.csv"
)

TRADING_DAYS_PER_YEAR = 252

INITIAL_CAPITAL = 100_000.0


# ============================================================
# COST SCENARIOS
# ============================================================

COST_SCENARIOS = [
    0.0000,
    0.0010,
    0.0020,
    0.0040,
    0.0060,
    0.0100,
]


# ============================================================
# METRIC FUNCTION
# ============================================================

def calculate_metrics(
    equity_curve,
    cost,
):
    """
    Calculate risk and performance metrics
    from a daily portfolio equity curve.
    """

    equity_curve = equity_curve.copy()

    equity_curve["Date"] = pd.to_datetime(
        equity_curve["Date"]
    )

    equity_curve = (
        equity_curve
        .sort_values("Date")
        .reset_index(drop=True)
    )

    equity = (
        equity_curve["Portfolio_Equity"]
        .astype(float)
    )

    # --------------------------------------------------------
    # DAILY RETURNS
    # --------------------------------------------------------

    daily_returns = (
        equity
        .pct_change()
        .dropna()
    )


    # --------------------------------------------------------
    # START / END
    # --------------------------------------------------------

    start_date = (
        equity_curve["Date"].iloc[0]
    )

    end_date = (
        equity_curve["Date"].iloc[-1]
    )

    start_value = float(
        equity.iloc[0]
    )

    final_value = float(
        equity.iloc[-1]
    )


    # --------------------------------------------------------
    # TIME PERIOD
    # --------------------------------------------------------

    days = (
        end_date - start_date
    ).days

    years = (
        days / 365.25
    )


    # --------------------------------------------------------
    # TOTAL RETURN
    # --------------------------------------------------------

    total_return = (
        final_value
        / start_value
    ) - 1.0


    # --------------------------------------------------------
    # CAGR
    # --------------------------------------------------------

    if years > 0 and final_value > 0:

        cagr = (
            final_value
            / start_value
        ) ** (
            1.0 / years
        ) - 1.0

    else:

        cagr = np.nan


    # --------------------------------------------------------
    # ANNUALIZED VOLATILITY
    # --------------------------------------------------------

    if len(daily_returns) > 1:

        annualized_volatility = (
            daily_returns.std(
                ddof=1
            )
            * np.sqrt(
                TRADING_DAYS_PER_YEAR
            )
        )

    else:

        annualized_volatility = np.nan


    # --------------------------------------------------------
    # RUNNING PEAK
    # --------------------------------------------------------

    running_peak = (
        equity
        .cummax()
    )


    # --------------------------------------------------------
    # DRAWDOWN
    # --------------------------------------------------------

    drawdown = (
        equity
        / running_peak
    ) - 1.0


    # --------------------------------------------------------
    # MAXIMUM DRAWDOWN
    # --------------------------------------------------------

    max_drawdown = float(
        drawdown.min()
    )


    # --------------------------------------------------------
    # SHARPE RATIO
    # --------------------------------------------------------
    #
    # Risk-free rate assumed to be 0%.
    #
    # Sharpe =
    #
    # annualized mean daily return
    # ----------------------------
    # annualized volatility
    #
    # --------------------------------------------------------

    if (
        len(daily_returns) > 1
        and daily_returns.std(
            ddof=1
        ) > 0
    ):

        sharpe = (
            daily_returns.mean()
            / daily_returns.std(
                ddof=1
            )
            * np.sqrt(
                TRADING_DAYS_PER_YEAR
            )
        )

    else:

        sharpe = np.nan


    # --------------------------------------------------------
    # CALMAR RATIO
    # --------------------------------------------------------
    #
    # CAGR / absolute maximum drawdown
    #
    # --------------------------------------------------------

    if (
        max_drawdown < 0
        and not np.isnan(cagr)
    ):

        calmar = (
            cagr
            / abs(max_drawdown)
        )

    else:

        calmar = np.nan


    # --------------------------------------------------------
    # DAILY WIN RATE
    # --------------------------------------------------------

    positive_days = int(
        (daily_returns > 0).sum()
    )

    negative_days = int(
        (daily_returns < 0).sum()
    )

    flat_days = int(
        (daily_returns == 0).sum()
    )

    total_return_days = (
        positive_days
        + negative_days
    )

    if total_return_days > 0:

        daily_win_rate = (
            positive_days
            / total_return_days
        )

    else:

        daily_win_rate = np.nan


    # --------------------------------------------------------
    # BEST / WORST DAY
    # --------------------------------------------------------

    if len(daily_returns) > 0:

        best_day = float(
            daily_returns.max()
        )

        worst_day = float(
            daily_returns.min()
        )

    else:

        best_day = np.nan
        worst_day = np.nan


    # --------------------------------------------------------
    # TIME UNDERWATER
    # --------------------------------------------------------
    #
    # Underwater means:
    #
    # equity < previous peak
    #
    # This does NOT mean the portfolio
    # was losing money every day.
    #
    # It means it had not yet recovered
    # its previous high-water mark.
    #
    # --------------------------------------------------------

    underwater = (
        drawdown < 0
    )

    underwater_days = int(
        underwater.sum()
    )

    total_days = len(
        equity_curve
    )

    if total_days > 0:

        time_underwater = (
            underwater_days
            / total_days
        )

    else:

        time_underwater = np.nan


    # --------------------------------------------------------
    # AVERAGE EXPOSURE
    # --------------------------------------------------------

    if "Exposure" in equity_curve.columns:

        average_exposure = float(
            equity_curve[
                "Exposure"
            ].mean()
        )

        max_exposure = float(
            equity_curve[
                "Exposure"
            ].max()
        )

    else:

        average_exposure = np.nan
        max_exposure = np.nan


    # --------------------------------------------------------
    # MAX ACTIVE POSITIONS
    # --------------------------------------------------------

    if "Active_Positions" in equity_curve.columns:

        max_active_positions = int(
            equity_curve[
                "Active_Positions"
            ].max()
        )

    else:

        max_active_positions = np.nan


    # --------------------------------------------------------
    # RETURN RESULTS
    # --------------------------------------------------------

    return {
        "Cost_Per_Side": cost,

        "Start_Date": start_date,

        "End_Date": end_date,

        "Initial_Value": start_value,

        "Final_Value": final_value,

        "Total_Return": total_return,

        "CAGR": cagr,

        "Annualized_Volatility": (
            annualized_volatility
        ),

        "Max_Drawdown": max_drawdown,

        "Sharpe": sharpe,

        "Calmar": calmar,

        "Positive_Days": positive_days,

        "Negative_Days": negative_days,

        "Flat_Days": flat_days,

        "Daily_Win_Rate": daily_win_rate,

        "Best_Day": best_day,

        "Worst_Day": worst_day,

        "Underwater_Days": underwater_days,

        "Time_Underwater": time_underwater,

        "Average_Exposure": average_exposure,

        "Max_Exposure": max_exposure,

        "Max_Active_Positions": (
            max_active_positions
        ),

        "Trading_Days": len(
            equity_curve
        ),
    }


# ============================================================
# LOAD ALL COST SCENARIOS
# ============================================================

results = []


for cost in COST_SCENARIOS:

    cost_tag = (
        f"{cost:.4f}"
        .replace(".", "_")
    )

    equity_file = (
        PROCESSED_DIR
        / (
            "stateful_portfolio_equity_"
            f"cost_{cost_tag}.csv"
        )
    )


    # --------------------------------------------------------
    # CHECK FILE EXISTS
    # --------------------------------------------------------

    if not equity_file.exists():

        raise FileNotFoundError(
            "\nEquity file not found:\n"
            f"{equity_file}\n\n"
            "Run the corresponding "
            "backtest before running "
            "this risk analysis."
        )


    # --------------------------------------------------------
    # LOAD EQUITY CURVE
    # --------------------------------------------------------

    equity_curve = pd.read_csv(
        equity_file
    )


    # --------------------------------------------------------
    # VALIDATE REQUIRED COLUMNS
    # --------------------------------------------------------

    required_columns = {
        "Date",
        "Portfolio_Equity",
    }

    missing_columns = (
        required_columns
        - set(equity_curve.columns)
    )

    if missing_columns:

        raise ValueError(
            f"{equity_file.name} is missing "
            f"columns: "
            f"{sorted(missing_columns)}"
        )


    # --------------------------------------------------------
    # CALCULATE METRICS
    # --------------------------------------------------------

    metrics = calculate_metrics(
        equity_curve,
        cost,
    )

    results.append(
        metrics
    )


# ============================================================
# CREATE RESULTS TABLE
# ============================================================

results_df = pd.DataFrame(
    results
)


# ============================================================
# SORT BY COST
# ============================================================

results_df = (
    results_df
    .sort_values(
        "Cost_Per_Side"
    )
    .reset_index(drop=True)
)


# ============================================================
# SAVE RESULTS
# ============================================================

results_df.to_csv(
    OUTPUT_FILE,
    index=False,
)


# ============================================================
# DISPLAY REPORT
# ============================================================

print()
print("=" * 100)
print("PORTFOLIO RISK — TRANSACTION COST SENSITIVITY")
print("=" * 100)

print()

display_columns = [
    "Cost_Per_Side",
    "Final_Value",
    "Total_Return",
    "CAGR",
    "Annualized_Volatility",
    "Max_Drawdown",
    "Sharpe",
    "Calmar",
    "Daily_Win_Rate",
    "Time_Underwater",
]

display_df = (
    results_df[
        display_columns
    ]
    .copy()
)


# ------------------------------------------------------------
# FORMAT FOR TERMINAL
# ------------------------------------------------------------

display_df["Cost_Per_Side"] = (
    display_df["Cost_Per_Side"]
    .map(
        lambda x: f"{x:.2%}"
    )
)

display_df["Final_Value"] = (
    display_df["Final_Value"]
    .map(
        lambda x: f"₹{x:,.2f}"
    )
)

percentage_columns = [
    "Total_Return",
    "CAGR",
    "Annualized_Volatility",
    "Max_Drawdown",
    "Daily_Win_Rate",
    "Time_Underwater",
]

for column in percentage_columns:

    display_df[column] = (
        display_df[column]
        .map(
            lambda x: f"{x:.2%}"
        )
    )


display_df["Sharpe"] = (
    display_df["Sharpe"]
    .map(
        lambda x: f"{x:.3f}"
    )
)

display_df["Calmar"] = (
    display_df["Calmar"]
    .map(
        lambda x: f"{x:.3f}"
    )
)


print(
    display_df.to_string(
        index=False
    )
)


# ============================================================
# ADDITIONAL INFORMATION
# ============================================================

print()
print("-" * 100)

print(
    f"Results saved to:\n{OUTPUT_FILE}"
)

print()

print(
    "Risk-free rate assumption: 0%"
)

print(
    "Volatility annualization: "
    "252 trading days"
)

print(
    "CAGR uses actual calendar time "
    "between first and last equity dates."
)

print(
    "Sharpe uses daily portfolio returns."
)

print(
    "Time underwater means equity is "
    "below its previous high-water mark."
)

print("=" * 100)