
import pandas as pd


def split_train_test(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    purge_periods: int = 0,
    label_horizon: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Chronological train/test split.

    purge_periods removes the final training rows before the test
    boundary. When label_horizon is specified, the purge must be at
    least as large as the forward-label horizon, measured in rows.

    label_horizon defaults to zero for backward compatibility.
    """
    if (
        isinstance(train_ratio, bool)
        or not isinstance(train_ratio, (int, float))
        or not 0 < train_ratio < 1
    ):
        raise ValueError("train_ratio must be between 0 and 1")

    if (
        isinstance(purge_periods, bool)
        or not isinstance(purge_periods, int)
        or purge_periods < 0
    ):
        raise ValueError("purge_periods must be a non-negative integer")

    if (
        isinstance(label_horizon, bool)
        or not isinstance(label_horizon, int)
        or label_horizon < 0
    ):
        raise ValueError("label_horizon must be a non-negative integer")

    if purge_periods < label_horizon:
        raise ValueError(
            "purge_periods must be at least label_horizon"
        )

    result = df.copy()

    if "Date" in result.columns:
        result["Date"] = pd.to_datetime(
            result["Date"], errors="raise"
        )
        result = result.sort_values("Date", kind="stable")

    split_index = int(len(result) * train_ratio)

    if split_index <= 0 or split_index >= len(result):
        raise ValueError(
            "Not enough rows for a non-empty train/test split"
        )

    train_end = split_index - purge_periods

    if train_end <= 0:
        raise ValueError("Purge leaves no training rows")

    train = result.iloc[:train_end].copy()
    test = result.iloc[split_index:].copy()

    return train, test


def evaluate_oos(
    test_df: pd.DataFrame,
    signal_column: str,
    forward_return_column: str,
) -> dict:
    """Evaluate signal returns against non-signal controls."""

    if signal_column not in test_df.columns:
        raise ValueError(
            f"Missing signal column: {signal_column}"
        )

    if forward_return_column not in test_df.columns:
        raise ValueError(
            f"Missing forward-return column: {forward_return_column}"
        )

    signal_mask = test_df[signal_column].eq(True).fillna(False)

    returns = pd.to_numeric(
        test_df[forward_return_column],
        errors="coerce",
    )

    eligible = returns.notna()

    signal_returns = returns.loc[eligible & signal_mask]
    control_returns = returns.loc[eligible & ~signal_mask]
    baseline_returns = returns.loc[eligible]

    if signal_returns.empty:
        raise ValueError(
            "No valid signal observations in OOS data."
        )

    if control_returns.empty:
        raise ValueError(
            "No valid non-signal control observations in OOS data."
        )

    signal_return = float(signal_returns.mean())
    control_return = float(control_returns.mean())
    baseline_return = float(baseline_returns.mean())

    return {
        "sample_size": int(len(signal_returns)),
        "control_sample_size": int(len(control_returns)),
        "baseline_return": baseline_return,
        "oos_return": signal_return,
        "control_return": control_return,
        "oos_incremental_return": (
            signal_return - baseline_return
        ),
        "signal_vs_control_incremental_return": (
            signal_return - control_return
        ),
        "baseline_positive_rate": float(
            (baseline_returns > 0).mean()
        ),
        "oos_positive_rate": float(
            (signal_returns > 0).mean()
        ),
        "control_positive_rate": float(
            (control_returns > 0).mean()
        ),
    }
