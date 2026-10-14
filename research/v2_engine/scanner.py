from dataclasses import replace
from pathlib import Path

import pandas as pd

from research.validation.leakage import check_temporal_leakage

from .features import build_trend_strength
from .outcomes import add_forward_return
from .runner import run_dataframe_experiment
from .validation import validate_experiment
from .stability import (
    evaluate_time_stability,
    summarize_time_stability,
)
from .oos import (
    split_train_test,
    evaluate_oos,
)


TICKERS = [
    "RELIANCE",
    "TCS",
    "INFY",
    "HDFCBANK",
    "ICICIBANK",
]


def load_stock(ticker: str) -> pd.DataFrame:
    path = Path("data/processed") / f"{ticker.lower()}_features.csv"

    if not path.exists():
        raise FileNotFoundError(
            f"Processed data not found for {ticker}: {path}"
        )

    return pd.read_csv(path)


def analyze_stock(
    ticker: str,
    cost_per_trade: float = 0.001,
) -> dict:
    df = load_stock(ticker)

    df = build_trend_strength(df)

    df = add_forward_return(
        df,
        horizon_days=20,
    )

    # Check temporal ordering only for rows with valid outcomes.
    # The final 20 rows normally have no 20-session forward return.
    eligible = df["Forward_Return_20D"].notna()

    if eligible.any():
        leakage_result = check_temporal_leakage(
            df.loc[eligible].rename(
                columns={"Date": "TRADE_DATE"}
            ),
            signal_date_column="TRADE_DATE",
            target_date_column="TARGET_DATE",
        )
    else:
        leakage_result = None

    result = run_dataframe_experiment(
        experiment_id="V2-002",
        df=df,
        signal_column="V2_002_Signal",
        forward_return_column="Forward_Return_20D",
        cost_per_trade=cost_per_trade,
    )

    stability_results = evaluate_time_stability(
        df=df,
        signal_column="V2_002_Signal",
        forward_return_column="Forward_Return_20D",
        periods=3,
    )

    stability_summary = summarize_time_stability(
        stability_results
    )

    _, test_df = split_train_test(
        df,
        train_ratio=0.70,
        purge_periods=20,
        label_horizon=20,
    )

    oos_result = evaluate_oos(
        test_df=test_df,
        signal_column="V2_002_Signal",
        forward_return_column="Forward_Return_20D",
    )

    result = replace(
        result,
        oos_return=oos_result.get("oos_return"),
        oos_incremental_return=oos_result.get(
            "signal_vs_control_incremental_return"
        ),
        temporal_stability_passed=(
            stability_summary.get("all_periods_positive") is True
        ),
        leakage_passed=(
            leakage_result is not None
            and leakage_result.status == "PASS"
            and leakage_result.passed is True
        ),
    )

    result = validate_experiment(result)

    return {
        "ticker": ticker,
        "experiment_id": result.experiment_id,
        "hypothesis": result.hypothesis,
        "sample_size": result.sample_size,
        "baseline_return": result.baseline_return,
        "signal_return": result.signal_return,
        "incremental_return": result.incremental_return,
        "signal_positive_rate": result.signal_positive_rate,
        "cost_adjusted_return": result.cost_adjusted_return,
        "oos": oos_result,
        "oos_control_return": oos_result.get("control_return"),
        "oos_signal_vs_control_incremental_return": (
            oos_result.get("signal_vs_control_incremental_return")
        ),
        "validation_gates": {
            "leakage_passed": result.leakage_passed,
            "baseline_passed": result.baseline_passed,
            "cost_passed": result.cost_passed,
            "temporal_stability_passed": (
                result.temporal_stability_passed
            ),
            "oos_passed": result.oos_passed,
            "robustness_passed": result.robustness_passed,
            "adversarial_passed": result.adversarial_passed,
        },
        "failure_reason": result.failure_reason,
        "validation_status": result.status,
    }


def scan_universe(
    tickers: list[str] | None = None,
    cost_per_trade: float = 0.001,
) -> list[dict]:
    universe = tickers or TICKERS
    results = []

    for ticker in universe:
        try:
            result = analyze_stock(
                ticker=ticker,
                cost_per_trade=cost_per_trade,
            )
            results.append(result)

        except Exception as exc:
            results.append(
                {
                    "ticker": ticker,
                    "status": "ERROR",
                    "error": str(exc),
                }
            )

    return results
