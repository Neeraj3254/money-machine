from __future__ import annotations
from pathlib import Path
import pandas as pd
LEGACY_REQUIRED_COLUMNS = [
    "SYMBOL",
    "SERIES",
    "OPEN",
    "HIGH",
    "LOW",
    "CLOSE",
    "LAST",
    "PREVCLOSE",
    "TOTTRDQTY",
    "TOTTRDVAL",
    "TIMESTAMP",
    "TOTALTRADES",
    "ISIN",
]
LEGACY_TO_NORMALIZED = {
    "SYMBOL": "SYMBOL",
    "SERIES": "SERIES",
    "ISIN": "ISIN",
    "OPEN": "OPNPRIC",
    "HIGH": "HGHPRIC",
    "LOW": "LWPRIC",
    "CLOSE": "CLSPRIC",
    "LAST": "LASTPRIC",
    "PREVCLOSE": "PRVSCLSGPRIC",
    "TOTTRDQTY": "TTLTRADGVOL",
    "TOTTRDVAL": "TTLTRFVAL",
    "TOTALTRADES": "TTLNBOFTXSEXCTD",
}
def read_legacy_bhavcopy(path: str | Path) -> pd.DataFrame:
    """Read an NSE legacy Bhavcopy CSV."""
    df = pd.read_csv(path)
    df = df.dropna(axis=1, how="all")
    missing = [
        column
        for column in LEGACY_REQUIRED_COLUMNS
        if column not in df.columns
    ]
    if missing:
        raise ValueError(
            f"Legacy Bhavcopy missing required columns: {missing}"
        )
    return df
def normalize_legacy_bhavcopy(
    df: pd.DataFrame,
    equity_only: bool = True,
) -> pd.DataFrame:
    """Normalize legacy NSE Bhavcopy into Money Machine market schema."""
    df = df.copy()
    if equity_only:
        df = df[df["SERIES"].eq("EQ")].copy()
    normalized = df.rename(columns=LEGACY_TO_NORMALIZED)
    normalized["TRADE_DATE"] = pd.to_datetime(
        normalized["TIMESTAMP"],
        format="%d-%b-%Y",
        errors="raise",
    )
    normalized["DATA_AVAILABLE"] = True
    columns = [
        "SYMBOL",
        "SERIES",
        "ISIN",
        "OPNPRIC",
        "HGHPRIC",
        "LWPRIC",
        "CLSPRIC",
        "LASTPRIC",
        "PRVSCLSGPRIC",
        "TTLTRADGVOL",
        "TTLTRFVAL",
        "TTLNBOFTXSEXCTD",
        "TRADE_DATE",
        "DATA_AVAILABLE",
    ]
    return normalized[columns].reset_index(drop=True)
