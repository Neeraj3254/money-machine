from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ValidationResult:
    """
    Standard result for one validation gate.

    Each validation module should return this object so that
    all experiments use the same reporting structure.
    """

    name: str

    status: str
    # Expected values:
    # PASS
    # FAIL
    # INCONCLUSIVE
    # NOT_RUN

    passed: Optional[bool] = None

    metric: Optional[float] = None

    threshold: Optional[float] = None

    message: str = ""

    evidence: dict = field(default_factory=dict)


@dataclass
class ValidationReport:
    """
    Complete validation report for one research hypothesis.
    """

    experiment_id: str

    hypothesis: str

    status: str = "PRELIMINARY"

    gates: list[ValidationResult] = field(
        default_factory=list
    )

    metadata: dict = field(
        default_factory=dict
    )

    def add_gate(self, result: ValidationResult):
        """
        Add one validation gate to the report.
        """

        self.gates.append(result)

    def passed_gates(self):
        """
        Return all gates that passed.
        """

        return [
            gate
            for gate in self.gates
            if gate.status == "PASS"
        ]

    def failed_gates(self):
        """
        Return all gates that failed.
        """

        return [
            gate
            for gate in self.gates
            if gate.status == "FAIL"
        ]

    def inconclusive_gates(self):
        """
        Return all gates that are inconclusive.
        """

        return [
            gate
            for gate in self.gates
            if gate.status == "INCONCLUSIVE"
        ]

    def summary(self):
        """
        Return a compact summary of the validation report.
        """

        return {
            "experiment_id": self.experiment_id,
            "status": self.status,
            "total_gates": len(self.gates),
            "passed": len(self.passed_gates()),
            "failed": len(self.failed_gates()),
            "inconclusive": len(self.inconclusive_gates()),
        }