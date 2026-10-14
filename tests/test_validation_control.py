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
        hypothesis="Validation-control regression test",
        sample_size=500,
        baseline_return=0.01,
        signal_return=0.02,
        incremental_return=0.01,
        baseline_positive_rate=0.51,
        signal_positive_rate=0.55,
        incremental_positive_rate=0.04,
        cost_adjusted_return=0.015,
        oos_return=0.018,
        oos_incremental_return=0.008,
        parameter_stability=0.8,
        cross_stock_consistency=0.7,
        permutation_p_value=0.02,
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
    validated = validate_experiment(make_result(**{failed_gate: False}))
    assert validated.status == "NOT_VALIDATED"
    assert validated.failure_reason.startswith("Failed validation gates:")
def test_all_gates_and_complete_metrics_allow_promotion():
    validated = validate_experiment(make_result())
    assert validated.status == "VALIDATED_RESEARCH_EDGE"
    assert validated.failure_reason is None
def test_missing_metric_is_inconclusive():
    validated = validate_experiment(make_result(oos_return=None))
    assert validated.status == "INCONCLUSIVE"
    assert "oos_return" in validated.failure_reason
def test_small_sample_is_inconclusive():
    validated = validate_experiment(make_result(sample_size=99))
    assert validated.status == "INCONCLUSIVE"
    assert "sample_size" in validated.failure_reason
def test_non_finite_metric_is_inconclusive():
    validated = validate_experiment(make_result(permutation_p_value=float("nan")))
    assert validated.status == "INCONCLUSIVE"
    assert "permutation_p_value" in validated.failure_reason
def test_out_of_range_probability_is_inconclusive():
    validated = validate_experiment(make_result(permutation_p_value=1.5))
    assert validated.status == "INCONCLUSIVE"
    assert "permutation_p_value" in validated.failure_reason
def test_negative_incremental_positive_rate_is_valid_difference():
    validated = validate_experiment(
        make_result(incremental_positive_rate=-0.04)
    )
    assert validated.status == "VALIDATED_RESEARCH_EDGE"

@pytest.mark.parametrize("sample_size", [True, 100.5, -1, 99])
def test_invalid_sample_size_is_inconclusive(sample_size):
    validated = validate_experiment(
        make_result(sample_size=sample_size)
    )
    assert validated.status == "INCONCLUSIVE"
    assert "sample_size" in validated.failure_reason
