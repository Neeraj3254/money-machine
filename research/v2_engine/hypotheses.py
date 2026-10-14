from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Hypothesis:
    """
    Defines one research hypothesis.

    A hypothesis describes what we want to test.
    It does not execute trades.
    """

    experiment_id: str
    name: str
    family: str
    description: str
    feature_builder: str
    signal_definition: str
    forward_horizon_days: int
    status: str = "REGISTERED"


HYPOTHESES = [
    Hypothesis(
        experiment_id="V2-002",
        name="Trend Strength",
        family="Trend",
        description=(
            "Test whether stronger trend alignment contains "
            "incremental information about future returns."
        ),
        feature_builder="trend_strength",
        signal_definition=(
            "Trend-strength feature exceeds the predefined threshold."
        ),
        forward_horizon_days=20,
    ),

    Hypothesis(
        experiment_id="V2-003",
        name="Volatility-Adjusted Momentum",
        family="Momentum",
        description=(
            "Test whether momentum normalized by recent volatility "
            "contains incremental predictive information."
        ),
        feature_builder="volatility_adjusted_momentum",
        signal_definition=(
            "Volatility-adjusted momentum exceeds the predefined threshold."
        ),
        forward_horizon_days=20,
    ),

    Hypothesis(
        experiment_id="V2-004",
        name="Volume Confirmation",
        family="Volume",
        description=(
            "Test whether price momentum accompanied by unusual "
            "volume contains incremental predictive information."
        ),
        feature_builder="volume_confirmation",
        signal_definition=(
            "Momentum is confirmed by the predefined volume condition."
        ),
        forward_horizon_days=20,
    ),

    Hypothesis(
        experiment_id="V2-005",
        name="Mean Reversion",
        family="Mean Reversion",
        description=(
            "Test whether unusually extended short-term price moves "
            "tend to partially reverse over the forward horizon."
        ),
        feature_builder="mean_reversion",
        signal_definition=(
            "The predefined short-term deviation condition is satisfied."
        ),
        forward_horizon_days=20,
    ),

    Hypothesis(
        experiment_id="V2-006",
        name="Market Breadth / Regime Context",
        family="Market Regime",
        description=(
            "Test whether market breadth or regime context changes "
            "the conditional distribution of future stock returns."
        ),
        feature_builder="market_breadth_regime",
        signal_definition=(
            "The predefined breadth/regime condition is satisfied."
        ),
        forward_horizon_days=20,
    ),
]


def get_hypothesis(experiment_id: str) -> Hypothesis:
    """
    Return a registered hypothesis by experiment ID.
    """

    for hypothesis in HYPOTHESES:
        if hypothesis.experiment_id == experiment_id:
            return hypothesis

    raise ValueError(
        f"Unknown experiment ID: {experiment_id}"
    )


def list_hypotheses() -> list[Hypothesis]:
    """
    Return all registered hypotheses.
    """

    return list(HYPOTHESES)