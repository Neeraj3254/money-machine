import pandas as pd


INPUT_PATH = "data/processed/multi_stock_validation.csv"


print("=" * 70)
print("CROSS-STOCK VALIDATION SUMMARY")
print("=" * 70)


df = pd.read_csv(INPUT_PATH)


print("\nINDIVIDUAL STOCK RESULTS")
print("-" * 70)

print(
    df[
        [
            "Stock",
            "Signal_Avg_20D_Return",
            "Baseline_Avg_20D_Return",
            "Return_Difference",
            "Signal_Positive_Rate",
            "Baseline_Positive_Rate",
            "Positive_Rate_Difference",
        ]
    ].round(4).to_string(index=False)
)


mean_difference = df["Return_Difference"].mean()
median_difference = df["Return_Difference"].median()

positive_stocks = (
    df["Return_Difference"] > 0
).sum()

negative_stocks = (
    df["Return_Difference"] < 0
).sum()


print("\nCROSS-STOCK SUMMARY")
print("-" * 70)

print(f"Stocks tested: {len(df)}")
print(f"Mean return difference: {mean_difference:.4%}")
print(f"Median return difference: {median_difference:.4%}")
print(f"Stocks with positive difference: {positive_stocks}")
print(f"Stocks with negative difference: {negative_stocks}")


print("\nRESEARCH INTERPRETATION")
print("-" * 70)

if positive_stocks == len(df):
    print("The signal outperformed baseline across all tested stocks.")
elif negative_stocks == len(df):
    print("The signal underperformed baseline across all tested stocks.")
else:
    print("The signal produced mixed results across stocks.")


print("\n" + "=" * 70)
print("SUMMARY COMPLETE")
print("=" * 70)