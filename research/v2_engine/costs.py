import pandas as pd
def cost_adjusted_return(
    returns: pd.Series,
    cost_per_trade: float,
) -> float:
    """
    Calculate average return after applying a fixed cost per trade.
    cost_per_trade is expressed as a decimal.
    Example:
        0.001 = 0.10%
        0.002 = 0.20%
    """
    if cost_per_trade < 0:
        raise ValueError("cost_per_trade cannot be negative")
    clean = returns.dropna()
    if clean.empty:
        raise ValueError("No valid returns available.")
    adjusted = clean - cost_per_trade
    return float(adjusted.mean())
