from dataclasses import replace
import pytest
from research.v2_engine.results import ExperimentResult
from research.v2_engine.validation import validate_experiment
GATES = (
    "leakage_passed",
    "baseline_passed",
    "cost_passed",
    "temporal_stability_passed",
    "oos_passed",
    "robustness_passed",
    "adversarial_passed",
)
def make_result(**overrides):
    result = ExperimentResult(
        experiment_id="TEST-VALIDATION-CONTROL",
        hypothesis="Adversarial validation-control regression test",
        sample_size=100,
        leakage_passed=True,
        baseline_passed=True,
        cost_passed=True,
        temporal_stability_passed=True,
        oos_passed=True,
        robustness_passed=True,
        adversarial_passed=True,
    )
    return replace(result, **overrides)
@pytest.mark.parametrize("failed_gate", GATES)
def test_failed_gate_can_never_promote_to_validated(failed_gate):
    result = make_result(**{failed_gate: False})
    validated = validate_experiment(result)
    assert validated.status == "NOT_VALIDATED"
    assert validated.status != "VALIDATED_RESEARCH_EDGE"
    assert validated.failure_reason is not None
    assert validated.failure_reason.startswith("Failed validation gates:")
def test_all_required_gates_passing_can_promote_to_validated():
    result = make_result()
    validated = validate_experiment(result)
    assert validated.status == "VALIDATED_RESEARCH_EDGE"
    assert validated.failure_reason is None
