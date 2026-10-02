import pandas as pd

INPUT_PATH = "data/raw/reliance_daily.csv"
OUTPUT_PATH = "data/processed/reliance_daily_clean.csv"


print("=" * 60)
print("DATA QUALITY GATE v0.1")
print("=" * 60)


# --------------------------------------------------
# 1. LOAD DATA
# --------------------------------------------------

print("\n[1] Loading data...")

df = pd.read_csv(
    INPUT_PATH,
    header=[0, 1],
    index_col=0,
    parse_dates=True
)

print(f"Rows loaded: {len(df)}")


# --------------------------------------------------
# 2. FLATTEN COLUMNS
# --------------------------------------------------

print("\n[2] Normalizing columns...")

df.columns = df.columns.get_level_values(0)

print("Columns:")
print(list(df.columns))


# --------------------------------------------------
# 3. CHECK DATE INDEX
# --------------------------------------------------

print("\n[3] Checking dates...")

if df.index.isna().any():
    raise ValueError("FAIL: Missing dates found.")

if not df.index.is_monotonic_increasing:
    raise ValueError("FAIL: Dates are not sorted.")

if df.index.duplicated().any():
    raise ValueError("FAIL: Duplicate dates found.")

print("PASS: Dates are valid and ordered.")


# --------------------------------------------------
# 4. CHECK REQUIRED COLUMNS
# --------------------------------------------------

print("\n[4] Checking required columns...")

required_columns = [
    "Open",
    "High",
    "Low",
    "Close",
    "Adj Close",
    "Volume",
]

missing_columns = [
    column for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"FAIL: Missing columns: {missing_columns}"
    )

print("PASS: Required columns exist.")


# --------------------------------------------------
# 5. CHECK MISSING VALUES
# --------------------------------------------------

print("\n[5] Checking missing values...")

missing = df[required_columns].isna().sum()

print(missing)

if missing.sum() > 0:
    raise ValueError("FAIL: Missing market data found.")

print("PASS: No missing values.")


# --------------------------------------------------
# 6. CHECK PRICE VALUES
# --------------------------------------------------

print("\n[6] Checking price validity...")

price_columns = [
    "Open",
    "High",
    "Low",
    "Close",
    "Adj Close",
]

if (df[price_columns] <= 0).any().any():
    raise ValueError("FAIL: Zero or negative price found.")

print("PASS: All prices are positive.")


# --------------------------------------------------
# 7. CHECK OHLC LOGIC
# --------------------------------------------------

print("\n[7] Checking OHLC consistency...")

invalid_ohlc = (
    (df["High"] < df["Open"]) |
    (df["High"] < df["Close"]) |
    (df["Low"] > df["Open"]) |
    (df["Low"] > df["Close"]) |
    (df["High"] < df["Low"])
)

invalid_count = invalid_ohlc.sum()

print(f"Invalid OHLC rows: {invalid_count}")

if invalid_count > 0:
    raise ValueError("FAIL: Invalid OHLC relationships found.")

print("PASS: OHLC relationships are valid.")


# --------------------------------------------------
# 8. CHECK VOLUME
# --------------------------------------------------

print("\n[8] Checking volume...")

if (df["Volume"] < 0).any():
    raise ValueError("FAIL: Negative volume found.")

print("PASS: No negative volume.")


# --------------------------------------------------
# 9. BASIC STATISTICS
# --------------------------------------------------

print("\n[9] Basic data summary...")

print(f"Start date: {df.index.min()}")
print(f"End date:   {df.index.max()}")
print(f"Rows:       {len(df)}")

print("\nClose price summary:")
print(df["Close"].describe())


# --------------------------------------------------
# 10. SAVE VALIDATED DATA
# --------------------------------------------------

print("\n[10] Saving validated data...")

df.to_csv(OUTPUT_PATH)

print(f"Saved to: {OUTPUT_PATH}")


# --------------------------------------------------
# FINAL RESULT
# --------------------------------------------------

print("\n" + "=" * 60)
print("DATA QUALITY GATE: PASS")
print("=" * 60)