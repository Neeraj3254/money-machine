import yfinance as yf
from pathlib import Path


TICKERS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
]

START_DATE = "2019-01-01"
END_DATE = "2026-01-01"

OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


print("=" * 60)
print("MULTI-STOCK DATA DOWNLOAD")
print("=" * 60)


for ticker in TICKERS:

    print(f"\nDownloading {ticker}...")

    df = yf.download(
        ticker,
        start=START_DATE,
        end=END_DATE,
        auto_adjust=False,
        progress=False
    )

    if df.empty:
        print(f"WARNING: No data received for {ticker}")
        continue

    # Flatten MultiIndex columns if present
    if isinstance(df.columns, __import__("pandas").MultiIndex):
        df.columns = df.columns.get_level_values(0)

    output_path = OUTPUT_DIR / f"{ticker.replace('.NS', '').lower()}_daily.csv"

    df.to_csv(output_path)

    print(f"Rows: {len(df):,}")
    print(f"Saved: {output_path}")


print("\n" + "=" * 60)
print("DOWNLOAD COMPLETE")
print("=" * 60)