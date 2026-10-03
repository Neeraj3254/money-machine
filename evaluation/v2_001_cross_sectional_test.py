import pandas as pd
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "relative_strength_features.csv"
)

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "v2_001_cross_sectional_test.csv"
)

FORWARD_DAYS = 20


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(
    INPUT_FILE,
    parse_dates=["Date"]
)

df = df.sort_values(
    ["Date", "Stock"]
).reset_index(drop=True)


# ============================================================
# FUTURE RETURN
# ============================================================

df["Forward_Return_20D"] = (
    df.groupby("Stock")["Stock_Close"]
    .shift(-FORWARD_DAYS)
    / df["Stock_Close"]
    - 1
)


df = df.dropna(
    subset=["Forward_Return_20D"]
).copy()


# ============================================================
# CROSS-SECTIONAL RANK
# ============================================================

df["RS_Rank"] = (
    df.groupby("Date")["Relative_Return_20D"]
    .rank(
        ascending=False,
        method="first"
    )
)


df["RS_Rank"] = (
    df["RS_Rank"]
    .astype(int)
)


# ============================================================
# TOP / BOTTOM
# ============================================================

df["Top_2"] = (
    df["RS_Rank"] <= 2
)

df["Bottom_2"] = (
    df["RS_Rank"] >= 4
)


# ============================================================
# DAILY CROSS-SECTIONAL SPREAD
# ============================================================

daily = (
    df.groupby("Date")
    .agg(
        Top_2_Return=(
            "Forward_Return_20D",
            lambda x: x[
                df.loc[x.index, "Top_2"]
            ].mean()
        ),
        Bottom_2_Return=(
            "Forward_Return_20D",
            lambda x: x[
                df.loc[x.index, "Bottom_2"]
            ].mean()
        ),
    )
    .reset_index()
)

daily["Top_Bottom_Spread"] = (
    daily["Top_2_Return"]
    - daily["Bottom_2_Return"]
)


# ============================================================
# RESULTS
# ============================================================

print("=" * 90)
print("V2-001 CROSS-SECTIONAL RELATIVE-STRENGTH TEST")
print("=" * 90)

print(
    f"\nEvaluation dates: {len(daily):,}"
)

print(
    f"Average top-2 return: "
    f"{daily['Top_2_Return'].mean():.4%}"
)

print(
    f"Average bottom-2 return: "
    f"{daily['Bottom_2_Return'].mean():.4%}"
)

print(
    f"Top-minus-bottom spread: "
    f"{daily['Top_Bottom_Spread'].mean():.4%}"
)

print(
    f"Positive spread dates: "
    f"{(daily['Top_Bottom_Spread'] > 0).mean():.2%}"
)

print("\nStock rank distribution:")

rank_summary = (
    df.groupby("Stock")["RS_Rank"]
    .agg(
        Mean_Rank="mean",
        Median_Rank="median",
    )
)

rank_summary["Rank_1"] = (
    df.groupby("Stock")["RS_Rank"]
    .apply(lambda x: (x == 1).sum())
)

rank_summary["Rank_5"] = (
    df.groupby("Stock")["RS_Rank"]
    .apply(lambda x: (x == 5).sum())
)

print(
    rank_summary
    .round(2)
    .to_string()
)

# ============================================================
# SAVE
# ============================================================

daily.to_csv(
    OUTPUT_FILE,
    index=False
)

print(
    f"\nSaved:\n{OUTPUT_FILE}"
)

print(
    "\n" + "=" * 90
)
print(
    "CROSS-SECTIONAL TEST COMPLETE"
)
print(
    "=" * 90
)