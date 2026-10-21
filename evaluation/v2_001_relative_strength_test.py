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
    / "v2_001_relative_strength_test.csv"
)

FORWARD_DAYS = 20


# ============================================================
# LOAD
# ============================================================

df = pd.read_csv(
    INPUT_FILE,
    parse_dates=["Date"]
)

df = df.sort_values(
    ["Stock", "Date"]
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


# ============================================================
# SIGNAL
# ============================================================

df["Relative_Strength_Signal"] = (
    df["Relative_Return_20D"] > 0
)


# Remove observations where future outcome is unavailable.
df = df.dropna(
    subset=["Forward_Return_20D"]
).copy()


# ============================================================
# VALIDATION
# ============================================================

assert (
    df.duplicated(
        ["Stock", "Date"]
    ).sum()
    == 0
)

assert (
    df["Forward_Return_20D"]
    .notna()
    .all()
)


# ============================================================
# OVERALL BASELINE
# ============================================================

baseline_avg = (
    df["Forward_Return_20D"]
    .mean()
)

baseline_positive = (
    df["Forward_Return_20D"]
    > 0
).mean()


# ============================================================
# SIGNAL RESULTS
# ============================================================

signal = df[
    df["Relative_Strength_Signal"]
]

signal_avg = (
    signal["Forward_Return_20D"]
    .mean()
)

signal_positive = (
    signal["Forward_Return_20D"]
    > 0
).mean()


incremental_return = (
    signal_avg
    - baseline_avg
)

incremental_positive = (
    signal_positive
    - baseline_positive
)


# ============================================================
# BY STOCK
# ============================================================

rows = []

for stock, group in df.groupby("Stock"):

    baseline = (
        group["Forward_Return_20D"]
        .mean()
    )

    baseline_win = (
        group["Forward_Return_20D"]
        > 0
    ).mean()

    s = group[
        group["Relative_Strength_Signal"]
    ]

    signal_return = (
        s["Forward_Return_20D"]
        .mean()
    )

    signal_win = (
        s["Forward_Return_20D"]
        > 0
    ).mean()

    rows.append(
        {
            "Stock": stock,
            "Observations": len(group),
            "Signal_Observations": len(s),
            "Signal_Frequency": len(s) / len(group),
            "Baseline_Avg_Return": baseline,
            "Signal_Avg_Return": signal_return,
            "Incremental_Return": (
                signal_return - baseline
            ),
            "Baseline_Positive_Rate": baseline_win,
            "Signal_Positive_Rate": signal_win,
            "Incremental_Positive_Rate": (
                signal_win - baseline_win
            ),
        }
    )


results = pd.DataFrame(rows)


# ============================================================
# OUTPUT
# ============================================================

print("=" * 90)
print("V2-001 RELATIVE STRENGTH — FIRST EVIDENCE TEST")
print("=" * 90)

print(
    f"\nForward horizon: {FORWARD_DAYS} trading days"
)

print(
    f"Observations: {len(df):,}"
)

print(
    f"Signal observations: {len(signal):,}"
)

print(
    f"Signal frequency: "
    f"{len(signal) / len(df):.2%}"
)

print("\nPooled results:")
print(
    f"Baseline average return: "
    f"{baseline_avg:.4%}"
)

print(
    f"Signal average return:   "
    f"{signal_avg:.4%}"
)

print(
    f"Incremental return:      "
    f"{incremental_return:.4%}"
)

print(
    f"Baseline positive rate:  "
    f"{baseline_positive:.2%}"
)

print(
    f"Signal positive rate:    "
    f"{signal_positive:.2%}"
)

print(
    f"Incremental positive:    "
    f"{incremental_positive:.2%}"
)

print("\nBy stock:")
print(
    results.to_string(
        index=False,
        formatters={
            "Signal_Frequency": "{:.2%}".format,
            "Baseline_Avg_Return": "{:.4%}".format,
            "Signal_Avg_Return": "{:.4%}".format,
            "Incremental_Return": "{:.4%}".format,
            "Baseline_Positive_Rate": "{:.2%}".format,
            "Signal_Positive_Rate": "{:.2%}".format,
            "Incremental_Positive_Rate": "{:.2%}".format,
        }
    )
)


# ============================================================
# SAVE
# ============================================================

df.to_csv(
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
    "V2-001 FIRST EVIDENCE TEST COMPLETE"
)
print(
    "=" * 90
)