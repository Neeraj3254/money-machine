from __future__ import annotations

import numpy as np
import pandas as pd


def permutation_test_mean_spread(
    baseline: pd.DataFrame,
    spread_col: str = "Q1_MINUS_Q5",
    n_permutations: int = 10000,
    random_state: int = 42,
) -> dict:
    """
    Test whether the observed mean Q1-Q5 spread is distinguishable
    from zero using a sign-flipping permutation test.

    The test preserves the magnitude of each daily spread while
    randomly changing its direction.

    Parameters
    ----------
    baseline:
        Daily baseline dataframe containing the spread column.

    spread_col:
        Column containing daily Q1-Q5 spreads.

    n_permutations:
        Number of random sign permutations.

    random_state:
        Seed for reproducibility.

    Returns
    -------
    dict
        Summary of the permutation test.
    """

    if spread_col not in baseline.columns:
        raise ValueError(
            f"Missing required column: {spread_col}"
        )

    spread = (
        pd.to_numeric(
            baseline[spread_col],
            errors="coerce",
        )
        .dropna()
        .to_numpy(dtype=float)
    )

    if len(spread) < 2:
        raise ValueError(
            "At least 2 valid daily spreads are required."
        )

    if n_permutations <= 0:
        raise ValueError(
            "n_permutations must be greater than zero."
        )

    rng = np.random.default_rng(random_state)

    observed_mean = float(np.mean(spread))

    null_means = np.empty(n_permutations)

    for i in range(n_permutations):

        signs = rng.choice(
            np.array([-1.0, 1.0]),
            size=len(spread),
        )

        shuffled = spread * signs

        null_means[i] = np.mean(shuffled)

    p_value = float(
        np.mean(
            np.abs(null_means) >= abs(observed_mean)
        )
    )

    return {
        "observations": len(spread),
        "observed_mean": observed_mean,
        "null_mean": float(np.mean(null_means)),
        "null_std": float(np.std(null_means, ddof=1)),
        "p_value": p_value,
        "n_permutations": n_permutations,
        "random_state": random_state,
    }


def bootstrap_mean_spread(
    baseline: pd.DataFrame,
    spread_col: str = "Q1_MINUS_Q5",
    n_bootstrap: int = 10000,
    random_state: int = 42,
) -> dict:
    """
    Bootstrap the mean daily spread and estimate a
    percentile confidence interval.

    This is a descriptive uncertainty estimate and should
    not be interpreted as proof of an independent trading edge.
    """

    if spread_col not in baseline.columns:
        raise ValueError(
            f"Missing required column: {spread_col}"
        )

    spread = (
        pd.to_numeric(
            baseline[spread_col],
            errors="coerce",
        )
        .dropna()
        .to_numpy(dtype=float)
    )

    if len(spread) < 2:
        raise ValueError(
            "At least 2 valid daily spreads are required."
        )

    if n_bootstrap <= 0:
        raise ValueError(
            "n_bootstrap must be greater than zero."
        )

    rng = np.random.default_rng(random_state)

    bootstrap_means = np.empty(n_bootstrap)

    for i in range(n_bootstrap):

        sample = rng.choice(
            spread,
            size=len(spread),
            replace=True,
        )

        bootstrap_means[i] = np.mean(sample)

    observed_mean = float(np.mean(spread))

    ci_low, ci_high = np.percentile(
        bootstrap_means,
        [2.5, 97.5],
    )

    return {
        "observations": len(spread),
        "observed_mean": observed_mean,
        "bootstrap_mean": float(
            np.mean(bootstrap_means)
        ),
        "ci_95_low": float(ci_low),
        "ci_95_high": float(ci_high),
        "n_bootstrap": n_bootstrap,
        "random_state": random_state,
    }


def summarize_significance(
    permutation_result: dict,
    bootstrap_result: dict,
) -> dict:
    """
    Combine significance diagnostics into one summary.
    """

    p_value = permutation_result["p_value"]

    ci_low = bootstrap_result["ci_95_low"]
    ci_high = bootstrap_result["ci_95_high"]

    permutation_pass = p_value < 0.05

    bootstrap_excludes_zero = (
        ci_low > 0
        or ci_high < 0
    )

    return {
        "permutation_p_value": p_value,
        "permutation_pass": permutation_pass,
        "bootstrap_ci_95_low": ci_low,
        "bootstrap_ci_95_high": ci_high,
        "bootstrap_excludes_zero": bootstrap_excludes_zero,
        "significance_pass": (
            permutation_pass
            and bootstrap_excludes_zero
        ),
    }