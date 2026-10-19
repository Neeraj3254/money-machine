import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

TRADE_FILE = Path(
    "data/processed/stateful_portfolio_trades_cost_0_0010.csv"
)

REGIME_FILE = Path(
    "data/processed/nifty50_regimes_leakage_free.csv"
)

OUTPUT_FILE = Path(
    "data/processed/pooled_regime_effect.csv"
)

N_PERMUTATIONS = 10_000

RANDOM_SEED = 42


# ============================================================
# LOAD DATA
# ============================================================

trades = pd.read_csv(TRADE_FILE)
regimes = pd.read_csv(REGIME_FILE)


# ============================================================
# VALIDATE
# ============================================================

required_trade_columns = [
    "Entry_Date",
    "Return",
]

required_regime_columns = [
    "Date",
    "Market_Regime",
]

missing_trade = [
    c for c in required_trade_columns
    if c not in trades.columns
]

missing_regime = [
    c for c in required_regime_columns
    if c not in regimes.columns
]

if missing_trade:
    raise ValueError(
        f"Trade file is missing columns: {missing_trade}"
    )

if missing_regime:
    raise ValueError(
        f"Regime file is missing columns: {missing_regime}"
    )


# ============================================================
# NORMALIZE DATES
# ============================================================

trades["Entry_Date"] = pd.to_datetime(
    trades["Entry_Date"]
)

regimes["Date"] = pd.to_datetime(
    regimes["Date"]
)


# ============================================================
# JOIN LEAKAGE-FREE REGIME
# ============================================================

data = trades.merge(
    regimes[
        ["Date", "Market_Regime"]
    ],
    left_on="Entry_Date",
    right_on="Date",
    how="left",
)


# ============================================================
# KEEP VALID REGIMES ONLY
# ============================================================

data = data[
    data["Market_Regime"].notna()
    & (data["Market_Regime"] != "UNKNOWN")
].copy()


# ============================================================
# AGGREGATE TO DATE LEVEL
#
# Market regime is a market-wide variable.
# Therefore all trades on the same date remain one cluster.
# ============================================================

daily = (
    data
    .groupby("Entry_Date")
    .agg(
        Return_Sum=("Return", "sum"),
        Trade_Count=("Return", "count"),
        Market_Regime=("Market_Regime", "first"),
    )
    .reset_index()
)


# ============================================================
# ARRAYS
# ============================================================

date_returns = (
    daily["Return_Sum"].to_numpy()
)

date_counts = (
    daily["Trade_Count"].to_numpy()
)

original_labels = (
    daily["Market_Regime"].to_numpy()
)


unique_regimes = sorted(
    daily["Market_Regime"].unique()
)


total_dates = len(daily)

total_trades = int(
    date_counts.sum()
)


# ============================================================
# RANDOM NUMBER GENERATOR
# ============================================================

rng = np.random.default_rng(
    RANDOM_SEED
)


# ============================================================
# RESULTS
# ============================================================

results = []


# ============================================================
# TEST EACH REGIME
# ============================================================

for regime in unique_regimes:

    # --------------------------------------------------------
    # Observed regime mask
    # --------------------------------------------------------

    observed_mask = (
        original_labels == regime
    )

    other_mask = ~observed_mask


    # --------------------------------------------------------
    # Observed effect
    # --------------------------------------------------------

    regime_trades = int(
        date_counts[observed_mask].sum()
    )

    other_trades = int(
        date_counts[other_mask].sum()
    )

    regime_dates = int(
        observed_mask.sum()
    )

    other_dates = int(
        other_mask.sum()
    )


    regime_avg = (
        date_returns[observed_mask].sum()
        /
        regime_trades
    )

    other_avg = (
        date_returns[other_mask].sum()
        /
        other_trades
    )

    observed_effect = (
        regime_avg
        - other_avg
    )


    # --------------------------------------------------------
    # Evidence classification
    # --------------------------------------------------------

    if regime_trades < 10:
        evidence = "VERY LOW"

    elif regime_trades < 30:
        evidence = "LOW"

    elif regime_trades < 50:
        evidence = "PRELIMINARY"

    else:
        evidence = "REASONABLE"


    # --------------------------------------------------------
    # Date-clustered permutation test
    # --------------------------------------------------------

    permuted_effects = np.empty(
        N_PERMUTATIONS
    )

    for i in range(N_PERMUTATIONS):

        shuffled_labels = rng.permutation(
            original_labels
        )

        mask = (
            shuffled_labels == regime
        )

        selected_count = int(
            date_counts[mask].sum()
        )

        remaining_count = int(
            date_counts[~mask].sum()
        )

        if (
            selected_count == 0
            or remaining_count == 0
        ):

            permuted_effects[i] = np.nan

            continue


        selected_avg = (
            date_returns[mask].sum()
            /
            selected_count
        )

        remaining_avg = (
            date_returns[~mask].sum()
            /
            remaining_count
        )

        permuted_effects[i] = (
            selected_avg
            - remaining_avg
        )


    # --------------------------------------------------------
    # Remove invalid permutations
    # --------------------------------------------------------

    permuted_effects = (
        permuted_effects[
            np.isfinite(permuted_effects)
        ]
    )


    # --------------------------------------------------------
    # Two-sided permutation p-value
    # --------------------------------------------------------

    extreme_count = np.sum(
        np.abs(permuted_effects)
        >= abs(observed_effect)
    )

    p_value = (
        extreme_count + 1
    ) / (
        len(permuted_effects) + 1
    )


    # --------------------------------------------------------
    # Null distribution
    # --------------------------------------------------------

    null_mean = (
        np.mean(permuted_effects)
    )

    null_q025 = (
        np.quantile(
            permuted_effects,
            0.025
        )
    )

    null_q975 = (
        np.quantile(
            permuted_effects,
            0.975
        )
    )


    # --------------------------------------------------------
    # Save result
    # --------------------------------------------------------

    results.append(
        {
            "Market_Regime": regime,
            "Trades": regime_trades,
            "Other_Trades": other_trades,
            "Regime_Dates": regime_dates,
            "Other_Dates": other_dates,
            "Total_Dates": total_dates,
            "Observed_Avg_Return": regime_avg,
            "Other_Avg_Return": other_avg,
            "Observed_Effect": observed_effect,
            "Null_Mean": null_mean,
            "Null_Q025": null_q025,
            "Null_Q975": null_q975,
            "Permutation_P_Value": p_value,
            "Evidence": evidence,
        }
    )

    print(
        f"Completed: {regime} | "
        f"{N_PERMUTATIONS:,} permutations"
    )


# ============================================================
# CREATE OUTPUT
# ============================================================

summary = pd.DataFrame(results)


# ============================================================
# MULTIPLE-COMPARISON CONTROL
# ============================================================

m = len(summary)

summary["Bonferroni_Adjusted_P"] = (
    summary["Permutation_P_Value"] * m
).clip(
    upper=1.0
)


# ============================================================
# DISPLAY
# ============================================================

print("\n" + "=" * 115)
print("POOLED LEAKAGE-FREE REGIME EFFECT")
print("=" * 115)

print(
    f"\nValid portfolio trades: {total_trades}"
)

print(
    f"Unique entry dates: {total_dates}"
)

print(
    f"Regimes tested: {m}"
)

print(
    f"Permutations per regime: "
    f"{N_PERMUTATIONS:,}"
)

print(
    "\nRandomization unit: Entry_Date"
)

print(
    "\nObserved Effect = "
    "Regime Average Return - Other-Regime Average Return"
)

print("\n")


display_columns = [
    "Market_Regime",
    "Trades",
    "Regime_Dates",
    "Observed_Avg_Return",
    "Other_Avg_Return",
    "Observed_Effect",
    "Null_Q025",
    "Null_Q975",
    "Permutation_P_Value",
    "Bonferroni_Adjusted_P",
    "Evidence",
]


print(
    summary[
        display_columns
    ].to_string(
        index=False,
        formatters={
            "Observed_Avg_Return":
                lambda x: f"{x:.2%}",

            "Other_Avg_Return":
                lambda x: f"{x:.2%}",

            "Observed_Effect":
                lambda x: f"{x:.2%}",

            "Null_Q025":
                lambda x: f"{x:.2%}",

            "Null_Q975":
                lambda x: f"{x:.2%}",

            "Permutation_P_Value":
                lambda x: f"{x:.4f}",

            "Bonferroni_Adjusted_P":
                lambda x: f"{x:.4f}",
        },
    )
)


# ============================================================
# SAVE
# ============================================================

summary.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\nSaved:")
print(OUTPUT_FILE)

print("\n" + "=" * 115)
print("POOLED REGIME EFFECT COMPLETE")
print("=" * 115)