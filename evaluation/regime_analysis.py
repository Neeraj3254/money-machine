import pandas as pd
import numpy as np

INPUT_PATH = "data/processed/reliance_features.csv"

print("=" * 60)
print("REGIME ANALYSIS v0.1")
print("=" * 60)

df = pd.read_csv(
    INPUT_PATH,
    index_col=0,
    parse_dates=True
)

# --------------------------------------------------
# 1. STRATEGY SIGNAL
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
# 2. VOLATILITY REGIME
# --------------------------------------------------

# Use rolling volatility known at that point in time.
df["Volatility"] = (
    df["Daily_Return"]
    .rolling(20)
    .std()
)

# Remove rows without volatility
df = df.dropna(
    subset=["Volatility"]
)

# --------------------------------------------------
# 3. DEFINE REGIMES
# --------------------------------------------------

low_threshold = df["Volatility"].quantile(0.33)

high_threshold = df["Volatility"].quantile(0.67)

def classify_regime(vol):

    if vol <= low_threshold:
        return "LOW"

    elif vol <= high_threshold:
        return "MEDIUM"

    else:
        return "HIGH"

df["Regime"] = (
    df["Volatility"]
    .apply(classify_regime)
)

# --------------------------------------------------
# 4. ANALYZE EACH REGIME
# --------------------------------------------------

results = []

for regime in ["LOW", "MEDIUM", "HIGH"]:

    subset = df[
        df["Regime"] == regime
    ]

    returns = subset["Strategy_Return"]

    equity = (
        1 + returns
    ).cumprod()

    total_return = (
        equity.iloc[-1] - 1
    )

    volatility = (
        returns.std() *
        np.sqrt(252)
    )

    peak = equity.cummax()

    drawdown = (
        equity / peak
    ) - 1

    max_drawdown = drawdown.min()

    active_days = (
        subset["Position"].sum()
    )

    results.append({
        "Regime": regime,
        "Days": len(subset),
        "Active_Days": active_days,
        "Return": total_return,
        "Volatility": volatility,
        "Max_Drawdown": max_drawdown
    })

# --------------------------------------------------
# 5. OUTPUT
# --------------------------------------------------

results_df = pd.DataFrame(results)

print("\nVOLATILITY THRESHOLDS")
print("-" * 40)

print(
    f"Low threshold: "
    f"{low_threshold:.4%}"
)

print(
    f"High threshold: "
    f"{high_threshold:.4%}"
)

print("\nREGIME RESULTS")
print("-" * 60)

print(
    results_df.to_string(
        index=False
    )
)

results_df.to_csv(
    "data/processed/regime_analysis.csv",
    index=False
)

print(
    "\nSaved to: "
    "data/processed/regime_analysis.csv"
)

print("\n" + "=" * 60)
print("REGIME ANALYSIS COMPLETE")
print("=" * 60)