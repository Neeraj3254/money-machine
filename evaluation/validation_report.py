import pandas as pd
from pathlib import Path


DATA_DIR = Path("data/processed")


print("=" * 80)
print("MONEY MACHINE — VALIDATION REPORT")
print("=" * 80)


# --------------------------------------------------
# CROSS STOCK
# --------------------------------------------------

cross = pd.read_csv(
    DATA_DIR / "multi_stock_validation.csv"
)

print("\n1. CROSS-STOCK VALIDATION")
print("-" * 80)

print(
    cross[
        [
            "Stock",
            "Return_Difference",
            "Positive_Rate_Difference"
        ]
    ].round(4).to_string(index=False)
)


# --------------------------------------------------
# STATISTICAL TEST
# --------------------------------------------------

stats = pd.read_csv(
    DATA_DIR / "statistical_test.csv"
)

print("\n2. BOOTSTRAP TEST")
print("-" * 80)

print(
    stats[
        [
            "Stock",
            "Observed_Difference",
            "CI_Lower",
            "CI_Upper",
            "CI_Contains_Zero"
        ]
    ].round(4).to_string(index=False)
)


# --------------------------------------------------
# EXPECTANCY
# --------------------------------------------------

expectancy = pd.read_csv(
    DATA_DIR / "expectancy_analysis.csv"
)

print("\n3. EXPECTANCY")
print("-" * 80)

print(
    expectancy[
        [
            "Stock",
            "Win_Rate",
            "Average_Win",
            "Average_Loss",
            "Expectancy",
            "Profit_Factor"
        ]
    ].round(4).to_string(index=False)
)


# --------------------------------------------------
# COSTS
# --------------------------------------------------

costs = pd.read_csv(
    DATA_DIR / "cost_sensitivity.csv"
)

print("\n4. COST SENSITIVITY")
print("-" * 80)

print(
    costs.round(4).to_string(index=False)
)


# --------------------------------------------------
# EXECUTION
# --------------------------------------------------

execution = pd.read_csv(
    DATA_DIR / "execution_model.csv"
)

print("\n5. NEXT-OPEN EXECUTION")
print("-" * 80)

print(
    execution[
        [
            "Stock",
            "Average_Return",
            "Median_Return",
            "Win_Rate"
        ]
    ].round(4).to_string(index=False)
)


# --------------------------------------------------
# WALK FORWARD
# --------------------------------------------------

walk = pd.read_csv(
    DATA_DIR / "walk_forward.csv"
)

print("\n6. WALK-FORWARD")
print("-" * 80)

print(
    walk[
        [
            "Stock",
            "Period",
            "Mean_Return",
            "Median_Return",
            "Win_Rate"
        ]
    ].round(4).to_string(index=False)
)


print("\n" + "=" * 80)
print("VALIDATION REPORT COMPLETE")
print("=" * 80)