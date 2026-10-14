import numpy as np
import pandas as pd

from .metrics import summarize_returns


def split_time_periods(
    df: pd.DataFrame,
    periods: int = 3,
) -> list[pd.DataFrame]:
    """Split a time series into chronological periods without randomization."""

    if periods < 2:
        raise ValueError("periods must be at least 2")

    result = df.copy()

    if "Date" in result.columns:
        result["Date"] = pd.to_datetime(result["Date"])

        if result["Date"].isna().any():
            raise ValueError("Date column contains invalid values")

        if result["Date"].duplicated().any():
            raise ValueError("Date column contains duplicate dates")

        result = result.sort_values("Date", kind="stable")

    indices = np.array_split(np.arange(len(result)), periods)

    return [
        result.iloc[index].copy()
        for index in indices
        if len(index) > 0
    ]


def evaluate_period(
    df: pd.DataFrame,
    signal_column: str,
    forward_return_column: str,
) -> dict:
    """Compare signal returns against eligible non-signal controls."""

    if signal_column not in df.columns:
        raise ValueError(f"Missing signal column: {signal_column}")

    if forward_return_column not in df.columns:
        raise ValueError(
            f"Missing forward-return column: {forward_return_column}"
        )

    eligible = df[forward_return_column].notna()
    signal_mask = df[signal_column].eq(True).fillna(False)

    signal_returns = df.loc[
        eligible & signal_mask,
        forward_return_column,
    ].astype(float)

    control_returns = df.loc[
        eligible & ~signal_mask,
        forward_return_column,
    ].astype(float)

    if signal_returns.empty:
        raise ValueError("No valid signal observations in period.")

    if control_returns.empty:
        raise ValueError(
            "No valid non-signal control observations in period."
        )

    metrics = summarize_returns(
        signal_returns=signal_returns,
        baseline_returns=control_returns,
    )

    metrics["control_sample_size"] = int(len(control_returns))
    return metrics


def evaluate_time_stability(
    df: pd.DataFrame,
    signal_column: str,
    forward_return_column: str,
    periods: int = 3,
) -> list[dict]:
    """Evaluate the same signal against controls in chronological periods."""

    time_periods = split_time_periods(df, periods=periods)
    results = []

    for period_number, period_df in enumerate(time_periods, start=1):
        metrics = evaluate_period(
            period_df,
            signal_column=signal_column,
            forward_return_column=forward_return_column,
        )

        metrics["period"] = period_number

        if "Date" in period_df.columns and not period_df.empty:
            metrics["start_date"] = period_df["Date"].iloc[0]
            metrics["end_date"] = period_df["Date"].iloc[-1]

        results.append(metrics)

    return results


def summarize_time_stability(
    results: list[dict],
) -> dict:
    """Summarize incremental returns across chronological periods."""

    if not results:
        raise ValueError("At least one period result is required")

    incremental_returns = [
        float(result["incremental_return"])
        for result in results
    ]

    positive_periods = sum(
        value > 0 for value in incremental_returns
    )

    return {
        "periods": len(results),
        "positive_periods": positive_periods,
        "negative_periods": len(results) - positive_periods,
        "min_incremental_return": min(incremental_returns),
        "max_incremental_return": max(incremental_returns),
        "all_periods_positive": positive_periods == len(results),
    }
