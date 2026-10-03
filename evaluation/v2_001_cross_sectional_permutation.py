import pandas as pd
import numpy as np


INPUT_FILE = "data/processed/relative_strength_features.csv"

N_PERMUTATIONS = 10_000
RANDOM_SEED = 42


print("=" * 90)
print("V2-001 CROSS-SECTIONAL PERMUTATION TEST")
print("=" * 90)


# ---------------------------------------------------------
# 1. Load relative-strength data
# ---------------------------------------------------------

df = pd.read_csv(
    INPUT_FILE,
    parse_dates=["Date"]
)

df = df.sort_values(["Date", "Stock"])


# ---------------------------------------------------------
# 2. Calculate forward 20D returns
# ---------------------------------------------------------

df["Forward_20D_Return"] = (
    df.groupby("Stock")["Stock_Close"].shift(-20)
    / df["Stock_Close"]
    - 1
)

df = df.dropna(
    subset=[
        "Relative_Return_20D",
        "Forward_20D_Return"
    ]
).copy()


# ---------------------------------------------------------
# 3. Rank relative strength within each date
# ---------------------------------------------------------

df["RS_Rank"] = (
    df.groupby("Date")["Relative_Return_20D"]
    .rank(
        ascending=False,
        method="first"
    )
)


# ---------------------------------------------------------
# 4. Convert data into Date x Stock return matrix
# ---------------------------------------------------------

return_matrix = (
    df.pivot(
        index="Date",
        columns="Stock",
        values="Forward_20D_Return"
    )
    .dropna()
)

dates = return_matrix.index
returns = return_matrix.to_numpy()

n_dates, n_stocks = returns.shape


print(f"\nEvaluation dates: {n_dates:,}")
print(f"Stocks per date: {n_stocks}")


# ---------------------------------------------------------
# 5. Observed Top-2 / Bottom-2 spread
# ---------------------------------------------------------

rank_matrix = (
    df.pivot(
        index="Date",
        columns="Stock",
        values="RS_Rank"
    )
    .loc[dates]
    .to_numpy()
)

top_mask = rank_matrix <= 2
bottom_mask = rank_matrix >= 4

top_returns = (
    np.where(top_mask, returns, np.nan)
)

bottom_returns = (
    np.where(bottom_mask, returns, np.nan)
)

top_2 = np.nanmean(top_returns, axis=1)
bottom_2 = np.nanmean(bottom_returns, axis=1)

daily_spread = top_2 - bottom_2

observed_spread = daily_spread.mean()


print(
    f"Observed top-minus-bottom spread: "
    f"{observed_spread:.4%}"
)


# ---------------------------------------------------------
# 6. Permutation test
# ---------------------------------------------------------

print(
    f"\nRunning {N_PERMUTATIONS:,} permutations..."
)

rng = np.random.default_rng(RANDOM_SEED)

permutation_spreads = np.empty(N_PERMUTATIONS)


for i in range(N_PERMUTATIONS):

    # Randomly assign ranks independently within each date.
    random_keys = rng.random(
        (n_dates, n_stocks)
    )

    random_ranks = np.argsort(
        np.argsort(
            random_keys,
            axis=1
        ),
        axis=1
    )

    # Lowest random rank = Top 2
    random_top = (
        random_ranks < 2
    )

    # Highest random rank = Bottom 2
    random_bottom = (
        random_ranks >= n_stocks - 2
    )

    random_top_returns = np.where(
        random_top,
        returns,
        np.nan
    )

    random_bottom_returns = np.where(
        random_bottom,
        returns,
        np.nan
    )

    random_top_mean = np.nanmean(
        random_top_returns,
        axis=1
    )

    random_bottom_mean = np.nanmean(
        random_bottom_returns,
        axis=1
    )

    permutation_spreads[i] = (
        random_top_mean
        - random_bottom_mean
    ).mean()


# ---------------------------------------------------------
# 7. Two-sided permutation p-value
# ---------------------------------------------------------

p_value = (
    np.sum(
        np.abs(permutation_spreads)
        >= abs(observed_spread)
    )
    + 1
) / (N_PERMUTATIONS + 1)


# ---------------------------------------------------------
# 8. Null distribution interval
# ---------------------------------------------------------

lower = np.percentile(
    permutation_spreads,
    2.5
)

upper = np.percentile(
    permutation_spreads,
    97.5
)


# ---------------------------------------------------------
# 9. Results
# ---------------------------------------------------------

print("\n" + "=" * 90)
print("PERMUTATION RESULTS")
print("=" * 90)

print(
    f"Observed spread:       "
    f"{observed_spread:.4%}"
)

print(
    f"Permutation mean:      "
    f"{permutation_spreads.mean():.4%}"
)

print(
    f"Permutation std:       "
    f"{permutation_spreads.std():.4%}"
)

print(
    f"95% null interval:     "
    f"[{lower:.4%}, {upper:.4%}]"
)

print(
    f"Two-sided p-value:     "
    f"{p_value:.4f}"
)


# ---------------------------------------------------------
# 10. Save results
# ---------------------------------------------------------

result = pd.DataFrame({
    "Observed_Spread": [observed_spread],
    "Permutation_Mean": [
        permutation_spreads.mean()
    ],
    "Permutation_Std": [
        permutation_spreads.std()
    ],
    "Null_95_Lower": [lower],
    "Null_95_Upper": [upper],
    "P_Value": [p_value],
    "N_Permutations": [N_PERMUTATIONS],
})


output_file = (
    "data/processed/"
    "v2_001_cross_sectional_permutation.csv"
)

result.to_csv(
    output_file,
    index=False
)


print("\nSaved:")
print(output_file)

print("\n" + "=" * 90)
print("PERMUTATION TEST COMPLETE")
print("=" * 90)