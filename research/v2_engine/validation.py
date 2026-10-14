
import math
from dataclasses import replace

from .results import ExperimentResult


MINIMUM_SAMPLE_SIZE = 100

REQUIRED_METRICS = (
    "baseline_return",
    "signal_return",
    "incremental_return",
    "baseline_positive_rate",
    "signal_positive_rate",
    "incremental_positive_rate",
    "cost_adjusted_return",
    "oos_return",
    "oos_incremental_return",
    "parameter_stability",
    "cross_stock_consistency",
    "permutation_p_value",
)


def validate_experiment(result: ExperimentResult) -> ExperimentResult:
    """Validate evidence first where necessary, then enforce all gates."""

    # Cost evidence must be present and finite.
    cost_value = result.cost_adjusted_return

    if cost_value is None:
        return replace(
            result,
            status="INCONCLUSIVE",
            failure_reason=(
                "Missing/insufficient evidence: cost_adjusted_return"
            ),
        )

    if (
        isinstance(cost_value, bool)
        or not isinstance(cost_value, (int, float))
        or not math.isfinite(cost_value)
    ):
        return replace(
            result,
            status="INCONCLUSIVE",
            failure_reason="Invalid metric: cost_adjusted_return",
        )

    # Every validation gate must pass before promotion.
    gates = [
        ("leakage", result.leakage_passed),
        ("baseline", result.baseline_passed),
        ("cost", result.cost_passed),
        ("temporal stability", result.temporal_stability_passed),
        ("out-of-sample", result.oos_passed),
        ("robustness", result.robustness_passed),
        ("adversarial", result.adversarial_passed),
    ]

    failed_gates = [
        name for name, passed in gates if passed is not True
    ]

    if failed_gates:
        return replace(
            result,
            status="NOT_VALIDATED",
            failure_reason=(
                "Failed validation gates: "
                + ", ".join(failed_gates)
            ),
        )

    # Validate all required metrics.
    missing_metrics = []
    invalid_metrics = []

    for name in REQUIRED_METRICS:
        value = getattr(result, name)

        if value is None:
            missing_metrics.append(name)
        elif (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            invalid_metrics.append(name)

    # Sample size must be a genuine integer, not a bool or float.
    if (
        isinstance(result.sample_size, bool)
        or not isinstance(result.sample_size, int)
        or result.sample_size < MINIMUM_SAMPLE_SIZE
    ):
        missing_metrics.append(
            f"sample_size must be an integer >= {MINIMUM_SAMPLE_SIZE}"
        )

    # Probability metrics must lie between 0 and 1.
    for name in (
        "baseline_positive_rate",
        "signal_positive_rate",
        "permutation_p_value",
    ):
        value = getattr(result, name)

        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0 <= value <= 1
        ):
            invalid_metrics.append(name)

    # Incremental positive rate is a difference, so negative values
    # are valid. It must be finite, but need not lie in [0, 1].

    if missing_metrics or invalid_metrics:
        reasons = []

        if missing_metrics:
            reasons.append(
                "missing/insufficient evidence: "
                + ", ".join(sorted(set(missing_metrics)))
            )

        if invalid_metrics:
            reasons.append(
                "invalid metrics: "
                + ", ".join(sorted(set(invalid_metrics)))
            )

        return replace(
            result,
            status="INCONCLUSIVE",
            failure_reason="; ".join(reasons),
        )

    return replace(
        result,
        status="VALIDATED_RESEARCH_EDGE",
        failure_reason=None,
    )
