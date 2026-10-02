import pandas as pd
import numpy as np

INPUT_PATH = "data/processed/reliance_daily_clean.csv"

print("=" * 60)
print("RETURN ENGINE v0.1")
print("=" * 60)


# --------------------------------------------------
# 1. LOAD VALIDATED DATA
# --------------------------------------------------

df = pd.read_csv(
    INPUT_PATH,
    index_col=0,
    parse_dates=True
)


# --------------------------------------------------
# 2. DAILY RETURNS
# --------------------------------------------------

df["Daily_Return"] = df["Close"].pct_change()


# --------------------------------------------------
# 3. CUMULATIVE GROWTH
# --------------------------------------------------

df["Growth_Index"] = (
    1 + df["Daily_Return"]
).cumprod()


# --------------------------------------------------
# 4. RUNNING PEAK
# --------------------------------------------------

df["Running_Peak"] = df["Growth_Index"].cummax()


# --------------------------------------------------
# 5. DRAWDOWN
# --------------------------------------------------

df["Drawdown"] = (
    df["Growth_Index"] /
    df["Running_Peak"]
) - 1


# --------------------------------------------------
# 6. ROLLING VOLATILITY
# --------------------------------------------------

df["Rolling_20D_Volatility"] = (
    df["Daily_Return"]
    .rolling(20)
    .std()
    * np.sqrt(252)
)


# --------------------------------------------------
# 7. SUMMARY
# --------------------------------------------------

returns = df["Daily_Return"].dropna()

print("\nReturn statistics:")

print(
    f"Average daily return: "
    f"{returns.mean():.4%}"
)

print(
    f"Annualized volatility: "
    f"{returns.std() * np.sqrt(252):.2%}"
)

print(
    f"Maximum drawdown: "
    f"{df['Drawdown'].min():.2%}"
)

print(
    f"Final growth index: "
    f"{df['Growth_Index'].iloc[-1]:.4f}"
)


# --------------------------------------------------
# 8. SAVE
# --------------------------------------------------

output_path = "data/processed/reliance_returns.csv"

df.to_csv(output_path)

print(
    f"\nSaved return dataset to: "
    f"{output_path}"
)

print("\n" + "=" * 60)
print("RETURN ENGINE COMPLETE")
print("=" * 60)