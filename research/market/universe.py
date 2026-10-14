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



def validate_universe(df: pd.DataFrame) -> dict:
    """Validate an EQ-only universe before it is saved or used."""

    required_columns = ["SYMBOL", "SERIES", "ISIN"]
    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Universe is missing columns: {missing_columns}"
        )

    result = df[required_columns].copy()

    for column in required_columns:
        result[column] = (
            result[column]
            .astype("string")
            .str.strip()
            .str.upper()
        )

    invalid_values = {"", "NAN", "NONE", "NULL", "<NA>"}

    for column in required_columns:
        invalid = (
            result[column].isna()
            | result[column].isin(invalid_values)
        )
        if invalid.any():
            raise ValueError(
                f"Universe contains missing or invalid {column} values"
            )

    if not result["SERIES"].eq("EQ").all():
        raise ValueError("Universe must contain only EQ-series records")

    if result["SYMBOL"].duplicated().any():
        raise ValueError("Universe contains duplicate symbols")

    if result["ISIN"].duplicated().any():
        raise ValueError("Universe contains duplicate ISINs")

    return {
        "rows": int(len(result)),
        "unique_symbols": int(result["SYMBOL"].nunique()),
        "unique_isins": int(result["ISIN"].nunique()),
        "missing_symbols": 0,
        "missing_isins": 0,
        "duplicate_symbol_count": 0,
    }


def save_universe(
    df: pd.DataFrame,
    path: str = "data/universe/nse_equity_universe.csv",
) -> None:
    """Validate and atomically save the EQ-only universe."""

    import os
    import tempfile

    validate_universe(df)

    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            suffix=".tmp",
            prefix=f"{file_path.stem}_",
            dir=file_path.parent,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            df.to_csv(temporary_file, index=False)

        os.replace(temporary_path, file_path)

    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()