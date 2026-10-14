import pandas as pd

from .metrics import summarize_returns
from .results import ExperimentResult
from .hypotheses import get_hypothesis
from .costs import cost_adjusted_return


def run_basic_experiment(
    experiment_id: str,
    signal_returns: pd.Series,
    baseline_returns: pd.Series,
) -> ExperimentResult:
    """
    Run the basic descriptive stage of a V2 experiment.


    This function calculates evidence.
    It does not decide whether a strategy is tradable.
    """

    hypothesis = get_hypothesis(experiment_id)

    summary = summarize_returns(
        signal_returns=signal_returns,
        baseline_returns=baseline_returns,
    )

    return ExperimentResult(
        experiment_id=experiment_id,
        hypothesis=hypothesis.name,
        sample_size=summary["sample_size"],
        baseline_return=summary["baseline_return"],
        signal_return=summary["signal_return"],
        incremental_return=summary["incremental_return"],
        baseline_positive_rate=summary["baseline_positive_rate"],
        signal_positive_rate=summary["signal_positive_rate"],
        incremental_positive_rate=summary[
            "incremental_positive_rate"
        ],
    )


def run_dataframe_experiment(
    experiment_id: str,
    df: pd.DataFrame,
    signal_column: str,
    forward_return_column: str,
    cost_per_trade: float = 0.001,
) -> ExperimentResult:
    """
    Run a registered experiment from a prepared research DataFrame.

    The DataFrame must already contain:
    - a signal column
    - a forward-return column

    This function performs descriptive evaluation only.
    It does not validate or promote the hypothesis.
    """

    if signal_column not in df.columns:
        raise ValueError(
            f"Missing signal column: {signal_column}"
        )

    if forward_return_column not in df.columns:
        raise ValueError(
            f"Missing forward-return column: "
            f"{forward_return_column}"
        )


    eligible = df[forward_return_column].notna()
    signal_mask = df[signal_column].eq(True).fillna(False)

    signal_returns = df.loc[
        eligible & signal_mask,
        forward_return_column,
    ].astype(float)

    # Independent descriptive control: eligible observations
    # where the signal is not active.
    baseline_returns = df.loc[
        eligible & ~signal_mask,
        forward_return_column,
    ].astype(float)

    if signal_returns.empty:
        raise ValueError("No valid observations for the signal.")

    if baseline_returns.empty:
        raise ValueError(
            "No valid non-signal control observations."
        )

    if signal_returns.empty:
        raise ValueError(
            "No valid observations for the signal."
        )

    result = run_basic_experiment(
        experiment_id=experiment_id,
        signal_returns=signal_returns,
        baseline_returns=baseline_returns,
    )

    result.cost_adjusted_return = cost_adjusted_return(
        signal_returns,
        cost_per_trade,
    )

    return result