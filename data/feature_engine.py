import pandas as pd
import numpy as np

INPUT_PATH = "data/processed/reliance_returns.csv"
OUTPUT_PATH = "data/processed/reliance_features.csv"

print("=" * 60)
print("FEATURE ENGINE v0.1")
print("=" * 60)

# --------------------------------------------------
# 1. LOAD DATA
# --------------------------------------------------

df = pd.read_csv(
    INPUT_PATH,
    index_col=0,
    parse_dates=True
)

print(f"\nRows loaded: {len(df)}")

# --------------------------------------------------
# 2. MOMENTUM
# --------------------------------------------------

df["Return_5D"] = df["Close"].pct_change(5)

df["Return_20D"] = df["Close"].pct_change(20)

df["Return_60D"] = df["Close"].pct_change(60)

# --------------------------------------------------
# 3. MOVING AVERAGES
# --------------------------------------------------

df["SMA_20"] = df["Close"].rolling(20).mean()

df["SMA_50"] = df["Close"].rolling(50).mean()

df["SMA_200"] = df["Close"].rolling(200).mean()

# --------------------------------------------------
# 4. PRICE VS MOVING AVERAGE
# --------------------------------------------------

df["Price_vs_SMA20"] = (
    df["Close"] / df["SMA_20"]
) - 1

df["Price_vs_SMA50"] = (
    df["Close"] / df["SMA_50"]
) - 1

df["Price_vs_SMA200"] = (
    df["Close"] / df["SMA_200"]
) - 1

# --------------------------------------------------
# 5. VOLATILITY
# --------------------------------------------------

df["Volatility_20D"] = (
    df["Daily_Return"]
    .rolling(20)
    .std()
    * np.sqrt(252)
)

df["Volatility_60D"] = (
    df["Daily_Return"]
    .rolling(60)
    .std()
    * np.sqrt(252)
)

# --------------------------------------------------
# 6. VOLUME
# --------------------------------------------------

df["Volume_SMA20"] = (
    df["Volume"].rolling(20).mean()
)

df["Volume_Ratio"] = (
    df["Volume"] / df["Volume_SMA20"]
)

# --------------------------------------------------
# 7. TREND
# --------------------------------------------------

df["SMA20_above_SMA50"] = (
    df["SMA_20"] > df["SMA_50"]
)

df["SMA50_above_SMA200"] = (
    df["SMA_50"] > df["SMA_200"]
)

# --------------------------------------------------
# 8. REMOVE WARM-UP ROWS
# --------------------------------------------------

df = df.dropna()

# --------------------------------------------------
# 9. SUMMARY
# --------------------------------------------------

print("\nFeature columns created:")

feature_columns = [
    "Return_5D",
    "Return_20D",
    "Return_60D",
    "SMA_20",
    "SMA_50",
    "SMA_200",
    "Price_vs_SMA20",
    "Price_vs_SMA50",
    "Price_vs_SMA200",
    "Volatility_20D",
    "Volatility_60D",
    "Volume_Ratio",
    "SMA20_above_SMA50",
    "SMA50_above_SMA200",
]

for column in feature_columns:
    print(f"  - {column}")

print(f"\nRows after warm-up removal: {len(df)}")

# --------------------------------------------------
# 10. SAVE
# --------------------------------------------------

df.to_csv(OUTPUT_PATH)

print(f"\nSaved to: {OUTPUT_PATH}")

print("\n" + "=" * 60)
print("FEATURE ENGINE COMPLETE")
print("=" * 60)