import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "stateful_portfolio_equity_v2.csv"
)


# ============================================================
# LOAD EQUITY CURVE
# ============================================================

df = pd.read_csv(
    INPUT_FILE,
    parse_dates=["Date"]
)

df = (
    df
    .sort_values("Date")
    .reset_index(drop=True)
)


# ============================================================
# DAILY RETURNS
# ============================================================

df["Daily_Return"] = (
    df["Portfolio_Equity"]
    .pct_change()
)


returns = (
    df["Daily_Return"]
    .dropna()
)


# ============================================================
# CAGR
# ============================================================

start_equity = (
    df["Portfolio_Equity"].iloc[0]
)

end_equity = (
    df["Portfolio_Equity"].iloc[-1]
)

days = (
    df["Date"].iloc[-1]
    - df["Date"].iloc[0]
).days

years = days / 365.25

cagr = (
    (end_equity / start_equity)
    ** (1 / years)
    - 1
)


# ============================================================
# ANNUALIZED VOLATILITY
# ============================================================

annualized_volatility = (
    returns.std()
    * np.sqrt(252)
)


# ============================================================
# DRAWDOWN
# ============================================================

running_max = (
    df["Portfolio_Equity"]
    .cummax()
)

df["Drawdown"] = (
    df["Portfolio_Equity"]
    / running_max
    - 1
)

max_drawdown = (
    df["Drawdown"].min()
)


# ============================================================
# SHARPE RATIO
# ============================================================
#
# Risk-free rate = 0 for this research diagnostic.
#
# We are not claiming this is an investable Sharpe ratio.
# It is a standardized comparison metric.
# ============================================================

if returns.std() > 0:

    sharpe = (
        returns.mean()
        / returns.std()
    ) * np.sqrt(252)

else:

    sharpe = np.nan


# ============================================================
# CALMAR RATIO
# ============================================================

if max_drawdown < 0:

    calmar = (
        cagr
        / abs(max_drawdown)
    )

else:

    calmar = np.nan


# ============================================================
# DAILY WIN RATE
# ============================================================

positive_days = (
    returns > 0
).sum()

negative_days = (
    returns < 0
).sum()

flat_days = (
    returns == 0
).sum()

daily_win_rate = (
    positive_days
    / len(returns)
)


# ============================================================
# TIME UNDERWATER
# ============================================================

underwater = (
    df["Drawdown"] < 0
)

underwater_days = (
    underwater.sum()
)

underwater_percentage = (
    underwater_days
    / len(df)
)


# ============================================================
# WORST DAILY RETURN
# ============================================================

worst_day = (
    returns.min()
)

best_day = (
    returns.max()
)


# ============================================================
# EXPOSURE
# ============================================================

average_exposure = (
    df["Exposure"].mean()
)

maximum_exposure = (
    df["Exposure"].max()
)


# ============================================================
# REPORT
# ============================================================

print("=" * 70)
print("PORTFOLIO RISK METRICS")
print("=" * 70)

print(
    f"Start date:              "
    f"{df['Date'].iloc[0].date()}"
)

print(
    f"End date:                "
    f"{df['Date'].iloc[-1].date()}"
)

print(
    f"Initial equity:          "
    f"₹{start_equity:,.2f}"
)

print(
    f"Final equity:            "
    f"₹{end_equity:,.2f}"
)

print()

print(
    f"CAGR:                    "
    f"{cagr:.2%}"
)

print(
    f"Annualized volatility:   "
    f"{annualized_volatility:.2%}"
)

print(
    f"Maximum drawdown:        "
    f"{max_drawdown:.2%}"
)

print(
    f"Sharpe ratio:            "
    f"{sharpe:.3f}"
)

print(
    f"Calmar ratio:            "
    f"{calmar:.3f}"
)

print()

print(
    f"Positive days:           "
    f"{positive_days}"
)

print(
    f"Negative days:           "
    f"{negative_days}"
)

print(
    f"Flat days:               "
    f"{flat_days}"
)

print(
    f"Daily win rate:          "
    f"{daily_win_rate:.2%}"
)

print()

print(
    f"Best daily return:       "
    f"{best_day:.2%}"
)

print(
    f"Worst daily return:      "
    f"{worst_day:.2%}"
)

print()

print(
    f"Underwater days:         "
    f"{underwater_days}"
)

print(
    f"Time underwater:         "
    f"{underwater_percentage:.2%}"
)

print()

print(
    f"Average exposure:        "
    f"{average_exposure:.2%}"
)

print(
    f"Maximum exposure:        "
    f"{maximum_exposure:.2%}"
)

print()

print(
    f"Trading days analyzed:   "
    f"{len(df)}"
)