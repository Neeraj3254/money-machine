import pandas as pd
import numpy as np

INPUT_PATH = "data/processed/reliance_features.csv"

print("=" * 60)
print("MOMENTUM BACKTEST v0.1")
print("=" * 60)

# --------------------------------------------------
# 1. LOAD DATA
# --------------------------------------------------

df = pd.read_csv(
    INPUT_PATH,
    index_col=0,
    parse_dates=True
)

print(f"\nRows loaded: {len(df)}")


# --------------------------------------------------
# 2. CREATE SIGNAL
# --------------------------------------------------

df["Signal"] = (
    (df["Return_20D"] > 0) &
    (df["SMA_20"] > df["SMA_50"]) &
    (df["Close"] > df["SMA_200"])
)


# --------------------------------------------------
# 3. AVOID LOOK-AHEAD BIAS
# --------------------------------------------------

# Signal generated using information available
# at the current close.
#
# Position begins on the NEXT trading day.

df["Position"] = (
    df["Signal"]
    .shift(1)
    .fillna(False)
)


# --------------------------------------------------
# 4. STRATEGY DAILY RETURN
# --------------------------------------------------

df["Strategy_Return"] = (
    df["Position"] *
    df["Daily_Return"]
)


# --------------------------------------------------
# 5. EQUITY CURVES
# --------------------------------------------------

df["Strategy_Equity"] = (
    1 + df["Strategy_Return"]
).cumprod()

df["BuyHold_Equity"] = (
    1 + df["Daily_Return"]
).cumprod()


# --------------------------------------------------
# 6. STRATEGY DRAWDOWN
# --------------------------------------------------

strategy_peak = (
    df["Strategy_Equity"]
    .cummax()
)

df["Strategy_Drawdown"] = (
    df["Strategy_Equity"] /
    strategy_peak
) - 1


# --------------------------------------------------
# 7. PERFORMANCE
# --------------------------------------------------

strategy_return = (
    df["Strategy_Equity"].iloc[-1] - 1
)

buyhold_return = (
    df["BuyHold_Equity"].iloc[-1] - 1
)

strategy_max_drawdown = (
    df["Strategy_Drawdown"].min()
)


# --------------------------------------------------
# 8. VOLATILITY
# --------------------------------------------------

strategy_volatility = (
    df["Strategy_Return"]
    .std()
    * np.sqrt(252)
)


# --------------------------------------------------
# 9. MARKET EXPOSURE
# --------------------------------------------------

exposure = df["Position"].mean()


# --------------------------------------------------
# 10. NUMBER OF ENTRIES
# --------------------------------------------------

entries = (
    df["Position"] &
    ~df["Position"].shift(1).fillna(False)
).sum()


# --------------------------------------------------
# 11. OUTPUT
# --------------------------------------------------

print("\nSTRATEGY")
print("-" * 40)

print(
    f"Total return: "
    f"{strategy_return:.2%}"
)

print(
    f"Annualized volatility: "
    f"{strategy_volatility:.2%}"
)

print(
    f"Maximum drawdown: "
    f"{strategy_max_drawdown:.2%}"
)

print(
    f"Market exposure: "
    f"{exposure:.2%}"
)

print(
    f"Number of entries: "
    f"{entries}"
)


print("\nBUY & HOLD")
print("-" * 40)

print(
    f"Total return: "
    f"{buyhold_return:.2%}"
)


print("\n" + "=" * 60)
print("BACKTEST COMPLETE")
print("=" * 60)