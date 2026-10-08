from pathlib import Path

import pandas as pd


MARKET_DATA_DIR = Path("data/market")
RAW_DATA_DIR = MARKET_DATA_DIR / "raw"
NORMALIZED_DATA_DIR = MARKET_DATA_DIR / "normalized"


def ensure_market_directories() -> None:
    """Create local market-data directories."""

    RAW_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    NORMALIZED_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def normalized_daily_path(
    date: str,
) -> Path:
    """
    Return the local path for one normalized trading day.
    """

    return (
        NORMALIZED_DATA_DIR
        / f"market_{date}.parquet"
    )


def is_cached(
    date: str,
) -> bool:
    """
    Check whether normalized data for a date
    already exists locally.
    """

    return normalized_daily_path(date).exists()


def save_daily_data(
    df: pd.DataFrame,
    date: str,
) -> Path:
    """
    Save one normalized trading day's market data.
    """

    ensure_market_directories()

    path = normalized_daily_path(date)

    df.to_parquet(
        path,
        index=False,
    )

    return path


def load_daily_data(
    date: str,
) -> pd.DataFrame:
    """
    Load one locally cached trading day.
    """

    path = normalized_daily_path(date)

    if not path.exists():
        raise FileNotFoundError(
            f"No cached market data for {date}"
        )

    return pd.read_parquet(path)


def market_data_status() -> dict:
    """
    Return basic local market-data status.
    """

    ensure_market_directories()

    files = list(
        NORMALIZED_DATA_DIR.glob(
            "market_*.parquet"
        )
    )

    return {
        "normalized_days": len(files),
        "data_directory": str(
            NORMALIZED_DATA_DIR
        ),
    }