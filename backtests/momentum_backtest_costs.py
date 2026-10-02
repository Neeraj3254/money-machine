import pandas as pd
import numpy as np

INPUT_PATH = "data/processed/reliance_features.csv"

# Research assumptions only.
# These are not your actual broker charges.
COST_PER_SIDE = 0.0010
SLIPPAGE_PER_SIDE = 0.0010

print("=" * 60)
print("MOMENTUM BACKTEST WITH COSTS v0.1")
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
# 3. TRADE ON NEXT DAY
# --------------------------------------------------

df["Position"] = (
    df["Signal"]
    .shift(1)
    .fillna(False)
    .astype(bool)
)


# --------------------------------------------------
# 4. GROSS RETURN
# --------------------------------------------------

df["Gross_Return"] = (
    df["Position"] *
    df["Daily_Return"]
)


# --------------------------------------------------
# 5. DETECT ENTRIES / EXITS
# --------------------------------------------------

previous_position = (
    df["Position"]
    .shift(1)
    .fillna(False)
    .astype(bool)
)

entries = (
    df["Position"] &
    ~previous_position
)

exits = (
    ~df["Position"] &
    previous_position
)

trade_events = entries | exits


# --------------------------------------------------
# 6. TRADING COSTS
# --------------------------------------------------

cost_per_event = (
    COST_PER_SIDE +
    SLIPPAGE_PER_SIDE
)

df["Trading_Cost"] = (
    trade_events.astype(float)
    * cost_per_event
)


# --------------------------------------------------
# 7. NET RETURN
# --------------------------------------------------

df["Net_Return"] = (
    df["Gross_Return"] -
    df["Trading_Cost"]
)


# --------------------------------------------------
# 8. EQUITY CURVES
# --------------------------------------------------

df["Gross_Equity"] = (
    1 + df["Gross_Return"]
).cumprod()

df["Net_Equity"] = (
    1 + df["Net_Return"]
).cumprod()


# --------------------------------------------------
# 9. NET DRAWDOWN
# --------------------------------------------------

peak = df["Net_Equity"].cummax()

df["Net_Drawdown"] = (
    df["Net_Equity"] /
    peak
) - 1


# --------------------------------------------------
# 10. STATISTICS
# --------------------------------------------------

gross_return = (
    df["Gross_Equity"].iloc[-1] - 1
)

net_return = (
    df["Net_Equity"].iloc[-1] - 1
)

max_drawdown = (
    df["Net_Drawdown"].min()
)

annualized_volatility = (
    df["Net_Return"].std()
    * np.sqrt(252)
)

number_of_entries = int(entries.sum())

number_of_exits = int(exits.sum())

total_cost = df["Trading_Cost"].sum()


# --------------------------------------------------
# 11. OUTPUT
# --------------------------------------------------

print("\nRESEARCH ASSUMPTIONS")
print("-" * 40)

print(
    f"Cost per side: "
    f"{COST_PER_SIDE:.2%}"
)

print(
    f"Slippage per side: "
    f"{SLIPPAGE_PER_SIDE:.2%}"
)

print("\nRESULTS")
print("-" * 40)

print(
    f"Gross return: "
    f"{gross_return:.2%}"
)

print(
    f"Net return: "
    f"{net_return:.2%}"
)

print(
    f"Annualized volatility: "
    f"{annualized_volatility:.2%}"
)

print(
    f"Maximum drawdown: "
    f"{max_drawdown:.2%}"
)

print(
    f"Entries: "
    f"{number_of_entries}"
)

print(
    f"Exits: "
    f"{number_of_exits}"
)

print(
    f"Total modeled trading cost: "
    f"{total_cost:.2%}"
)

print("\n" + "=" * 60)
print("COST-ADJUSTED BACKTEST COMPLETE")
print("=" * 60)