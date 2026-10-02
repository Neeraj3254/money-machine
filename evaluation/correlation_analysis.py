import pandas as pd
from pathlib import Path


DATA_DIR = Path("data/processed")

TICKERS = [
    "reliance",
    "tcs",
    "infy",
    "hdfcbank",
    "icicibank"
]


returns = {}


for ticker in TICKERS:

    path = DATA_DIR / f"{ticker}_features.csv"

    df = pd.read_csv(
        path,
        index_col=0,
        parse_dates=True
    )

    returns[ticker.upper()] = df["Daily_Return"]


returns_df = pd.DataFrame(returns)

correlation = returns_df.corr()


print("=" * 70)
print("CROSS-STOCK RETURN CORRELATION")
print("=" * 70)

print(
    correlation.round(3).to_string()
)

average_off_diagonal = (
    correlation.values.sum()
    - len(correlation)
) / (
    len(correlation) * (len(correlation) - 1)
)

print(
    f"\nAverage pairwise correlation: "
    f"{average_off_diagonal:.3f}"
)


output_path = (
    DATA_DIR / "return_correlation.csv"
)

correlation.to_csv(output_path)

print(f"\nSaved to: {output_path}")

print("\n" + "=" * 70)
print("CORRELATION ANALYSIS COMPLETE")
print("=" * 70)