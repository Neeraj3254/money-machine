import pandas as pd

from research.market.data_foundation import (
    summarize_directory_audit,
    validate_daily_integrity,
    validate_daily_schema,
)


def valid_frame():
    return pd.DataFrame(
        {
            "SYMBOL": ["TEST"],
            "SERIES": ["EQ"],
            "ISIN": ["INE000000000"],
            "TCKRSYMB": ["TEST"],
            "OPNPRIC": [100.0],
            "HGHPRIC": [105.0],
            "LWPRIC": [95.0],
            "CLSPRIC": [102.0],
            "LASTPRIC": [102.0],
            "PRVSCLSGPRIC": [99.0],
            "TTLTRADGVOL": [10000.0],
            "TTLTRFVAL": [1000000.0],
            "TTLNBOFTXSEXCTD": [100.0],
            "DATA_AVAILABLE": [True],
        }
    )


def test_schema_accepts_valid_frame():
    result = validate_daily_schema(valid_frame())

    assert result["valid"] is True
    assert result["missing_columns"] == []


def test_integrity_accepts_valid_frame():
    result = validate_daily_integrity(valid_frame())

    assert result["integrity_valid"] is True
    assert result["duplicate_isin"] == 0
    assert result["invalid_prices"] == 0
    assert result["negative_volume"] == 0
    assert result["invalid_ohlc"] == 0
    assert result["missing_close"] == 0


def test_duplicate_isin_is_rejected():
    df = pd.concat(
        [valid_frame(), valid_frame()],
        ignore_index=True,
    )

    result = validate_daily_integrity(df)

    assert result["duplicate_isin"] == 1
    assert result["integrity_valid"] is False


def test_invalid_ohlc_is_rejected():
    df = valid_frame()
    df.loc[0, "HGHPRIC"] = 90.0

    result = validate_daily_integrity(df)

    assert result["invalid_ohlc"] == 1
    assert result["integrity_valid"] is False


def test_negative_volume_is_rejected():
    df = valid_frame()
    df.loc[0, "TTLTRADGVOL"] = -1

    result = validate_daily_integrity(df)

    assert result["negative_volume"] == 1
    assert result["integrity_valid"] is False


def test_missing_schema_column_is_rejected():
    df = valid_frame().drop(columns=["CLSPRIC"])

    result = validate_daily_schema(df)

    assert result["valid"] is False
    assert "CLSPRIC" in result["missing_columns"]


def test_audit_summary():
    audit = pd.DataFrame(
        [
            {
                "integrity_valid": True,
                "rows": 10,
                "available_rows": 8,
                "duplicate_isin": 0,
                "invalid_prices": 0,
                "negative_volume": 0,
                "invalid_ohlc": 0,
                "missing_close": 0,
            }
        ]
    )

    result = summarize_directory_audit(audit)

    assert result["files"] == 1
    assert result["valid_files"] == 1
    assert result["invalid_files"] == 0
    assert result["total_rows"] == 10
    assert result["total_available_rows"] == 8


def test_unexpected_schema_column_is_reported():
    df = valid_frame()
    df["UNEXPECTED_COLUMN"] = ["extra"]

    result = validate_daily_schema(df)

    assert result["unexpected_columns"] == ["UNEXPECTED_COLUMN"]


def test_non_finite_close_is_rejected():
    df = valid_frame()
    df.loc[0, "CLSPRIC"] = float("inf")

    result = validate_daily_integrity(df)

    assert result["integrity_valid"] is False


def test_negative_trade_value_is_rejected():
    df = valid_frame()
    df.loc[0, "TTLTRFVAL"] = -1

    result = validate_daily_integrity(df)

    assert result["integrity_valid"] is False
    assert result["invalid_trade_value"] == 1


def test_invalid_data_available_flag_is_rejected():
    df = valid_frame()
    df["DATA_AVAILABLE"] = ["unknown"]

    result = validate_daily_integrity(df)

    assert result["integrity_valid"] is False
    assert result["invalid_data_available"] == 1

def test_empty_available_session_is_rejected():
    df = valid_frame()
    df["DATA_AVAILABLE"] = False

    result = validate_daily_integrity(df)

    assert result["available_rows"] == 0
    assert result["no_available_rows"] == 1
    assert result["integrity_valid"] is False