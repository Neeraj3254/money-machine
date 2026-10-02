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
    "data/processed/regime_effect_bootstrap.csv"
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
# JOIN LEAKAGE-FREE REGIMES
# ============================================================

data = trades.merge(
    regimes[["Date", "Market_Regime"]],
    left_on="Entry_Date",
    right_on="Date",
    how="left",
)


# ============================================================
# REMOVE UNKNOWN REGIMES
# ============================================================

data = data[
    data["Market_Regime"].notna()
    & (data["Market_Regime"] != "UNKNOWN")
].copy()


# ============================================================
# ASSIGN TIME PERIOD
# ============================================================

def assign_period(date):

    year = date.year

    if 2020 <= year <= 2021:
        return "2020-2021"

    if 2022 <= year <= 2023:
        return "2022-2023"

    if 2024 <= year <= 2025:
        return "2024-2025"

    return "OUTSIDE_TEST"


data["Period"] = data["Entry_Date"].apply(
    assign_period
)

data = data[
    data["Period"] != "OUTSIDE_TEST"
].copy()


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
# PROCESS EACH PERIOD
# ============================================================

for period in sorted(data["Period"].unique()):

    period_data = data[
        data["Period"] == period
    ].copy()

    # --------------------------------------------------------
    # Aggregate to DATE level.
    #
    # This is the key efficiency improvement.
    #
    # All trades on the same date remain one cluster.
    # --------------------------------------------------------

    daily = (
        period_data
        .groupby("Entry_Date")
        .agg(
            Return_Sum=("Return", "sum"),
            Trade_Count=("Return", "count"),
            Market_Regime=("Market_Regime", "first"),
        )
        .reset_index()
    )

    date_returns = (
        daily["Return_Sum"]
        .to_numpy()
    )

    date_counts = (
        daily["Trade_Count"]
        .to_numpy()
    )

    original_labels = (
        daily["Market_Regime"]
        .to_numpy()
    )

    unique_regimes = sorted(
        daily["Market_Regime"].unique()
    )

    total_return = date_returns.sum()
    total_trades = date_counts.sum()

    total_dates = len(daily)

    # --------------------------------------------------------
    # Each regime is tested separately.
    # --------------------------------------------------------

    for regime in unique_regimes:

        observed_mask = (
            original_labels == regime
        )

        observed_return = (
            date_returns[observed_mask].sum()
            /
            date_counts[observed_mask].sum()
        )

        other_mask = ~observed_mask

        other_return = (
            date_returns[other_mask].sum()
            /
            date_counts[other_mask].sum()
        )

        observed_effect = (
            observed_return
            - other_return
        )

        regime_trades = int(
            date_counts[observed_mask].sum()
        )

        other_trades = int(
            date_counts[other_mask].sum()
        )

        regime_dates = int(
            observed_mask.sum()
        )

        # ----------------------------------------------------
        # Evidence classification
        # ----------------------------------------------------

        if regime_trades < 10:
            evidence = "VERY LOW"

        elif regime_trades < 30:
            evidence = "LOW"

        elif regime_trades < 50:
            evidence = "PRELIMINARY"

        else:
            evidence = "REASONABLE"

        # ----------------------------------------------------
        # Permutation test
        #
        # Regime labels are shuffled across DATE clusters.
        # Trade outcomes remain attached to their dates.
        # ----------------------------------------------------

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

            selected_count = (
                date_counts[mask].sum()
            )

            other_count = (
                date_counts[~mask].sum()
            )

            # This should normally never happen.
            if selected_count == 0 or other_count == 0:

                permuted_effects[i] = np.nan

                continue

            selected_return = (
                date_returns[mask].sum()
                /
                selected_count
            )

            shuffled_other_return = (
                date_returns[~mask].sum()
                /
                other_count
            )

            permuted_effects[i] = (
                selected_return
                - shuffled_other_return
            )

        # ----------------------------------------------------
        # Remove invalid values
        # ----------------------------------------------------

        permuted_effects = (
            permuted_effects[
                np.isfinite(permuted_effects)
            ]
        )

        # ----------------------------------------------------
        # Two-sided permutation p-value
        # ----------------------------------------------------

        extreme_count = np.sum(
            np.abs(permuted_effects)
            >= abs(observed_effect)
        )

        p_value = (
            extreme_count + 1
        ) / (
            len(permuted_effects) + 1
        )

        # ----------------------------------------------------
        # Null distribution
        # ----------------------------------------------------

        null_mean = (
            np.mean(permuted_effects)
        )

        null_std = (
            np.std(permuted_effects)
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

        # ----------------------------------------------------
        # Save result
        # ----------------------------------------------------

        results.append(
            {
                "Period": period,
                "Market_Regime": regime,
                "Trades": regime_trades,
                "Other_Trades": other_trades,
                "Regime_Dates": regime_dates,
                "Total_Dates": total_dates,
                "Observed_Effect": observed_effect,
                "Null_Mean": null_mean,
                "Null_Std": null_std,
                "Null_Q025": null_q025,
                "Null_Q975": null_q975,
                "Permutation_P_Value": p_value,
                "Evidence": evidence,
            }
        )

        print(
            f"Completed: {period} | "
            f"{regime} | "
            f"{N_PERMUTATIONS:,} permutations"
        )


# ============================================================
# CREATE OUTPUT
# ============================================================

summary = pd.DataFrame(results)


# ============================================================
# DISPLAY
# ============================================================

print("\n" + "=" * 110)
print("DATE-CLUSTERED REGIME EFFECT PERMUTATION TEST")
print("=" * 110)

print(
    f"\nPermutations per Period × Regime: "
    f"{N_PERMUTATIONS:,}"
)

print(
    "Randomization unit: Entry_Date"
)

print(
    "\nObserved Effect = "
    "Regime Average Return - Other-Regime Average Return"
)

print("\n")

print(
    summary[
        [
            "Period",
            "Market_Regime",
            "Trades",
            "Regime_Dates",
            "Observed_Effect",
            "Null_Q025",
            "Null_Q975",
            "Permutation_P_Value",
            "Evidence",
        ]
    ].to_string(
        index=False,
        formatters={
            "Observed_Effect":
                lambda x: f"{x:.2%}",

            "Null_Q025":
                lambda x: f"{x:.2%}",

            "Null_Q975":
                lambda x: f"{x:.2%}",

            "Permutation_P_Value":
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

print("\n" + "=" * 110)
print("PERMUTATION TEST COMPLETE")
print("=" * 110)