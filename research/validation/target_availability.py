from __future__ import annotations

import pandas as pd


def classify_target_availability(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classify whether each forward target is valid, missing temporarily,
    or missing at the end of the available security history.

    Required columns:
        ISIN
        TRADE_DATE
        TARGET_DATE
        TARGET_CLOSE
    """

    required = [
        "ISIN",
        "TRADE_DATE",
        "TARGET_DATE",
        "TARGET_CLOSE",
    ]

    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    result = df.copy()

    result["TRADE_DATE"] = pd.to_datetime(
        result["TRADE_DATE"]
    )

    result["TARGET_DATE"] = pd.to_datetime(
        result["TARGET_DATE"]
    )

    # Last observed date for each security
    last_observed = (
        result.groupby("ISIN")["TRADE_DATE"]
        .max()
        .rename("LAST_OBSERVED_DATE")
    )

    result = result.merge(
        last_observed,
        on="ISIN",
        how="left",
    )

    result["TARGET_AVAILABLE"] = (
        result["TARGET_CLOSE"].notna()
    )

    result["TARGET_STATUS"] = "NO_FORWARD_TARGET"

    # Valid target
    valid = (
        result["TARGET_DATE"].notna()
        & result["TARGET_CLOSE"].notna()
    )

    result.loc[valid, "TARGET_STATUS"] = (
        "VALID_TARGET"
    )

    # Missing target where the security is observed later.
    temporary_gap = (
        result["TARGET_DATE"].notna()
        & result["TARGET_CLOSE"].isna()
        & (
            result["LAST_OBSERVED_DATE"]
            > result["TARGET_DATE"]
        )
    )

    result.loc[
        temporary_gap,
        "TARGET_STATUS"
    ] = "TEMPORARY_GAP"

    # Missing target where there is no observation
    # after the target date.
    terminal_gap = (
        result["TARGET_DATE"].notna()
        & result["TARGET_CLOSE"].isna()
        & (
            result["LAST_OBSERVED_DATE"]
            <= result["TARGET_DATE"]
        )
    )

    result.loc[
        terminal_gap,
        "TARGET_STATUS"
    ] = "TERMINAL_GAP"

    return result


def summarize_target_availability(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Produce counts and percentages for target status.
    """

    counts = (
        df["TARGET_STATUS"]
        .value_counts()
        .rename("count")
        .to_frame()
    )

    counts["percent"] = (
        counts["count"]
        / len(df)
        * 100
    )

    return counts