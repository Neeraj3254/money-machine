import pandas as pd
from pathlib import Path


INPUT_PATH = (
    Path("data/processed")
    / "strategy_market_regime.csv"
)


df = pd.read_csv(INPUT_PATH)


print("=" * 80)
print("REGIME SAMPLE SIZE CHECK")
print("=" * 80)


summary = (
    df.groupby("Market_Regime")
    .agg(
        Stocks=("Stock", "nunique"),
        Total_Observations=("Observations", "sum"),
        Minimum_Observations=("Observations", "min"),
        Maximum_Observations=("Observations", "max")
    )
    .reset_index()
)


summary["Warning"] = summary[
    "Total_Observations"
].apply(
    lambda x:
        "LOW SAMPLE"
        if x < 30
        else "OK"
)


print(
    summary.to_string(index=False)
)


print("\nInterpretation rule:")
print("30+ observations = preliminary")
print("Below 30 = insufficient for strong inference")

print("\n" + "=" * 80)
print("REGIME SAMPLE CHECK COMPLETE")
print("=" * 80)