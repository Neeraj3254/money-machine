import pandas as pd
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "strategy_market_regime.csv"
)


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(INPUT_FILE)


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

required_columns = [
    "Stock",
    "Market_Regime",
    "Observations",
    "Average_Return",
    "Median_Return",
    "Positive_Rate",
]

missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )


# ============================================================
# CLASSIFY EVIDENCE
# ============================================================

def classify_sample_size(n):
    if n < 10:
        return "VERY LOW"
    elif n < 30:
        return "LOW"
    elif n < 50:
        return "PRELIMINARY"
    else:
        return "REASONABLE"


df["Evidence_Level"] = (
    df["Observations"]
    .apply(classify_sample_size)
)


# ============================================================
# DISPLAY RESULTS
# ============================================================

print("=" * 75)
print("REGIME SAMPLE SIZE CHECK")
print("=" * 75)

print()

print(
    df[
        [
            "Stock",
            "Market_Regime",
            "Observations",
            "Evidence_Level",
        ]
    ].to_string(index=False)
)

print()

print("=" * 75)
print("EVIDENCE RULE")
print("=" * 75)

print("<10   = VERY LOW")
print("10-29 = LOW")
print("30-49 = PRELIMINARY")
print("50+   = REASONABLE")

print("=" * 75)