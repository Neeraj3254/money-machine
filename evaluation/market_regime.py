import pandas as pd
import numpy as np
from pathlib import Path


INPUT_PATH = Path(
    "data/raw/nifty50_daily.csv"
)

OUTPUT_PATH = Path(
    "data/processed/nifty50_regimes.csv"
)


df = pd.read_csv(
    INPUT_PATH,
    index_col=0,
    parse_dates=True
)


df["Daily_Return"] = (
    df["Close"].pct_change()
)

df["Volatility_20D"] = (
    df["Daily_Return"]
    .rolling(20)
    .std()
)


df["Return_60D"] = (
    df["Close"]
    .pct_change(60)
)


vol_low = df["Volatility_20D"].quantile(0.33)
vol_high = df["Volatility_20D"].quantile(0.67)


def classify(row):

    if pd.isna(row["Volatility_20D"]):
        return "UNKNOWN"

    if row["Volatility_20D"] <= vol_low:

        if row["Return_60D"] > 0:
            return "LOW_VOL_UP"
        else:
            return "LOW_VOL_DOWN"

    elif row["Volatility_20D"] <= vol_high:

        if row["Return_60D"] > 0:
            return "MED_VOL_UP"
        else:
            return "MED_VOL_DOWN"

    else:

        if row["Return_60D"] > 0:
            return "HIGH_VOL_UP"
        else:
            return "HIGH_VOL_DOWN"


df["Market_Regime"] = df.apply(
    classify,
    axis=1
)


print("=" * 70)
print("NIFTY MARKET REGIME ENGINE")
print("=" * 70)

print("\nRegime counts:")
print(
    df["Market_Regime"]
    .value_counts()
)

print("\nVolatility thresholds:")
print(f"Low:  {vol_low:.4%}")
print(f"High: {vol_high:.4%}")


df.to_csv(OUTPUT_PATH)

print(f"\nSaved to: {OUTPUT_PATH}")

print("\n" + "=" * 70)
print("MARKET REGIME COMPLETE")
print("=" * 70)