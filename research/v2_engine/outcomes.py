import pandas as pd


def add_forward_return(
    df: pd.DataFrame,
    horizon_days: int = 20,
) -> pd.DataFrame:
    """
    Add a future return outcome without changing row order.

    TARGET_DATE identifies the actual future observation used
    to calculate the forward return.
    """
    if "Close" not in df.columns:
        raise ValueError("Missing required column: Close")

    if horizon_days <= 0:
        raise ValueError("horizon_days must be positive")

    result = df.copy()

    if "Date" in result.columns:
        dates = pd.to_datetime(result["Date"], errors="raise")

        if dates.isna().any():
            raise ValueError("Date values cannot be missing")

        if not dates.is_monotonic_increasing:
            raise ValueError(
                "Date values must be in chronological order"
            )

        if dates.duplicated().any():
            raise ValueError("Date values must not contain duplicates")

        result["Date"] = dates
        result["TARGET_DATE"] = dates.shift(-horizon_days)

    result[f"Forward_Return_{horizon_days}D"] = (
        result["Close"].shift(-horizon_days) / result["Close"]
    ) - 1

    return result
