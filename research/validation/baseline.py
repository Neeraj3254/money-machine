from __future__ import annotations

import pandas as pd


V2_007A_CONFIG = {
    "experiment_id": "V2-007A",
    "hypothesis": "BEAR_HIGH_VOL weak-momentum reversal",
    "regime": "BEAR_HIGH_VOL",
    "signal_quantile": 1,
    "control_quantile": 5,
    "momentum_feature": "Return_20D",
    "outcome": "next_session_return",
    "liquidity_threshold": 10_000_000,
    "cost_per_turnover": 0.001,
}


def compare_group_returns(
    df: pd.DataFrame,
    group_col: str,
    return_col: str,
) -> pd.DataFrame:
    """
    Compare mean and median returns across predefined groups.
    """

    required = [group_col, return_col]

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    result = (
        df.dropna(subset=[return_col])
        .groupby(group_col)[return_col]
        .agg(
            observations="count",
            mean_return="mean",
            median_return="median",
            positive_rate=lambda x: (x > 0).mean(),
        )
        .reset_index()
    )

    return result


def validate_v2_007a_config() -> dict:
    """
    Validate the V2-007A experiment definition.
    """

    required = [
        "experiment_id",
        "hypothesis",
        "regime",
        "signal_quantile",
        "control_quantile",
        "momentum_feature",
        "outcome",
        "liquidity_threshold",
        "cost_per_turnover",
    ]

    missing = [
        key
        for key in required
        if key not in V2_007A_CONFIG
    ]

    if missing:
        raise ValueError(
            f"Missing experiment configuration: {missing}"
        )

    if (
        V2_007A_CONFIG["signal_quantile"]
        == V2_007A_CONFIG["control_quantile"]
    ):
        raise ValueError(
            "Signal and control quantiles must differ."
        )

    if V2_007A_CONFIG["liquidity_threshold"] <= 0:
        raise ValueError(
            "Liquidity threshold must be positive."
        )

    if V2_007A_CONFIG["cost_per_turnover"] < 0:
        raise ValueError(
            "Transaction cost cannot be negative."
        )

    return V2_007A_CONFIG


def prepare_v2_007a_dataset(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepare the common eligible universe for V2-007A.

    Every comparison uses exactly the same:

    - regime
    - liquidity threshold
    - valid next-session outcome
    - valid momentum signal
    """

    required = [
        "TRADE_DATE",
        "ISIN",
        "SYMBOL",
        "Regime",
        "Return_20D",
        "NEXT_RETURN_1D",
        "TTLTRFVAL",
    ]

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    result = df.copy()

    result["TRADE_DATE"] = pd.to_datetime(
        result["TRADE_DATE"]
    )

    # --------------------------------------------------
    # 1. Regime filter
    # --------------------------------------------------

    result = result[
        result["Regime"]
        == V2_007A_CONFIG["regime"]
    ].copy()

    # --------------------------------------------------
    # 2. Liquidity filter
    # --------------------------------------------------

    result = result[
        result["TTLTRFVAL"]
        >= V2_007A_CONFIG["liquidity_threshold"]
    ].copy()

    # --------------------------------------------------
    # 3. Valid next-session outcome
    # --------------------------------------------------

    result = result[
        result["NEXT_RETURN_1D"].notna()
    ].copy()

    # --------------------------------------------------
    # 4. Valid momentum signal
    # --------------------------------------------------

    result = result[
        result["Return_20D"].notna()
    ].copy()

    return result.reset_index(drop=True)

def calculate_v2_007a_baseline(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate the gross next-session return baseline
    for Q1, Q5, and the full eligible market universe.

    All groups come from the same prepared universe.
    """

    required = [
        "TRADE_DATE",
        "Momentum_Quantile",
        "NEXT_RETURN_1D",
    ]

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    result = df.copy()

    # Q1: weak momentum
    q1 = (
        result[
            result["Momentum_Quantile"]
            == V2_007A_CONFIG["signal_quantile"]
        ]
        .groupby("TRADE_DATE")["NEXT_RETURN_1D"]
        .mean()
        .rename("Q1")
    )

    # Q5: strong momentum
    q5 = (
        result[
            result["Momentum_Quantile"]
            == V2_007A_CONFIG["control_quantile"]
        ]
        .groupby("TRADE_DATE")["NEXT_RETURN_1D"]
        .mean()
        .rename("Q5")
    )

    # Full eligible universe
    market = (
        result
        .groupby("TRADE_DATE")["NEXT_RETURN_1D"]
        .mean()
        .rename("MARKET")
    )

    comparison = pd.concat(
        [q1, q5, market],
        axis=1,
    )

    comparison["Q1_MINUS_Q5"] = (
        comparison["Q1"]
        - comparison["Q5"]
    )

    comparison["Q1_MINUS_MARKET"] = (
        comparison["Q1"]
        - comparison["MARKET"]
    )

    return comparison.reset_index()

def summarize_v2_007a_spread(
    baseline: pd.DataFrame,
) -> dict:
    """
    Summarize the daily Q1-minus-Q5 spread.

    The unit of analysis is the research day.
    """

    required = [
        "TRADE_DATE",
        "Q1_MINUS_Q5",
    ]

    missing = [
        col
        for col in required
        if col not in baseline.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    spread = (
        baseline["Q1_MINUS_Q5"]
        .dropna()
        .astype(float)
    )

    n = len(spread)

    if n == 0:
        raise ValueError(
            "No valid spread observations."
        )

    mean = spread.mean()
    median = spread.median()
    std = spread.std(ddof=1)

    standard_error = (
        std / (n ** 0.5)
        if n > 1
        else float("nan")
    )

    # Approximate 95% normal confidence interval.
    ci_low = (
        mean - 1.96 * standard_error
        if n > 1
        else float("nan")
    )

    ci_high = (
        mean + 1.96 * standard_error
        if n > 1
        else float("nan")
    )

    return {
        "days": n,
        "mean_spread": mean,
        "median_spread": median,
        "std_spread": std,
        "standard_error": standard_error,
        "ci_95_low": ci_low,
        "ci_95_high": ci_high,
        "positive_spread_rate": (spread > 0).mean(),
        "negative_spread_rate": (spread < 0).mean(),
        "best_day": spread.max(),
        "worst_day": spread.min(),
    }