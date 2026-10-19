from io import BytesIO
from pathlib import Path
import os

import pandas as pd
import requests


NSE_SECURITY_MASTER_URL = (
    "https://archives.nseindia.com/content/equities/"
    "EQUITY_L.csv"
)


def _atomic_save_csv(df: pd.DataFrame, output: Path) -> None:
    """Write a CSV to a temporary file, then replace the destination."""
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")

    try:
        df.to_csv(temporary, index=False)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()


def _validate_security_master_fields(df: pd.DataFrame) -> None:
    """Reject malformed master records before any universe filtering."""
    required_columns = ["SYMBOL", "SERIES", "ISIN"]
    missing = [column for column in required_columns if column not in df]
    if missing:
        raise ValueError(
            f"Security master is missing required columns: {missing}"
        )

    invalid_values = {"", "NAN", "NONE", "NULL", "<NA>"}
    for column in required_columns:
        values = df[column].astype("string").str.strip().str.upper()
        invalid = values.isna() | values.isin(invalid_values)
        if invalid.any():
            raise ValueError(
                f"Security master contains invalid {column} values"
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

    df = pd.read_csv(BytesIO(response.content))

    # Normalize column names.
    df.columns = (
        df.columns.astype(str).str.strip().str.upper()
    )

    # Validate the downloaded CSV schema before selecting columns.
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

    # Keep only the required fields.
    normalized = df[
        ["SYMBOL", "SERIES", "ISIN NUMBER"]
    ].copy()

    normalized = normalized.rename(
        columns={"ISIN NUMBER": "ISIN"}
    )

    # Normalize identifier values.
    for column in ["SYMBOL", "SERIES", "ISIN"]:
        normalized[column] = (
            normalized[column]
            .astype("string")
            .str.strip()
            .str.upper()
        )

    # Reject missing, blank, or placeholder identifiers.
    invalid_values = {"", "NAN", "NONE", "NULL", "<NA>"}

    for column in ["SYMBOL", "SERIES", "ISIN"]:
        invalid = (
            normalized[column].isna()
            | normalized[column].isin(invalid_values)
        )

        if invalid.any():
            raise ValueError(
                f"Security master contains invalid {column} values"
            )

    # Reject ambiguous security identifiers.
    if normalized["SYMBOL"].duplicated().any():
        raise ValueError(
            "Security master contains duplicate symbols"
        )

    if normalized["ISIN"].duplicated().any():
        raise ValueError(
            "Security master contains duplicate ISINs"
        )

    # Save only after all validation succeeds.
    output = Path(output_path)
    _atomic_save_csv(normalized, output)

    return output


def build_equity_universe(
    security_master_path: str = "data/universe/nse_security_master.csv",
    equity_universe_path: str = "data/universe/nse_equity_universe.csv",
) -> dict:
    """
    Download, filter, validate, and save the NSE equity universe.
    """

    from research.market.universe import (
        filter_equity_universe,
        load_security_master,
        save_universe,
        validate_universe,
    )

    # Download and normalize the security master.
    download_security_master(security_master_path)

    # Load the downloaded master.
    master = load_security_master(security_master_path)

    if master.empty:
        raise ValueError("Downloaded security master is empty.")

    # Validate the entire provider master before filtering out non-EQ rows.
    # Otherwise a malformed EQ record can be silently discarded by the
    # filter and the remaining partial universe can appear valid.
    _validate_security_master_fields(master)

    # Keep standard equity-series securities.
    equity = filter_equity_universe(master)

    if equity.empty:
        raise ValueError("No EQ-series securities found.")

    # Validate before saving the equity universe.
    summary = validate_universe(equity)

    # Persist the validated universe.
    save_universe(equity, equity_universe_path)

    return {
        "security_master_path": security_master_path,
        "equity_universe_path": equity_universe_path,
        **summary,
    }
