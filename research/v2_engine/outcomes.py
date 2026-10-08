import pandas as pd
def add_forward_return(
    df: pd.DataFrame,
    horizon_days: int = 20,
) -> pd.DataFrame:
    """
    Add a future return column for research evaluation.
    The forward return is an outcome only.
    It must never be used to construct the signal.
    """
    if "Close" not in df.columns:
        raise ValueError("Missing required column: Close")
    if horizon_days <= 0:
        raise ValueError("horizon_days must be positive")
    result = df.copy()
    result[f"Forward_Return_{horizon_days}D"] = (
        result["Close"].shift(-horizon_days)
        / result["Close"]
    ) - 1
    return result
