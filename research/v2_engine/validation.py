from dataclasses import replace

from .results import ExperimentResult


def validate_experiment(result: ExperimentResult) -> ExperimentResult:
    """
    Apply the standard V2 research promotion gate.

    This function evaluates evidence.
    It does not create a trading signal.
    """

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
        name
        for name, passed in gates
        if not passed
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

    return replace(
        result,
        status="VALIDATED_RESEARCH_EDGE",
        failure_reason=None,
    )