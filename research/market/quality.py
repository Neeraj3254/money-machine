import pandas as pd


def validate_research_panel(df: pd.DataFrame) -> dict:
    """
    Run basic structural and market-data quality checks.
    """

    required_columns = [
        "TRADE_DATE",
        "SYMBOL",
        "ISIN",
        "CLSPRIC",
        "TTLTRADGVOL",
        "TTLTRFVAL",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    duplicate_rows = df.duplicated(
        subset=["TRADE_DATE", "ISIN"]
    ).sum()

    invalid_close = (
        pd.to_numeric(
            df["CLSPRIC"],
            errors="coerce",
        )
        <= 0
    ).sum()

    invalid_volume = (
        pd.to_numeric(
            df["TTLTRADGVOL"],
            errors="coerce",
        )
        < 0
    ).sum()

    invalid_trade_value = (
        pd.to_numeric(
            df["TTLTRFVAL"],
            errors="coerce",
        )
        < 0
    ).sum()

    observations_per_security = (
        df.groupby("ISIN")
        .size()
        .describe()
    )

    securities_with_20_days = (
        df.groupby("ISIN")
        .size()
        .ge(20)
        .sum()
    )

    securities_with_60_days = (
        df.groupby("ISIN")
        .size()
        .ge(60)
        .sum()
    )

    securities_with_120_days = (
        df.groupby("ISIN")
        .size()
        .ge(120)
        .sum()
    )

    return {
        "rows": len(df),
        "unique_isins": df["ISIN"].nunique(),
        "unique_symbols": df["SYMBOL"].nunique(),
        "duplicate_date_isin_rows": int(
            duplicate_rows
        ),
        "invalid_close_rows": int(
            invalid_close
        ),
        "invalid_volume_rows": int(
            invalid_volume
        ),
        "invalid_trade_value_rows": int(
            invalid_trade_value
        ),
        "securities_with_20_days": int(
            securities_with_20_days
        ),
        "securities_with_60_days": int(
            securities_with_60_days
        ),
        "securities_with_120_days": int(
            securities_with_120_days
        ),
        "observations_per_security": (
            observations_per_security.to_dict()
        ),
    }