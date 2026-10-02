import pandas as pd
import numpy as np

INPUT_PATH = "data/processed/reliance_features.csv"

TRAIN_END = "2023-12-31"

print("=" * 60)
print("OUT-OF-SAMPLE TEST v0.1")
print("=" * 60)

df = pd.read_csv(
    INPUT_PATH,
    index_col=0,
    parse_dates=True
)

# --------------------------------------------------
# 1. CREATE FIXED SIGNAL
# --------------------------------------------------

df["Signal"] = (
    (df["Return_20D"] > 0) &
    (df["SMA_20"] > df["SMA_50"]) &
    (df["Close"] > df["SMA_200"])
)

df["Position"] = (
    df["Signal"]
    .shift(1)
    .fillna(False)
    .astype(bool)
)

df["Strategy_Return"] = (
    df["Position"] *
    df["Daily_Return"]
)

# --------------------------------------------------
# 2. SPLIT CHRONOLOGICALLY
# --------------------------------------------------

train = df.loc[:TRAIN_END].copy()

test = df.loc["2024-01-01":].copy()

# --------------------------------------------------
# 3. PERFORMANCE FUNCTION
# --------------------------------------------------

def performance(data):

    equity = (
        1 + data["Strategy_Return"]
    ).cumprod()

    total_return = (
        equity.iloc[-1] - 1
    )

    volatility = (
        data["Strategy_Return"].std()
        * np.sqrt(252)
    )

    peak = equity.cummax()

    drawdown = (
        equity / peak
    ) - 1

    max_drawdown = drawdown.min()

    return (
        total_return,
        volatility,
        max_drawdown,
        len(data)
    )

# --------------------------------------------------
# 4. CALCULATE
# --------------------------------------------------

train_return, train_vol, train_dd, train_rows = (
    performance(train)
)

test_return, test_vol, test_dd, test_rows = (
    performance(test)
)

# --------------------------------------------------
# 5. OUTPUT
# --------------------------------------------------

print("\nDEVELOPMENT PERIOD")
print("-" * 40)

print(f"Period: {train.index[0].date()} → {train.index[-1].date()}")
print(f"Rows: {train_rows}")
print(f"Return: {train_return:.2%}")
print(f"Volatility: {train_vol:.2%}")
print(f"Maximum drawdown: {train_dd:.2%}")

print("\nOUT-OF-SAMPLE PERIOD")
print("-" * 40)

print(f"Period: {test.index[0].date()} → {test.index[-1].date()}")
print(f"Rows: {test_rows}")
print(f"Return: {test_return:.2%}")
print(f"Volatility: {test_vol:.2%}")
print(f"Maximum drawdown: {test_dd:.2%}")

print("\n" + "=" * 60)
print("OUT-OF-SAMPLE TEST COMPLETE")
print("=" * 60)