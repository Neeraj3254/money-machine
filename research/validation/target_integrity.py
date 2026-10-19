from __future__ import annotations

import pandas as pd


def check_target_integrity(
    df: pd.DataFrame,
    max_temporary_gap_rate: float = 0.05,
    max_terminal_gap_rate: float = 0.01,
):
    """
    Validate forward-target integrity.

    NO_FORWARD_TARGET:
        Expected censoring at the end of the research window.

    VALID_TARGET:
        Target close exists.

    TEMPORARY_GAP:
        Security has observations after the missing target.

    TERMINAL_GAP:
        Security has no observation after the target.
    """

    required = ["TARGET_STATUS"]

    missing = [
        col for col in required
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    counts = (
        df["TARGET_STATUS"]
        .value_counts()
    )

    valid = counts.get("VALID_TARGET", 0)
    temporary = counts.get("TEMPORARY_GAP", 0)
    terminal = counts.get("TERMINAL_GAP", 0)
    no_target = counts.get("NO_FORWARD_TARGET", 0)

    total = len(df)

    resolved_target_rows = (
        valid + temporary + terminal
    )

    temporary_rate = (
        temporary / resolved_target_rows
        if resolved_target_rows
        else 0.0
    )

    terminal_rate = (
        terminal / resolved_target_rows
        if resolved_target_rows
        else 0.0
    )

    passed = (
        temporary_rate <= max_temporary_gap_rate
        and terminal_rate <= max_terminal_gap_rate
    )

    status = "PASS" if passed else "FAIL"

    return {
        "name": "Target Integrity",
        "status": status,
        "passed": passed,
        "total_rows": total,
        "valid_targets": valid,
        "temporary_gaps": temporary,
        "terminal_gaps": terminal,
        "no_forward_target": no_target,
        "resolved_target_rows": resolved_target_rows,
        "temporary_gap_rate": temporary_rate,
        "terminal_gap_rate": terminal_rate,
        "max_temporary_gap_rate": max_temporary_gap_rate,
        "max_terminal_gap_rate": max_terminal_gap_rate,
    }