from pathlib import Path

import pandas as pd


def load_security_master(
    path: str = "data/universe/nse_security_master.csv",
) -> pd.DataFrame:
    """
    Load the normalized NSE security master.
    """

    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Security master not found: {file_path}"
        )

    df = pd.read_csv(file_path)

    required_columns = [
        "SYMBOL",
        "SERIES",
        "ISIN",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Security master is missing columns: {missing}"
        )

    return df


def filter_equity_universe(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Keep standard NSE equity-series securities.
    """

    result = df.copy()

    result["SYMBOL"] = (
        result["SYMBOL"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    result["SERIES"] = (
        result["SERIES"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    result["ISIN"] = (
        result["ISIN"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    result = result[
        result["SERIES"] == "EQ"
    ].copy()

    result = result[
        result["SYMBOL"].notna()
        & result["ISIN"].notna()
    ].copy()

    result = result.drop_duplicates(
        subset=["SYMBOL", "ISIN"]
    )

    return result.reset_index(drop=True)


def validate_universe(
    df: pd.DataFrame,
) -> dict:

    return {
        "rows": int(len(df)),
        "unique_symbols": int(
            df["SYMBOL"].nunique()
        ),
        "unique_isins": int(
            df["ISIN"].nunique()
        ),
        "missing_symbols": int(
            df["SYMBOL"].isna().sum()
        ),
        "missing_isins": int(
            df["ISIN"].isna().sum()
        ),
        "duplicate_symbol_count": int(
            df["SYMBOL"].duplicated().sum()
        ),
    }


def save_universe(
    df: pd.DataFrame,
    path: str = "data/universe/nse_equity_universe.csv",
) -> None:

    file_path = Path(path)

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        file_path,
        index=False,
    )