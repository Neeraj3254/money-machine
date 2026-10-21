import pandas as pd
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "stateful_trades.csv"
)

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "stateful_equity_curve.csv"
)

INITIAL_CAPITAL = 100_000


# ============================================================
# LOAD TRADES
# ============================================================

trades = pd.read_csv(
    INPUT_FILE,
    parse_dates=["Signal_Date", "Entry_Date", "Exit_Date"]
)

trades = trades.sort_values("Trade_ID").reset_index(drop=True)


# ============================================================
# BUILD EQUITY CURVE
# ============================================================

equity = INITIAL_CAPITAL

equity_values = []

for _, trade in trades.iterrows():

    trade_return = trade["Return"]

    equity *= (1 + trade_return)

    equity_values.append(equity)


trades["Equity"] = equity_values


# ============================================================
# DRAWDOWN
# ============================================================

trades["Equity_Peak"] = trades["Equity"].cummax()

trades["Drawdown"] = (
    trades["Equity"] / trades["Equity_Peak"]
) - 1


# ============================================================
# BASIC METRICS
# ============================================================

final_equity = trades["Equity"].iloc[-1]

total_return = (
    final_equity / INITIAL_CAPITAL
) - 1

max_drawdown = trades["Drawdown"].min()


# ============================================================
# WIN / LOSS METRICS
# ============================================================

wins = trades.loc[trades["Return"] > 0, "Return"]

losses = trades.loc[trades["Return"] < 0, "Return"]


win_rate = len(wins) / len(trades)

average_win = wins.mean()

average_loss = abs(losses.mean())


# ============================================================
# EXPECTANCY
# ============================================================

expectancy = (
    win_rate * average_win
    - (1 - win_rate) * average_loss
)


# ============================================================
# PROFIT FACTOR
# ============================================================

gross_profit = wins.sum()

gross_loss = abs(losses.sum())

profit_factor = gross_profit / gross_loss


# ============================================================
# CONSECUTIVE WINS / LOSSES
# ============================================================

max_consecutive_wins = 0
max_consecutive_losses = 0

current_wins = 0
current_losses = 0


for result in trades["Return"]:

    if result > 0:

        current_wins += 1
        current_losses = 0

        max_consecutive_wins = max(
            max_consecutive_wins,
            current_wins
        )

    elif result < 0:

        current_losses += 1
        current_wins = 0

        max_consecutive_losses = max(
            max_consecutive_losses,
            current_losses
        )


# ============================================================
# OUTPUT
# ============================================================

trades.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# REPORT
# ============================================================

print("=" * 60)
print("STATEFUL RISK LEDGER")
print("=" * 60)

print(f"Initial capital:        ₹{INITIAL_CAPITAL:,.2f}")
print(f"Final equity:           ₹{final_equity:,.2f}")
print(f"Total return:           {total_return:.2%}")
print(f"Maximum drawdown:       {max_drawdown:.2%}")
print()

print(f"Number of trades:       {len(trades)}")
print(f"Win rate:               {win_rate:.2%}")
print(f"Average winner:         {average_win:.2%}")
print(f"Average loser:          {average_loss:.2%}")
print(f"Expectancy:             {expectancy:.2%}")
print(f"Profit factor:          {profit_factor:.2f}")
print()

print(
    f"Max consecutive wins:   "
    f"{max_consecutive_wins}"
)

print(
    f"Max consecutive losses: "
    f"{max_consecutive_losses}"
)

print()

print(f"Saved: {OUTPUT_FILE}")