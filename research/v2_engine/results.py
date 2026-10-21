from dataclasses import dataclass
from typing import Optional


@dataclass
class ExperimentResult:
    """
    Standardized result produced by a V2 research experiment.

    This object records evidence.
    It does not make trading decisions.
    """

    experiment_id: str
    hypothesis: str

    sample_size: int

    baseline_return: Optional[float] = None
    signal_return: Optional[float] = None
    incremental_return: Optional[float] = None

    baseline_positive_rate: Optional[float] = None
    signal_positive_rate: Optional[float] = None
    incremental_positive_rate: Optional[float] = None

    cost_adjusted_return: Optional[float] = None

    oos_return: Optional[float] = None
    oos_incremental_return: Optional[float] = None

    parameter_stability: Optional[float] = None
    cross_stock_consistency: Optional[float] = None

    permutation_p_value: Optional[float] = None

    leakage_passed: bool = False
    baseline_passed: bool = False
    cost_passed: bool = False
    temporal_stability_passed: bool = False
    oos_passed: bool = False
    robustness_passed: bool = False
    adversarial_passed: bool = False

    status: str = "UNVALIDATED"
    failure_reason: Optional[str] = None