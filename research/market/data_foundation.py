from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "SYMBOL",
    "SERIES",
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
    "DATA_AVAILABLE",
}


PRICE_COLUMNS = [
    "OPNPRIC",
    "HGHPRIC",
    "LWPRIC",
    "CLSPRIC",
    "LASTPRIC",
    "PRVSCLSGPRIC",
]


POSITIVE_COLUMNS = [
    "OPNPRIC",
    "HGHPRIC",
    "LWPRIC",
    "CLSPRIC",
    "PRVSCLSGPRIC",
]


def validate_daily_schema(df: pd.DataFrame) -> dict:
    """Validate the structural schema of one normalized NSE session."""

    columns = set(df.columns)
    missing = sorted(REQUIRED_COLUMNS - columns)
    unexpected = sorted(columns - REQUIRED_COLUMNS)

    return {
        "valid": len(missing) == 0,
        "missing_columns": missing,
        "unexpected_columns": unexpected,
        "column_count": len(df.columns),
    }


def validate_daily_integrity(df: pd.DataFrame) -> dict:
    """Validate one normalized NSE market-data session."""

    schema = validate_daily_schema(df)

    result = {
        **schema,
        "rows": int(len(df)),
        "available_rows": None,
        "duplicate_isin": None,
        "invalid_prices": None,
        "negative_volume": None,
        "invalid_ohlc": None,
        "missing_close": None,
        "invalid_trade_value": None,
        "invalid_data_available": None,
        "non_finite_values": None,
        "no_available_rows": None,
        "integrity_valid": False,
    }

    if not schema["valid"]:
        return result

    flags = df["DATA_AVAILABLE"]

    valid_flags = flags.map(
        lambda value: isinstance(value, (bool, np.bool_))
    )

    result["invalid_data_available"] = int(
        (~valid_flags).sum()
    )

    if not valid_flags.all():
        return result

    available = df.loc[flags].copy()
    result["available_rows"] = int(len(available))

    # An empty session cannot establish data integrity.
    if available.empty:
        result["no_available_rows"] = 1
        return result

    result["no_available_rows"] = 0

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

    numeric = available[numeric_columns].apply(
        pd.to_numeric,
        errors="coerce",
    )

    values = numeric.to_numpy(dtype=float)

    result["non_finite_values"] = int(
        (~np.isfinite(values)).sum()
    )

    result["duplicate_isin"] = int(
        available["ISIN"].duplicated().sum()
    )

    prices = numeric[POSITIVE_COLUMNS]

    result["invalid_prices"] = int(
        (
            prices.isna().any(axis=1)
            | (~np.isfinite(prices)).any(axis=1)
            | prices.le(0).any(axis=1)
        ).sum()
    )

    volume = numeric["TTLTRADGVOL"]

    result["negative_volume"] = int(
        (volume < 0).sum()
    )

    trade_value = numeric["TTLTRFVAL"]

    result["invalid_trade_value"] = int(
        (trade_value < 0).sum()
    )

    high = numeric["HGHPRIC"]
    low = numeric["LWPRIC"]
    open_price = numeric["OPNPRIC"]
    close = numeric["CLSPRIC"]

    result["invalid_ohlc"] = int(
        (
            (high < low)
            | (high < open_price)
            | (high < close)
            | (low > open_price)
            | (low > close)
        ).sum()
    )

    result["missing_close"] = int(
        close.isna().sum()
    )

    checks = [
        result["duplicate_isin"],
        result["invalid_prices"],
        result["negative_volume"],
        result["invalid_ohlc"],
        result["missing_close"],
        result["invalid_trade_value"],
        result["invalid_data_available"],
        result["non_finite_values"],
        result["no_available_rows"],
    ]

    result["integrity_valid"] = all(
        count == 0 for count in checks
    )

    return result


def audit_normalized_directory(
    directory: str | Path = "data/market/normalized",
) -> pd.DataFrame:
    """Audit every normalized daily market-data file."""

    directory = Path(directory)

    files = sorted(
        directory.glob("market_*.parquet")
    )

    if not files:
        raise ValueError(
            f"No normalized market files found: {directory}"
        )

    records = []

    for path in files:
        df = pd.read_parquet(path)
        result = validate_daily_integrity(df)
        result["file"] = path.name
        records.append(result)

    return pd.DataFrame(records)


def summarize_directory_audit(
    audit: pd.DataFrame,
) -> dict:
    """Summarize normalized-data audit results."""

    if audit.empty:
        raise ValueError(
            "Cannot summarize an empty audit."
        )

    return {
        "files": int(len(audit)),
        "valid_files": int(
            audit["integrity_valid"].sum()
        ),
        "invalid_files": int(
            (~audit["integrity_valid"]).sum()
        ),
        "total_rows": int(
            audit["rows"].sum()
        ),
        "total_available_rows": int(
            audit["available_rows"].fillna(0).sum()
        ),
        "duplicate_isin_total": int(
            audit["duplicate_isin"].fillna(0).sum()
        ),
        "invalid_prices_total": int(
            audit["invalid_prices"].fillna(0).sum()
        ),
        "negative_volume_total": int(
            audit["negative_volume"].fillna(0).sum()
        ),
        "invalid_ohlc_total": int(
            audit["invalid_ohlc"].fillna(0).sum()
        ),
        "missing_close_total": int(
            audit["missing_close"].fillna(0).sum()
        ),
    }