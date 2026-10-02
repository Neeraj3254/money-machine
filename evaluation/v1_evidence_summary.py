import pandas as pd
from pathlib import Path


DATA_DIR = Path("data/processed")


cross = pd.read_csv(
    DATA_DIR / "multi_stock_validation.csv"
)

stats = pd.read_csv(
    DATA_DIR / "statistical_test.csv"
)

costs = pd.read_csv(
    DATA_DIR / "cost_sensitivity.csv"
)

walk = pd.read_csv(
    DATA_DIR / "walk_forward.csv"
)


print("=" * 80)
print("V1 EVIDENCE SUMMARY")
print("=" * 80)


# ------------------------------------------------
# CROSS STOCK
# ------------------------------------------------

positive_cross = (
    cross["Return_Difference"] > 0
).sum()

negative_cross = (
    cross["Return_Difference"] < 0
).sum()


# ------------------------------------------------
# BOOTSTRAP
# ------------------------------------------------

zero_containing = (
    stats["CI_Contains_Zero"]
).sum()


# ------------------------------------------------
# COST
# ------------------------------------------------

one_percent_row = costs[
    costs["Cost_Per_Trade"] == 0.01
]

if not one_percent_row.empty:

    expectancy_at_1pct = (
        one_percent_row[
            "Expectancy"
        ].iloc[0]
    )

else:

    expectancy_at_1pct = None


# ------------------------------------------------
# WALK FORWARD
# ------------------------------------------------

negative_periods = (
    walk["Mean_Return"] < 0
).sum()

total_periods = len(walk)


print("\nCross-stock evidence")
print("-" * 40)

print(
    f"Positive differences: "
    f"{positive_cross}"
)

print(
    f"Negative differences: "
    f"{negative_cross}"
)


print("\nBootstrap evidence")
print("-" * 40)

print(
    f"Confidence intervals containing zero: "
    f"{zero_containing}/{len(stats)}"
)


print("\nCost sensitivity")
print("-" * 40)

if expectancy_at_1pct is not None:

    print(
        f"Expectancy at 1% modeled cost: "
        f"{expectancy_at_1pct:.4%}"
    )


print("\nWalk-forward")
print("-" * 40)

print(
    f"Negative periods: "
    f"{negative_periods}/{total_periods}"
)


print("\n" + "=" * 80)
print("EVIDENCE STATUS")
print("=" * 80)

print(
    """
V1 STATUS: NOT VALIDATED AS A ROBUST GENERAL EDGE

Reasons:

1. Cross-stock results are inconsistent across
   evaluation methodologies.

2. Most bootstrap intervals include zero.

3. Performance varies substantially by time period.

4. Parameter robustness showed large dispersion.

5. Transaction costs materially reduce expectancy.

6. Execution assumptions materially change results.

7. Market and volatility regimes appear relevant.

Therefore:

DO NOT deploy V1 as a live trading strategy.

Use V1 as a research baseline and failure case.
"""
)

print("=" * 80)
print("EVIDENCE SUMMARY COMPLETE")
print("=" * 80)