from datetime import date
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import requests


NSE_BHAVCOPY_BASE_URL = (
    "https://nsearchives.nseindia.com/content/cm/"
)


RAW_DATA_DIR = Path("data/market/raw")


def build_bhavcopy_url(
    trade_date: str,
) -> str:
    """
    Build the NSE UDiFF CM bhavcopy URL.

    Expected date format:
    YYYY-MM-DD
    """

    parsed_date = date.fromisoformat(trade_date)

    date_code = parsed_date.strftime("%Y%m%d")

    filename = (
        f"BhavCopy_NSE_CM_0_0_0_"
        f"{date_code}_F_0000.csv.zip"
    )

    return (
        NSE_BHAVCOPY_BASE_URL
        + filename
    )


def download_daily_bhavcopy(
    trade_date: str,
) -> Path:
    """
    Download one NSE CM UDiFF bhavcopy ZIP.

    The raw ZIP is cached locally.
    """

    url = build_bhavcopy_url(
        trade_date
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/154.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "application/zip,"
            "application/octet-stream,*/*"
        ),
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    RAW_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        RAW_DATA_DIR
        / f"BhavCopy_NSE_CM_{trade_date}.zip"
    )

    output_path.write_bytes(
        response.content
    )

    return output_path


def extract_bhavcopy(
    zip_path: str | Path,
) -> Path:
    """
    Extract the CSV contained inside an NSE UDiFF ZIP.
    """

    zip_path = Path(zip_path)

    if not zip_path.exists():
        raise FileNotFoundError(
            f"ZIP file not found: {zip_path}"
        )

    with ZipFile(
        zip_path,
        "r",
    ) as archive:

        csv_files = [
            name
            for name in archive.namelist()
            if name.lower().endswith(".csv")
        ]

        if not csv_files:
            raise ValueError(
                "No CSV file found inside NSE bhavcopy ZIP."
            )

        csv_name = csv_files[0]

        output_path = (
            RAW_DATA_DIR
            / csv_name
        )

        with archive.open(csv_name) as source:
            output_path.write_bytes(
                source.read()
            )

    return output_path


def read_bhavcopy(
    path: str | Path,
) -> pd.DataFrame:
    """
    Read the extracted NSE bhavcopy.
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Bhavcopy CSV not found: {path}"
        )

    df = pd.read_csv(path)

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return df


def inspect_bhavcopy(
    df: pd.DataFrame,
) -> dict:
    """
    Return basic information about the downloaded file.
    """

    return {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "sample": df.head(5).to_dict(
            orient="records"
        ),
    }

import pandas as pd


def normalize_daily_market_data(
    bhavcopy_path,
    universe_path="data/universe/nse_equity_universe.csv",
):
    """
    Convert one NSE UDiFF Bhavcopy into a clean EQ-only
    daily market dataset.

    Rules:
    - Join against the NSE security master using ISIN.
    - Keep only SERIES == EQ.
    - Preserve securities absent from the day's Bhavcopy.
    - Do not combine EQ and BL series.
    - Return one row per universe security.
    """

    bhavcopy = read_bhavcopy(bhavcopy_path)

    universe = pd.read_csv(universe_path)

    required_bhavcopy = [
        "ISIN",
        "TCKRSYMB",
        "SCTYSRS",
        "OPNPRIC",
        "HGHPRIC",
        "LWPRIC",
        "CLSPRIC",
        "LASTPRIC",
        "PRVSCLSGPRIC",
        "TTLTRADGVOL",
        "TTLTRFVAL",
        "TTLNBOFTXSEXCTD",
    ]

    missing_columns = [
        column
        for column in required_bhavcopy
        if column not in bhavcopy.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing Bhavcopy columns: {missing_columns}"
        )

    required_universe = ["SYMBOL", "SERIES", "ISIN"]

    missing_universe_columns = [
        column
        for column in required_universe
        if column not in universe.columns
    ]

    if missing_universe_columns:
        raise ValueError(
            f"Missing universe columns: {missing_universe_columns}"
        )

    # Normalize identifiers.
    bhavcopy["ISIN"] = bhavcopy["ISIN"].astype(str).str.strip()
    bhavcopy["SCTYSRS"] = (
        bhavcopy["SCTYSRS"].astype(str).str.strip().str.upper()
    )

    universe["ISIN"] = universe["ISIN"].astype(str).str.strip()
    universe["SERIES"] = (
        universe["SERIES"].astype(str).str.strip().str.upper()
    )

    # Keep only EQ records from Bhavcopy.
    equity_bhavcopy = bhavcopy[
        bhavcopy["SCTYSRS"] == "EQ"
    ].copy()

    # Keep only the columns needed by the market engine.
    market_columns = [
        "ISIN",
        "TCKRSYMB",
        "OPNPRIC",
        "HGHPRIC",
        "LWPRIC",
        "CLSPRIC",
        "LASTPRIC",
        "PRVSCLSGPRIC",
        "TTLTRADGVOL",
        "TTLTRFVAL",
        "TTLNBOFTXSEXCTD",
    ]

    equity_bhavcopy = equity_bhavcopy[market_columns]

    # Protect against unexpected duplicate EQ records.
    duplicate_isins = equity_bhavcopy[
        equity_bhavcopy["ISIN"].duplicated(keep=False)
    ]

    if not duplicate_isins.empty:
        raise ValueError(
            "Duplicate EQ ISINs found in Bhavcopy:\n"
            + duplicate_isins.to_string(index=False)
        )

    # The universe is the authoritative list of securities.
    result = universe[
        ["SYMBOL", "SERIES", "ISIN"]
    ].copy()

    # Left join preserves securities that did not appear that day.
    result = result.merge(
        equity_bhavcopy,
        on="ISIN",
        how="left",
        validate="one_to_one",
    )

    # Prefer the security-master symbol.
    result["TCKRSYMB"] = result["SYMBOL"]

    # Numeric market fields.
    numeric_columns = [
        "OPNPRIC",
        "HGHPRIC",
        "LWPRIC",
        "CLSPRIC",
        "LASTPRIC",
        "PRVSCLSGPRIC",
        "TTLTRADGVOL",
        "TTLTRFVAL",
        "TTLNBOFTXSEXCTD",
    ]

    for column in numeric_columns:
        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        )

    result["DATA_AVAILABLE"] = result["CLSPRIC"].notna()

    return result

from pathlib import Path
from datetime import timedelta
import time

from .market_data import save_daily_data, is_cached


def build_and_save_daily_market_data(
    trade_date,
    bhavcopy_path=None,
):
    """
    Download/extract if necessary, normalize the NSE Bhavcopy,
    validate it, and save the normalized daily market dataset.
    """

    if bhavcopy_path is None:
        zip_path = download_daily_bhavcopy(trade_date)
        bhavcopy_path = extract_bhavcopy(zip_path)

    df = normalize_daily_market_data(
        bhavcopy_path=bhavcopy_path,
    )

    # Basic integrity checks.
    if len(df) == 0:
        raise ValueError(
            "Normalized market dataset is empty."
        )

    if df["ISIN"].duplicated().any():
        raise ValueError(
            "Duplicate ISINs found after normalization."
        )

    if df["SYMBOL"].duplicated().any():
        raise ValueError(
            "Duplicate symbols found after normalization."
        )

    save_daily_data(
        df,
        trade_date,
    )

    return df


def backfill_daily_market_data(
    start_date,
    end_date,
    sleep_seconds=0.5,
):
    """
    Backfill NSE CM UDiFF daily market data.

    The process is incremental:
    - existing normalized days are skipped
    - weekends are skipped
    - failed/non-trading dates are recorded
    - successful days are normalized and saved as Parquet
    """

    start = pd.Timestamp(start_date).date()
    end = pd.Timestamp(end_date).date()

    if start > end:
        raise ValueError(
            "start_date must be <= end_date"
        )

    current = start

    summary = {
        "requested_days": 0,
        "saved_days": 0,
        "skipped_cached_days": 0,
        "failed_days": 0,
        "failed_dates": [],
    }

    while current <= end:

        # Saturday = 5, Sunday = 6
        if current.weekday() >= 5:
            current += timedelta(days=1)
            continue

        summary["requested_days"] += 1

        trade_date = current.isoformat()

        try:

            # Skip if normalized Parquet already exists.
            if is_cached(trade_date):
                print(
                    f"[CACHED] {trade_date}"
                )

                summary[
                    "skipped_cached_days"
                ] += 1

                current += timedelta(days=1)
                continue

            print(
                f"[DOWNLOAD] {trade_date}"
            )

            df = build_and_save_daily_market_data(
                trade_date
            )

            print(
                f"[SAVED] {trade_date} | "
                f"rows={len(df)} | "
                f"available="
                f"{df['DATA_AVAILABLE'].sum()}"
            )

            summary["saved_days"] += 1

            time.sleep(
                sleep_seconds
            )

        except Exception as exc:

            print(
                f"[SKIP] {trade_date} | "
                f"{type(exc).__name__}: {exc}"
            )

            summary["failed_days"] += 1

            summary[
                "failed_dates"
            ].append(
                {
                    "date": trade_date,
                    "error": str(exc),
                }
            )

        current += timedelta(days=1)

    return summary