import pandas as pd


def split_train_test(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    """
    Split time-series data chronologically into
    training and out-of-sample test periods.

    No randomization is used.
    """

    if not 0 < train_ratio < 1:
        raise ValueError(
            "train_ratio must be between 0 and 1"
        )

    result = df.copy()

    if "Date" in result.columns:
        result["Date"] = pd.to_datetime(result["Date"])
        result = result.sort_values("Date")

    split_index = int(len(result) * train_ratio)

    train = result.iloc[:split_index].copy()
    test = result.iloc[split_index:].copy()

    return train, test

def evaluate_oos(
    test_df: pd.DataFrame,
    signal_column: str,
    forward_return_column: str,
) -> dict:
    """
    Evaluate a frozen signal on out-of-sample data.

    The test data is evaluated without changing
    the signal definition.
    """

    if signal_column not in test_df.columns:
        raise ValueError(
            f"Missing signal column: {signal_column}"
        )

    if forward_return_column not in test_df.columns:
        raise ValueError(
            f"Missing forward-return column: "
            f"{forward_return_column}"
        )

    eligible = test_df[forward_return_column].notna()

    signal_returns = test_df.loc[
        eligible & test_df[signal_column],
        forward_return_column,
    ]

    baseline_returns = test_df.loc[
        eligible,
        forward_return_column,
    ]

    if signal_returns.empty:
        raise ValueError(
            "No valid signal observations in OOS data."
        )

    signal_return = float(signal_returns.mean())
    baseline_return = float(baseline_returns.mean())

    return {
        "sample_size": int(signal_returns.shape[0]),
        "baseline_return": baseline_return,
        "oos_return": signal_return,
        "oos_incremental_return": (
            signal_return - baseline_return
        ),
        "baseline_positive_rate": float(
            (baseline_returns > 0).mean()
        ),
        "oos_positive_rate": float(
            (signal_returns > 0).mean()
        ),
    }
