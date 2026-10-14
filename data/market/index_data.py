from pathlib import Path

import pandas as pd


def load_legacy_nifty(
    path="data/raw/nifty50_daily.csv",
):
    df = pd.read_csv(path)

    df["Date"] = pd.to_datetime(df["Date"])

    return df[
        [
            "Date",
            "Open",
            "High",
            "Low",
            "Close",
        ]
    ].copy()


def load_nse_2026(
    path="data/raw/nifty50_2026_nse.csv",
):
    df = pd.read_csv(path)

    # NSE export contains trailing spaces in column names.
    df.columns = [
        column.strip()
        for column in df.columns
    ]

    df["Date"] = pd.to_datetime(
        df["Date"],
        format="%d-%b-%Y",
    )

    return df[
        [
            "Date",
            "Open",
            "High",
            "Low",
            "Close",
        ]
    ].copy()


def build_unified_nifty(
    output_path="data/raw/nifty50_daily_unified.csv",
):
    """
    Combine the existing 2019-2025 NIFTY price history
    with official NSE 2026 historical index data.

    Original source files are never modified.
    """

    legacy = load_legacy_nifty()
    nse_2026 = load_nse_2026()

    legacy["Source"] = "LEGACY_DATASET"
    nse_2026["Source"] = "NSE_HISTORICAL_INDEX"

    combined = pd.concat(
        [
            legacy,
            nse_2026,
        ],
        ignore_index=True,
    )

    combined = combined.sort_values(
        "Date"
    )

    duplicate_dates = (
        combined["Date"]
        .duplicated()
        .sum()
    )

    if duplicate_dates > 0:
        raise ValueError(
            f"Found {duplicate_dates} duplicate NIFTY dates"
        )

    price_columns = [
        "Open",
        "High",
        "Low",
        "Close",
    ]

    for column in price_columns:

        if combined[column].isna().any():
            raise ValueError(
                f"Missing values found in {column}"
            )

        if (combined[column] <= 0).any():
            raise ValueError(
                f"Non-positive values found in {column}"
            )

    combined = combined.reset_index(
        drop=True
    )

    output = Path(output_path)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    combined.to_csv(
        output,
        index=False,
    )

    return combined