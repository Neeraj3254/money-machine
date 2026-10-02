import pandas as pd

INPUT_PATH = "data/processed/reliance_features.csv"

print("=" * 60)
print("BENCHMARK ANALYSIS v0.2")
print("=" * 60)

# --------------------------------------------------
# 1. LOAD FEATURES
# --------------------------------------------------

df = pd.read_csv(
    INPUT_PATH,
    index_col=0,
    parse_dates=True
)

print(f"\nRows loaded: {len(df)}")


# --------------------------------------------------
# 2. CREATE FORWARD RETURNS
# --------------------------------------------------

# IMPORTANT:
# These returns represent what happened AFTER
# the current observation.

df["Forward_20D_Return"] = (
    df["Close"].shift(-20) /
    df["Close"]
) - 1


# Remove rows where a future 20-day observation
# does not exist.

df = df.dropna(
    subset=["Forward_20D_Return"]
)


# --------------------------------------------------
# 3. UNCONDITIONAL BASELINE
# --------------------------------------------------

baseline_return = (
    df["Forward_20D_Return"].mean()
)

baseline_positive_rate = (
    df["Forward_20D_Return"] > 0
).mean()


# --------------------------------------------------
# 4. MOMENTUM CONDITION
# --------------------------------------------------

signal = (
    (df["Return_20D"] > 0) &
    (df["SMA_20"] > df["SMA_50"]) &
    (df["Close"] > df["SMA_200"])
)

signal_df = df[signal]


# --------------------------------------------------
# 5. SIGNAL PERFORMANCE
# --------------------------------------------------

signal_return = (
    signal_df["Forward_20D_Return"].mean()
)

signal_positive_rate = (
    signal_df["Forward_20D_Return"] > 0
).mean()


# --------------------------------------------------
# 6. DIFFERENCE
# --------------------------------------------------

return_difference = (
    signal_return -
    baseline_return
)

positive_rate_difference = (
    signal_positive_rate -
    baseline_positive_rate
)


# --------------------------------------------------
# 7. OUTPUT
# --------------------------------------------------

print("\nUNCONDITIONAL BASELINE")
print("-" * 40)

print(
    f"Observations: "
    f"{len(df)}"
)

print(
    f"Average 20D return: "
    f"{baseline_return:.4%}"
)

print(
    f"Positive 20D rate: "
    f"{baseline_positive_rate:.2%}"
)


print("\nMOMENTUM CONDITION")
print("-" * 40)

print(
    f"Signal observations: "
    f"{len(signal_df)}"
)

print(
    f"Average 20D return: "
    f"{signal_return:.4%}"
)

print(
    f"Positive 20D rate: "
    f"{signal_positive_rate:.2%}"
)


print("\nINCREMENTAL DIFFERENCE")
print("-" * 40)

print(
    f"Return difference: "
    f"{return_difference:.4%}"
)

print(
    f"Positive-rate difference: "
    f"{positive_rate_difference:.2%}"
)


print("\n" + "=" * 60)
print("BENCHMARK ANALYSIS COMPLETE")
print("=" * 60)