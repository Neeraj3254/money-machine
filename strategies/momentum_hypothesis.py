import pandas as pd

INPUT_PATH = "data/processed/reliance_features.csv"

print("=" * 60)
print("MOMENTUM HYPOTHESIS v0.1")
print("=" * 60)

df = pd.read_csv(
    INPUT_PATH,
    index_col=0,
    parse_dates=True
)

# --------------------------------------------------
# HYPOTHESIS
# --------------------------------------------------

# Current-day information only.
# We will evaluate what happens AFTER the signal.

df["Signal"] = (
    (df["Return_20D"] > 0) &
    (df["SMA_20"] > df["SMA_50"]) &
    (df["Close"] > df["SMA_200"])
)

# --------------------------------------------------
# FORWARD RETURN
# --------------------------------------------------

df["Forward_5D_Return"] = (
    df["Close"].shift(-5) /
    df["Close"]
) - 1

df["Forward_20D_Return"] = (
    df["Close"].shift(-20) /
    df["Close"]
) - 1

# --------------------------------------------------
# SIGNAL DATA
# --------------------------------------------------

signal_days = df[df["Signal"]].copy()

print(f"\nTotal observations: {len(df)}")

print(
    f"Signal observations: "
    f"{len(signal_days)}"
)

print(
    f"Signal frequency: "
    f"{len(signal_days) / len(df):.2%}"
)

# --------------------------------------------------
# FORWARD PERFORMANCE
# --------------------------------------------------

print("\nForward returns when signal is TRUE:")

print(
    f"Average 5D return: "
    f"{signal_days['Forward_5D_Return'].mean():.4%}"
)

print(
    f"Average 20D return: "
    f"{signal_days['Forward_20D_Return'].mean():.4%}"
)

print(
    f"5D positive rate: "
    f"{(signal_days['Forward_5D_Return'] > 0).mean():.2%}"
)

print(
    f"20D positive rate: "
    f"{(signal_days['Forward_20D_Return'] > 0).mean():.2%}"
)

print("\n" + "=" * 60)
print("HYPOTHESIS TEST COMPLETE")
print("=" * 60)