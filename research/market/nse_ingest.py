from io import BytesIO
from pathlib import Path

import pandas as pd
import requests


NSE_SECURITY_MASTER_URL = (
    "https://archives.nseindia.com/content/equities/"
    "EQUITY_L.csv"
)


def download_security_master(
    output_path: str = "data/universe/nse_security_master.csv",
) -> Path:
    """
    Download the NSE equity security master and normalize
    it into Money Machine's internal format.
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/154.0.0.0 Safari/537.36"
        ),
        "Accept": "text/csv,application/octet-stream,*/*",
    }

    response = requests.get(
        NSE_SECURITY_MASTER_URL,
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    df = pd.read_csv(
        BytesIO(response.content)
    )

    # ---------------------------------------------------------
    # NORMALIZE COLUMN NAMES
    # ---------------------------------------------------------

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.upper()
    )

    required_columns = [
        "SYMBOL",
        "SERIES",
        "ISIN NUMBER",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Unexpected NSE format. Missing columns: {missing}. "
            f"Received columns: {list(df.columns)}"
        )

    # ---------------------------------------------------------
    # KEEP REQUIRED FIELDS
    # ---------------------------------------------------------

    normalized = df[
        [
            "SYMBOL",
            "SERIES",
            "ISIN NUMBER",
        ]
    ].copy()

    normalized = normalized.rename(
        columns={
            "ISIN NUMBER": "ISIN"
        }
    )

    # ---------------------------------------------------------
    # NORMALIZE VALUES
    # ---------------------------------------------------------

    for column in [
        "SYMBOL",
        "SERIES",
        "ISIN",
    ]:
        normalized[column] = (
            normalized[column]
            .astype(str)
            .str.strip()
            .str.upper()
        )

    # ---------------------------------------------------------
    # SAVE
    # ---------------------------------------------------------

    output = Path(output_path)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    normalized.to_csv(
        output,
        index=False,
    )

    return output