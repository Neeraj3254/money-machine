from __future__ import annotations

import pandas as pd


def apply_transaction_cost(
    returns: pd.Series,
    turnover: pd.Series,
    cost_per_turnover: float = 0.001,
) -> pd.Series:
    """
    Convert gross portfolio returns into net returns
    after transaction costs.
    """

    if cost_per_turnover < 0:
        raise ValueError(
            "cost_per_turnover cannot be negative."
        )

    returns = pd.to_numeric(
        returns,
        errors="coerce",
    )

    turnover = pd.to_numeric(
        turnover,
        errors="coerce",
    )

    if len(returns) != len(turnover):
        raise ValueError(
            "returns and turnover must have the same length."
        )

    transaction_cost = (
        turnover * cost_per_turnover
    )

    return returns - transaction_cost


def summarize_cost_impact(
    portfolio: pd.DataFrame,
    name: str,
    cost_per_turnover: float = 0.001,
) -> dict:
    """
    Compare gross and net portfolio performance
    after transaction costs.
    """

    required = [
        "GROSS_RETURN",
        "TURNOVER",
    ]

    missing = [
        column
        for column in required
        if column not in portfolio.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    df = portfolio.copy()

    df["NET_RETURN_TEST"] = apply_transaction_cost(
        df["GROSS_RETURN"],
        df["TURNOVER"],
        cost_per_turnover,
    )

    gross = df["GROSS_RETURN"].dropna()
    net = df["NET_RETURN_TEST"].dropna()

    return {
        "name": name,
        "days": len(df),
        "cost_per_turnover": cost_per_turnover,
        "mean_gross": float(gross.mean()),
        "mean_net": float(net.mean()),
        "mean_cost": float(
            (gross - net).mean()
        ),
        "median_net": float(net.median()),
        "positive_net_rate": float(
            (net > 0).mean()
        ),
        "best_net": float(net.max()),
        "worst_net": float(net.min()),
    }
