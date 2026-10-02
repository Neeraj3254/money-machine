import yfinance as yf
from pathlib import Path


OUTPUT_PATH = Path(
    "data/raw/nifty50_daily.csv"
)

print("=" * 60)
print("DOWNLOADING NIFTY 50")
print("=" * 60)


df = yf.download(
    "^NSEI",
    start="2019-01-01",
    end="2026-01-01",
    auto_adjust=False,
    progress=False
)


if hasattr(df.columns, "levels"):
    df.columns = df.columns.get_level_values(0)


df.to_csv(OUTPUT_PATH)

print(f"Rows: {len(df):,}")
print(f"Saved to: {OUTPUT_PATH}")

print("\n" + "=" * 60)
print("DOWNLOAD COMPLETE")
print("=" * 60)