from .results import ExperimentResult


def format_experiment_report(result: ExperimentResult) -> str:
    """
    Create a human-readable research report.

    This reports evidence only.
    It does not make a trading decision.
    """

    lines = [
        "=" * 60,
        "MONEY MACHINE — V2 RESEARCH REPORT",
        "=" * 60,
        "",
        f"Experiment: {result.experiment_id}",
        f"Hypothesis: {result.hypothesis}",
        f"Sample size: {result.sample_size}",
        "",
        "DESCRIPTIVE RESULTS",
        "-" * 40,
        f"Baseline return: "
        f"{result.baseline_return:.4%}",
        f"Signal return: "
        f"{result.signal_return:.4%}",
        f"Incremental return: "
        f"{result.incremental_return:.4%}",
        "",
        f"Baseline positive rate: "
        f"{result.baseline_positive_rate:.2%}",
        f"Signal positive rate: "
        f"{result.signal_positive_rate:.2%}",
        f"Incremental positive rate: "
        f"{result.incremental_positive_rate:.2%}",
        "",
        f"Status: {result.status}",
    ]

    if result.failure_reason:
        lines.extend([
            f"Failure reason: {result.failure_reason}",
        ])

    lines.extend([
        "",
        "=" * 60,
    ])

    return "\n".join(lines)