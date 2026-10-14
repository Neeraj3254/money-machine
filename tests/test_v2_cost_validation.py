import math
from dataclasses import replace

from research.v2_engine.results import ExperimentResult
from research.v2_engine.validation import validate_experiment


def make_result(**overrides):
    result = ExperimentResult(
        experiment_id="V2-002",
        hypothesis="Trend Strength",
        sample_size=200,
        cost_adjusted_return=0.01,
    )
    return replace(result, **overrides)


def test_cost_gate_defaults_to_not_passed():
    result = make_result()

    validated = validate_experiment(result)

    assert validated.cost_passed is False
    assert validated.status == "NOT_VALIDATED"


def test_cost_gate_does_not_allow_manual_promotion_with_missing_evidence():
    result = make_result(
        cost_passed=True,
        cost_adjusted_return=None,
    )

    validated = validate_experiment(result)

    assert validated.status == "INCONCLUSIVE"
    assert "cost_adjusted_return" in validated.failure_reason


def test_cost_gate_does_not_allow_non_finite_cost_evidence():
    result = make_result(
        cost_passed=True,
        cost_adjusted_return=math.nan,
    )

    validated = validate_experiment(result)

    assert validated.status == "INCONCLUSIVE"
    assert "cost_adjusted_return" in validated.failure_reason
