import pandas as pd
import numpy as np

INPUT_PATH = "data/processed/reliance_features.csv"

print("=" * 60)
print("RISK METRICS v0.1")
print("=" * 60)

df = pd.read_csv(
    INPUT_PATH,
    index_col=0,
    parse_dates=True
)

# --------------------------------------------------
# 1. SIGNAL
# --------------------------------------------------

df["Signal"] = (
    (df["Return_20D"] > 0) &
    (df["SMA_20"] > df["SMA_50"]) &
    (df["Close"] > df["SMA_200"])
)

# Trade next day
df["Position"] = (
    df["Signal"]
    .shift(1)
    .fillna(False)
    .astype(bool)
)

# --------------------------------------------------
# 2. STRATEGY RETURNS
# --------------------------------------------------

df["Strategy_Return"] = (
    df["Position"] *
    df["Daily_Return"]
)

returns = df["Strategy_Return"]

# --------------------------------------------------
# 3. EQUITY
# --------------------------------------------------

equity = (
    1 + returns
).cumprod()

# --------------------------------------------------
# 4. CAGR
# --------------------------------------------------

days = (
    df.index[-1] - df.index[0]
).days

years = days / 365.25

cagr = (
    equity.iloc[-1] ** (1 / years)
) - 1

# --------------------------------------------------
# 5. VOLATILITY
# --------------------------------------------------

annualized_volatility = (
    returns.std() *
    np.sqrt(252)
)

# --------------------------------------------------
# 6. SHARPE
# --------------------------------------------------

sharpe = (
    returns.mean() /
    returns.std()
) * np.sqrt(252)

# --------------------------------------------------
# 7. DRAWDOWN
# --------------------------------------------------

peak = equity.cummax()

drawdown = (
    equity / peak
) - 1

max_drawdown = drawdown.min()

# --------------------------------------------------
# 8. CALMAR
# --------------------------------------------------

calmar = (
    cagr / abs(max_drawdown)
)

# --------------------------------------------------
# 9. WIN RATE
# --------------------------------------------------

active_returns = returns[returns != 0]

win_rate = (
    active_returns > 0
).mean()

# --------------------------------------------------
# 10. PROFIT FACTOR
# --------------------------------------------------

gross_profit = (
    active_returns[active_returns > 0]
    .sum()
)

gross_loss = abs(
    active_returns[active_returns < 0]
    .sum()
)

profit_factor = (
    gross_profit / gross_loss
    if gross_loss != 0
    else np.nan
)

# --------------------------------------------------
# 11. OUTPUT
# --------------------------------------------------

print("\nPERFORMANCE")
print("-" * 40)

print(f"CAGR: {cagr:.2%}")

print(
    f"Annualized volatility: "
    f"{annualized_volatility:.2%}"
)

print(
    f"Maximum drawdown: "
    f"{max_drawdown:.2%}"
)

print(f"Sharpe ratio: {sharpe:.3f}")

print(f"Calmar ratio: {calmar:.3f}")

print("\nTRADE DISTRIBUTION")
print("-" * 40)

print(
    f"Active trading days: "
    f"{len(active_returns)}"
)

print(
    f"Daily win rate: "
    f"{win_rate:.2%}"
)

print(
    f"Profit factor: "
    f"{profit_factor:.3f}"
)

print("\n" + "=" * 60)
print("RISK METRICS COMPLETE")
print("=" * 60)