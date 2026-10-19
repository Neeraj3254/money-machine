from pathlib import Path

import pandas as pd


NORMALIZED_DATA_DIR = Path(
    "data/market/normalized"
)


def load_daily_file(path: Path) -> pd.DataFrame:
    """
    Load one normalized NSE daily market-data file.
    """

    df = pd.read_parquet(path)

    if df.empty:
        raise ValueError(
            f"Empty market-data file: {path}"
        )

    return df


def build_research_panel(
    start_date,
    end_date,
) -> pd.DataFrame:
    """
    Combine normalized daily market-data files
    into one longitudinal research panel.
    """

    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()

    frames = []

    files = sorted(
        NORMALIZED_DATA_DIR.glob(
            "market_*.parquet"
        )
    )

    for path in files:

        date_text = path.stem.replace(
            "market_",
            "",
        )

        try:
            file_date = pd.to_datetime(
                date_text
            ).date()

        except Exception:
            continue

        if not (
            start_date
            <= file_date
            <= end_date
        ):
            continue

        df = load_daily_file(path)

        df = df.copy()

        df["TRADE_DATE"] = file_date

        frames.append(df)

    if not frames:
        raise ValueError(
            "No normalized market-data files found "
            "for requested date range"
        )

    panel = pd.concat(
        frames,
        ignore_index=True,
    )

    return panel

def filter_available_market_data(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Keep only observations where actual market data is available.

    This prevents missing security observations from being treated
    as valid trading observations during research.
    """

    if "DATA_AVAILABLE" not in df.columns:
        raise ValueError(
            "Missing required column: DATA_AVAILABLE"
        )

    result = df.copy()

    result = result[
        result["DATA_AVAILABLE"] == True
    ].copy()

    result = result[
        result["CLSPRIC"].notna()
    ].copy()

    result = result[
        result["CLSPRIC"] > 0
    ].copy()

    return result.reset_index(drop=True)