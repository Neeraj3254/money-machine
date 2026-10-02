import pandas as pd
import numpy as np

INPUT_PATH = "data/processed/reliance_daily_clean.csv"

print("=" * 60)
print("MARKET STATISTICS v0.1")
print("=" * 60)

# Load validated data
df = pd.read_csv(
    INPUT_PATH,
    index_col=0,
    parse_dates=True
)

# --------------------------------------------------
# 1. DAILY RETURNS
# --------------------------------------------------

df["Return"] = df["Close"].pct_change()

returns = df["Return"].dropna()

print("\n[1] Return Statistics")

print(f"Trading days: {len(returns)}")
print(f"Average daily return: {returns.mean():.6f}")
print(f"Daily volatility: {returns.std():.6f}")

# --------------------------------------------------
# 2. POSITIVE / NEGATIVE DAYS
# --------------------------------------------------

positive_days = (returns > 0).sum()
negative_days = (returns < 0).sum()
flat_days = (returns == 0).sum()

print("\n[2] Daily Direction")

print(f"Positive days: {positive_days}")
print(f"Negative days: {negative_days}")
print(f"Flat days: {flat_days}")

print(f"Positive-day percentage: "
      f"{positive_days / len(returns) * 100:.2f}%")

# --------------------------------------------------
# 3. CUMULATIVE RETURN
# --------------------------------------------------

cumulative_return = (
    df["Close"].iloc[-1] / df["Close"].iloc[0]
) - 1

print("\n[3] Cumulative Return")

print(f"Cumulative return: {cumulative_return:.2%}")

# --------------------------------------------------
# 4. ANNUALIZED VOLATILITY
# --------------------------------------------------

annualized_volatility = returns.std() * np.sqrt(252)

print("\n[4] Annualized Volatility")

print(f"Annualized volatility: "
      f"{annualized_volatility:.2%}")

# --------------------------------------------------
# 5. MAXIMUM DRAWDOWN
# --------------------------------------------------

running_max = df["Close"].cummax()

drawdown = (
    df["Close"] / running_max
) - 1

max_drawdown = drawdown.min()

print("\n[5] Maximum Drawdown")

print(f"Maximum drawdown: {max_drawdown:.2%}")

# --------------------------------------------------
# 6. AVERAGE WIN / LOSS
# --------------------------------------------------

average_gain = returns[returns > 0].mean()
average_loss = returns[returns < 0].mean()

print("\n[6] Average Gain / Loss")

print(f"Average positive return: {average_gain:.4%}")
print(f"Average negative return: {average_loss:.4%}")

# --------------------------------------------------
# 7. SUMMARY
# --------------------------------------------------

print("\n" + "=" * 60)
print("MARKET STATISTICS COMPLETE")
print("=" * 60)