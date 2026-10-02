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
    / "portfolio_signals.csv"
)

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "portfolio_allocations.csv"
)

INITIAL_CAPITAL = 100_000

MAX_POSITION_WEIGHT = 0.30
MAX_TOTAL_EXPOSURE = 1.00


# ============================================================
# LOAD SIGNALS
# ============================================================

df = pd.read_csv(
    INPUT_FILE,
    parse_dates=["Date"]
)

df = df.sort_values(
    ["Date", "Stock"]
).reset_index(drop=True)


# ============================================================
# ACTIVE SIGNALS
# ============================================================

df["Active_Signals"] = (
    df.groupby("Date")["Signal"]
    .transform("sum")
)


# ============================================================
# EQUAL-WEIGHT ALLOCATION
# ============================================================

df["Raw_Weight"] = 0.0

active = df["Signal"]

df.loc[active, "Raw_Weight"] = (
    1.0 / df.loc[active, "Active_Signals"]
)


# ============================================================
# POSITION CAP
# ============================================================

df["Position_Weight"] = (
    df["Raw_Weight"]
    .clip(upper=MAX_POSITION_WEIGHT)
)


# ============================================================
# TOTAL EXPOSURE
# ============================================================

daily_exposure = (
    df.groupby("Date")["Position_Weight"]
    .sum()
)

exposure_scale = (
    MAX_TOTAL_EXPOSURE
    / daily_exposure.clip(lower=MAX_TOTAL_EXPOSURE)
)

df["Exposure_Scale"] = (
    df["Date"]
    .map(exposure_scale)
)

df["Final_Weight"] = (
    df["Position_Weight"]
    * df["Exposure_Scale"]
)


# ============================================================
# CAPITAL ALLOCATION
# ============================================================

df["Allocated_Capital"] = (
    INITIAL_CAPITAL
    * df["Final_Weight"]
)


# ============================================================
# OUTPUT
# ============================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

daily = (
    df.groupby("Date")
    .agg(
        Active_Signals=("Signal", "sum"),
        Total_Exposure=("Final_Weight", "sum"),
    )
)

print("=" * 70)
print("POSITION SIZING ENGINE")
print("=" * 70)

print(f"Initial capital: ₹{INITIAL_CAPITAL:,.2f}")
print(f"Max position weight: {MAX_POSITION_WEIGHT:.0%}")
print(f"Max total exposure: {MAX_TOTAL_EXPOSURE:.0%}")
print()

print(
    f"Average active signals: "
    f"{daily['Active_Signals'].mean():.2f}"
)

print(
    f"Maximum active signals: "
    f"{daily['Active_Signals'].max():.0f}"
)

print(
    f"Average exposure: "
    f"{daily['Total_Exposure'].mean():.2%}"
)

print(
    f"Maximum exposure: "
    f"{daily['Total_Exposure'].max():.2%}"
)

print()

print(f"Saved: {OUTPUT_FILE}")