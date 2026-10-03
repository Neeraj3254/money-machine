import pandas as pd
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

STOCKS = [
    "RELIANCE",
    "TCS",
    "INFY",
    "HDFCBANK",
    "ICICIBANK",
]

STOCK_FEATURE_TEMPLATE = (
    BASE_DIR
    / "data"
    / "processed"
    / "{stock}_features.csv"
)

NIFTY_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "nifty50_regimes_leakage_free.csv"
)

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "relative_strength_features.csv"
)

LOOKBACK = 20


# ============================================================
# LOAD NIFTY
# ============================================================

nifty = pd.read_csv(
    NIFTY_FILE,
    parse_dates=["Date"]
)

nifty = nifty[
    ["Date", "Close"]
].copy()

nifty = nifty.rename(
    columns={
        "Close": "NIFTY_Close"
    }
)

nifty = nifty.sort_values(
    "Date"
).reset_index(drop=True)

nifty["NIFTY_Return_20D"] = (
    nifty["NIFTY_Close"]
    .pct_change(LOOKBACK)
)


# ============================================================
# BUILD STOCK RELATIVE STRENGTH
# ============================================================

results = []

for stock in STOCKS:

    stock_file = Path(
        str(STOCK_FEATURE_TEMPLATE).format(
            stock=stock
        )
    )

    df = pd.read_csv(
        stock_file,
        parse_dates=["Date"]
    )

    required = {
        "Date",
        "Close",
        "Return_20D"
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"{stock}: missing columns {sorted(missing)}"
        )

    df = df[
        [
            "Date",
            "Close",
            "Return_20D"
        ]
    ].copy()

    df = df.rename(
        columns={
            "Close": "Stock_Close",
            "Return_20D": "Stock_Return_20D"
        }
    )

    df["Stock"] = stock

    # --------------------------------------------------------
    # Join stock data with NIFTY data by date
    # --------------------------------------------------------

    df = df.merge(
        nifty[
            [
                "Date",
                "NIFTY_Close",
                "NIFTY_Return_20D"
            ]
        ],
        on="Date",
        how="inner"
    )

    # --------------------------------------------------------
    # Relative strength
    # --------------------------------------------------------

    df["Relative_Return_20D"] = (
        df["Stock_Return_20D"]
        - df["NIFTY_Return_20D"]
    )

    # Diagnostic direction only.
    # This is NOT yet a trading rule.
    df["Relative_Strength_Positive"] = (
        df["Relative_Return_20D"] > 0
    )

    results.append(
        df
    )


# ============================================================
# COMBINE
# ============================================================

output = pd.concat(
    results,
    ignore_index=True
)

output = output.sort_values(
    ["Date", "Stock"]
).reset_index(drop=True)


# ============================================================
# VALIDATION
# ============================================================

print("=" * 80)
print("V2-001 RELATIVE STRENGTH FEATURE ENGINE")
print("=" * 80)

print(f"\nRows: {len(output):,}")
print(
    f"Stocks: {output['Stock'].nunique()}"
)
print(
    f"Date range: "
    f"{output['Date'].min().date()} "
    f"to "
    f"{output['Date'].max().date()}"
)

print("\nRows by stock:")
print(
    output["Stock"]
    .value_counts()
    .sort_index()
)

print("\nMissing values:")
print(
    output[
        [
            "Stock_Return_20D",
            "NIFTY_Return_20D",
            "Relative_Return_20D"
        ]
    ]
    .isna()
    .sum()
)

print("\nRelative-strength summary:")
print(
    output["Relative_Return_20D"]
    .describe()
    .round(4)
)

print("\nPositive relative-strength percentage:")
print(
    output["Relative_Strength_Positive"]
    .mean()
    .round(4)
)

# ------------------------------------------------------------
# Leakage sanity check
# ------------------------------------------------------------

assert (
    output["Relative_Return_20D"]
    .notna()
    .all()
)

assert (
    output["Date"]
    .is_monotonic_increasing
)

assert (
    output[
        "Relative_Return_20D"
    ].equals(
        (
            output["Stock_Return_20D"]
            - output["NIFTY_Return_20D"]
        )
    )
)

# No duplicate stock/date observations.
assert (
    output
    .duplicated(
        ["Stock", "Date"]
    )
    .sum()
    == 0
)


# ============================================================
# SAVE
# ============================================================

output.to_csv(
    OUTPUT_FILE,
    index=False
)

print(
    f"\nSaved:\n{OUTPUT_FILE}"
)

print(
    "\n" + "=" * 80
)
print(
    "V2-001 FEATURE ENGINE COMPLETE"
)
print(
    "=" * 80
)