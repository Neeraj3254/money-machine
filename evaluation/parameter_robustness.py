import pandas as pd
import numpy as np

INPUT_PATH = "data/processed/reliance_features.csv"

print("=" * 60)
print("PARAMETER ROBUSTNESS v0.1")
print("=" * 60)

df = pd.read_csv(
    INPUT_PATH,
    index_col=0,
    parse_dates=True
)

# --------------------------------------------------
# TEST PARAMETER COMBINATIONS
# --------------------------------------------------

momentum_periods = [10, 20, 30]
fast_periods = [20, 30, 50]
slow_periods = [100, 150, 200]

results = []

# --------------------------------------------------
# TEST EACH COMBINATION
# --------------------------------------------------

for momentum in momentum_periods:

    for fast in fast_periods:

        for slow in slow_periods:

            # Prevent nonsensical ordering
            if fast >= slow:
                continue

            temp = df.copy()

            temp["Momentum"] = (
                temp["Close"].pct_change(momentum)
            )

            temp["Fast_SMA"] = (
                temp["Close"]
                .rolling(fast)
                .mean()
            )

            temp["Slow_SMA"] = (
                temp["Close"]
                .rolling(slow)
                .mean()
            )

            temp["Signal"] = (
                (temp["Momentum"] > 0) &
                (temp["Fast_SMA"] > temp["Slow_SMA"]) &
                (temp["Close"] > temp["Slow_SMA"])
            )

            temp["Position"] = (
                temp["Signal"]
                .shift(1)
                .fillna(False)
                .astype(bool)
            )

            temp["Strategy_Return"] = (
                temp["Position"] *
                temp["Daily_Return"]
            )

            equity = (
                1 + temp["Strategy_Return"]
            ).cumprod()

            total_return = (
                equity.iloc[-1] - 1
            )

            volatility = (
                temp["Strategy_Return"].std()
                * np.sqrt(252)
            )

            peak = equity.cummax()

            drawdown = (
                equity / peak
            ) - 1

            max_drawdown = drawdown.min()

            results.append({
                "Momentum": momentum,
                "Fast_SMA": fast,
                "Slow_SMA": slow,
                "Return": total_return,
                "Volatility": volatility,
                "Max_Drawdown": max_drawdown
            })

# --------------------------------------------------
# RESULTS
# --------------------------------------------------

results_df = pd.DataFrame(results)

print("\nPARAMETER RESULTS")
print("-" * 60)

print(
    results_df
    .sort_values("Return", ascending=False)
    .to_string(index=False)
)

# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

print("\nSUMMARY")
print("-" * 60)

print(
    f"Combinations tested: "
    f"{len(results_df)}"
)

print(
    f"Median return: "
    f"{results_df['Return'].median():.2%}"
)

print(
    f"Minimum return: "
    f"{results_df['Return'].min():.2%}"
)

print(
    f"Maximum return: "
    f"{results_df['Return'].max():.2%}"
)

print(
    f"Median max drawdown: "
    f"{results_df['Max_Drawdown'].median():.2%}"
)

results_df.to_csv(
    "data/processed/parameter_robustness.csv",
    index=False
)

print(
    "\nSaved to: "
    "data/processed/parameter_robustness.csv"
)

print("\n" + "=" * 60)
print("PARAMETER ROBUSTNESS COMPLETE")
print("=" * 60)