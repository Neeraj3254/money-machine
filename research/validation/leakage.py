from dataclasses import dataclass
from typing import Optional

import pandas as pd

from research.validation.contract import ValidationResult


@dataclass
class LeakageCheck:
    """
    Configuration for a basic temporal leakage check.
    """

    signal_date_column: str = "TRADE_DATE"

    target_date_column: str = "TARGET_DATE"

    target_column: Optional[str] = "Forward_Return_20D"


def check_temporal_leakage(
    df: pd.DataFrame,
    signal_date_column: str = "TRADE_DATE",
    target_date_column: str = "TARGET_DATE",
) -> ValidationResult:
    """
    Check temporal ordering between signal and target.

    Rows without a target date are not considered leakage.
    They are reported as unavailable for this particular test.
    """

    required_columns = [
        signal_date_column,
        target_date_column,
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        return ValidationResult(
            name="Temporal Leakage",
            status="INCONCLUSIVE",
            passed=None,
            message=f"Missing required columns: {missing}",
        )

    data = df[
        [signal_date_column, target_date_column]
    ].copy()

    data[signal_date_column] = pd.to_datetime(
        data[signal_date_column],
        errors="coerce",
    )

    data[target_date_column] = pd.to_datetime(
        data[target_date_column],
        errors="coerce",
    )

    invalid_signal_dates = data[signal_date_column].isna()

    if invalid_signal_dates.any():
        return ValidationResult(
            name="Temporal Leakage",
            status="INCONCLUSIVE",
            passed=None,
            message=(
                f"{invalid_signal_dates.sum():,} rows contain "
                "invalid signal dates."
            ),
            evidence={
                "rows_checked": len(data),
                "invalid_signal_dates": int(
                    invalid_signal_dates.sum()
                ),
            },
        )

    missing_target_dates = data[target_date_column].isna()

    comparable = data[~missing_target_dates].copy()

    if len(comparable) == 0:
        return ValidationResult(
            name="Temporal Leakage",
            status="INCONCLUSIVE",
            passed=None,
            message="No rows contain a valid target date.",
            evidence={
                "total_rows": len(data),
                "missing_target_dates": int(
                    missing_target_dates.sum()
                ),
            },
        )

    leakage_mask = (
        comparable[target_date_column]
        <= comparable[signal_date_column]
    )

    leakage_count = int(leakage_mask.sum())

    rows_checked = len(comparable)

    leakage_rate = leakage_count / rows_checked

    if leakage_count == 0:
        if missing_target_dates.any():
            return ValidationResult(
                name="Temporal Leakage",
                status="INCONCLUSIVE",
                passed=None,
                metric=leakage_rate,
                threshold=0.0,
                message=(
                    "No temporal leakage detected among rows with valid target dates, "
                    "but missing target dates prevent a complete-data pass."
                ),
                evidence={
                    "total_rows": len(data),
                    "rows_checked": rows_checked,
                    "missing_target_dates": int(missing_target_dates.sum()),
                    "leakage_rows": 0,
                },
            )
        return ValidationResult(
            name="Temporal Leakage",
            status="PASS",
            passed=True,
            metric=leakage_rate,
            threshold=0.0,
            message=(
                "No temporal leakage detected among rows "
                "with valid target dates."
            ),
            evidence={
                "total_rows": len(data),
                "rows_checked": rows_checked,
                "missing_target_dates": int(
                    missing_target_dates.sum()
                ),
                "leakage_rows": 0,
            },
        )

    return ValidationResult(
        name="Temporal Leakage",
        status="FAIL",
        passed=False,
        metric=leakage_rate,
        threshold=0.0,
        message=(
            f"{leakage_count:,} rows contain potential "
            "temporal leakage."
        ),
        evidence={
            "total_rows": len(data),
            "rows_checked": rows_checked,
            "missing_target_dates": int(
                missing_target_dates.sum()
            ),
            "leakage_rows": leakage_count,
        },
    )
