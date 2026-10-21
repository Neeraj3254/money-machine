import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_PATH = Path(
    "data/raw/nifty50_daily.csv"
)

OUTPUT_PATH = Path(
    "data/processed/nifty50_regimes_leakage_free.csv"
)

MIN_HISTORY = 252


# ============================================================
# LOAD RAW NIFTY DATA
# ============================================================

df = pd.read_csv(
    INPUT_PATH,
    parse_dates=["Date"]
)

df = df.sort_values("Date").reset_index(drop=True)


# ============================================================
# CALCULATE MARKET FEATURES
# ============================================================

df["Daily_Return"] = (
    df["Close"].pct_change()
)

df["Volatility_20D"] = (
    df["Daily_Return"]
    .rolling(20)
    .std()
)

df["Return_60D"] = (
    df["Close"].pct_change(60)
)


# ============================================================
# LEAKAGE-FREE REGIME CLASSIFICATION
# ============================================================

regimes = []
low_thresholds = []
high_thresholds = []
history_counts = []


for i in range(len(df)):

    current_vol = df.loc[i, "Volatility_20D"]
    current_return = df.loc[i, "Return_60D"]

    # --------------------------------------------------------
    # Not enough data to calculate today's features
    # --------------------------------------------------------

    if pd.isna(current_vol) or pd.isna(current_return):

        regimes.append("UNKNOWN")
        low_thresholds.append(np.nan)
        high_thresholds.append(np.nan)
        history_counts.append(0)

        continue

    # --------------------------------------------------------
    # Use ONLY observations BEFORE today's date
    # --------------------------------------------------------

    historical_vol = (
        df.loc[:i - 1, "Volatility_20D"]
        .dropna()
    )

    history_count = len(historical_vol)

    history_counts.append(history_count)

    # --------------------------------------------------------
    # Require minimum historical sample
    # --------------------------------------------------------

    if history_count < MIN_HISTORY:

        regimes.append("UNKNOWN")
        low_thresholds.append(np.nan)
        high_thresholds.append(np.nan)

        continue

    # --------------------------------------------------------
    # Calculate thresholds using PAST data only
    # --------------------------------------------------------

    vol_low = historical_vol.quantile(0.33)
    vol_high = historical_vol.quantile(0.67)

    low_thresholds.append(vol_low)
    high_thresholds.append(vol_high)

    # --------------------------------------------------------
    # Preserve original regime logic
    # --------------------------------------------------------

    if current_vol <= vol_low:

        if current_return > 0:
            regime = "LOW_VOL_UP"
        else:
            regime = "LOW_VOL_DOWN"

    elif current_vol <= vol_high:

        if current_return > 0:
            regime = "MED_VOL_UP"
        else:
            regime = "MED_VOL_DOWN"

    else:

        if current_return > 0:
            regime = "HIGH_VOL_UP"
        else:
            regime = "HIGH_VOL_DOWN"

    regimes.append(regime)


# ============================================================
# STORE RESULTS
# ============================================================

df["Market_Regime"] = regimes

df["Vol_Low_Threshold"] = low_thresholds

df["Vol_High_Threshold"] = high_thresholds

df["Historical_Vol_Observations"] = history_counts


# ============================================================
# VALIDATION
# ============================================================

print("=" * 70)
print("LEAKAGE-FREE NIFTY MARKET REGIME ENGINE")
print("=" * 70)

print("\nRows:", len(df))

print("\nDate range:")
print(
    df["Date"].iloc[0],
    "to",
    df["Date"].iloc[-1]
)

print("\nRegime counts:")
print(
    df["Market_Regime"]
    .value_counts()
)

print("\nMinimum historical observations:")
print(MIN_HISTORY)

print("\nFirst valid regime date:")

valid_dates = df.loc[
    df["Market_Regime"] != "UNKNOWN",
    "Date"
]

if len(valid_dates) > 0:
    print(valid_dates.iloc[0])
else:
    print("None")


# ============================================================
# SAVE
# ============================================================

df.to_csv(
    OUTPUT_PATH,
    index=False
)

print("\nSaved:")
print(OUTPUT_PATH)

print("\n" + "=" * 70)
print("LEAKAGE-FREE REGIME COMPLETE")
print("=" * 70)