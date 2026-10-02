import yfinance as yf

SYMBOL = "RELIANCE.NS"

print(f"Downloading data for {SYMBOL}...")

df = yf.download(
    SYMBOL,
    start="2019-01-01",
    end="2026-01-01",
    auto_adjust=False,
    progress=False,
)

print("\nFirst 5 rows:")
print(df.head())

print("\nLast 5 rows:")
print(df.tail())

print("\nShape:")
print(df.shape)

print("\nColumns:")
print(df.columns)

output_path = "data/raw/reliance_daily.csv"

df.to_csv(output_path)

print(f"\nSaved to: {output_path}")