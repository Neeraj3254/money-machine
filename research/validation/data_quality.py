import pandas as pd

from research.validation.contract import ValidationResult


def check_target_completeness(
    df: pd.DataFrame,
    target_date_column: str = "TARGET_DATE",
    target_value_column: str = "TARGET_CLOSE",
) -> ValidationResult:
    """
    Check whether rows that have a target date also have
    a valid target value.

    Rows without a target date are outside the available
    forecast horizon and are not counted as failures.
    """

    required_columns = [
        target_date_column,
        target_value_column,
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        return ValidationResult(
            name="Target Completeness",
            status="INCONCLUSIVE",
            passed=None,
            message=f"Missing required columns: {missing}",
        )

    has_target_date = df[target_date_column].notna()

    eligible = df[has_target_date].copy()

    if len(eligible) == 0:
        return ValidationResult(
            name="Target Completeness",
            status="INCONCLUSIVE",
            passed=None,
            message="No rows contain a target date.",
        )

    missing_target = (
        eligible[target_value_column].isna()
        | (eligible[target_value_column] <= 0)
    )

    missing_count = int(missing_target.sum())

    total_eligible = len(eligible)

    missing_rate = missing_count / total_eligible

    if missing_count == 0:
        return ValidationResult(
            name="Target Completeness",
            status="PASS",
            passed=True,
            metric=missing_rate,
            threshold=0.0,
            message="All rows with target dates have valid target values.",
            evidence={
                "eligible_rows": total_eligible,
                "missing_target_values": 0,
            },
        )

    return ValidationResult(
        name="Target Completeness",
        status="FAIL",
        passed=False,
        metric=missing_rate,
        threshold=0.0,
        message=(
            f"{missing_count:,} rows have a target date "
            "but no valid target value."
        ),
        evidence={
            "eligible_rows": total_eligible,
            "missing_target_values": missing_count,
            "missing_rate": missing_rate,
        },
    )