import numpy as np
import pandas as pd


def average_return(returns: pd.Series) -> float:
    """Calculate mean forward return."""

    clean = returns.dropna()

    if clean.empty:
        raise ValueError("No valid returns available.")

    return float(clean.mean())


def positive_rate(returns: pd.Series) -> float:
    """Calculate fraction of positive returns."""

    clean = returns.dropna()

    if clean.empty:
        raise ValueError("No valid returns available.")

    return float((clean > 0).mean())


def incremental_return(
    signal_returns: pd.Series,
    baseline_returns: pd.Series,
) -> float:
    """
    Calculate signal return minus baseline return.
    """

    signal_avg = average_return(signal_returns)
    baseline_avg = average_return(baseline_returns)

    return signal_avg - baseline_avg


def summarize_returns(
    signal_returns: pd.Series,
    baseline_returns: pd.Series,
) -> dict:
    """
    Produce standardized descriptive statistics.
    """

    signal_avg = average_return(signal_returns)
    baseline_avg = average_return(baseline_returns)

    signal_positive = positive_rate(signal_returns)
    baseline_positive = positive_rate(baseline_returns)

    return {
        "sample_size": int(signal_returns.dropna().shape[0]),
        "baseline_return": baseline_avg,
        "signal_return": signal_avg,
        "incremental_return": signal_avg - baseline_avg,
        "baseline_positive_rate": baseline_positive,
        "signal_positive_rate": signal_positive,
        "incremental_positive_rate": (
            signal_positive - baseline_positive
        ),
    }