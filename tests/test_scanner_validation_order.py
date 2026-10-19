import pytest
import pandas as pd

from research.v2_engine import scanner
from research.v2_engine.results import ExperimentResult


def test_scanner_validates_only_after_all_evidence_stages(monkeypatch):
    events = []

    def fake_run_dataframe_experiment(**kwargs):
        events.append("experiment")
        return ExperimentResult(
            experiment_id="TEST",
            hypothesis="test",
            sample_size=1,
            baseline_return=0.0,
            signal_return=0.0,
            incremental_return=0.0,
            signal_positive_rate=0.0,
            cost_adjusted_return=0.0,
            status="NOT_VALIDATED",
            failure_reason="test",
        )

    def fake_validate_experiment(result):
        events.append("validate")
        return result

    def fake_stability(**kwargs):
        events.append("stability")
        return []

    def fake_stability_summary(results):
        events.append("stability_summary")
        return {}

    def fake_split_train_test(
        df, train_ratio, purge_periods=0, label_horizon=0
    ):
        assert purge_periods == 20
        assert label_horizon == 20
        events.append("split")
        return df, df

    def fake_oos(**kwargs):
        events.append("oos")
        return {}

    monkeypatch.setattr(
        scanner,
        "load_stock",
        lambda ticker: pd.DataFrame(
            {
                "Close": [1.0],
                "V2_002_Signal": [True],
                "Forward_Return_20D": [0.01],
            }
        ),
    )
    monkeypatch.setattr(scanner, "build_trend_strength", lambda df: df)
    monkeypatch.setattr(
        scanner,
        "add_forward_return",
        lambda df, horizon_days: df,
    )
    monkeypatch.setattr(
        scanner,
        "run_dataframe_experiment",
        fake_run_dataframe_experiment,
    )
    monkeypatch.setattr(
        scanner,
        "validate_experiment",
        fake_validate_experiment,
    )
    monkeypatch.setattr(
        scanner, "evaluate_time_stability", fake_stability
    )
    monkeypatch.setattr(
        scanner,
        "summarize_time_stability",
        fake_stability_summary,
    )
    monkeypatch.setattr(
        scanner, "split_train_test", fake_split_train_test
    )
    monkeypatch.setattr(scanner, "evaluate_oos", fake_oos)

    scanner.analyze_stock("TEST")

    assert events == [
        "experiment",
        "stability",
        "stability_summary",
        "split",
        "oos",
        "validate",
    ]


def test_scanner_passes_oos_control_lift_to_validation(monkeypatch):
    captured = {}

    def fake_validate_experiment(result):
        captured["oos_incremental_return"] = (
            result.oos_incremental_return
        )
        return result

    monkeypatch.setattr(
        scanner,
        "load_stock",
        lambda ticker: pd.DataFrame(
            {
                "Close": [1.0],
                "V2_002_Signal": [True],
                "Forward_Return_20D": [0.01],
            }
        ),
    )
    monkeypatch.setattr(scanner, "build_trend_strength", lambda df: df)
    monkeypatch.setattr(
        scanner, "add_forward_return", lambda df, horizon_days: df
    )
    monkeypatch.setattr(
        scanner,
        "run_dataframe_experiment",
        lambda **kwargs: ExperimentResult(
            experiment_id="TEST",
            hypothesis="test",
            sample_size=100,
            status="NOT_VALIDATED",
        ),
    )
    monkeypatch.setattr(
        scanner, "evaluate_time_stability", lambda **kwargs: []
    )
    monkeypatch.setattr(
        scanner,
        "summarize_time_stability",
        lambda results: {"all_periods_positive": False},
    )
    monkeypatch.setattr(
        scanner,
        "split_train_test",
        lambda df, train_ratio, purge_periods, label_horizon: (df, df),
    )
    monkeypatch.setattr(
        scanner,
        "evaluate_oos",
        lambda **kwargs: {
            "oos_return": 0.03,
            "oos_incremental_return": 0.01,
            "signal_vs_control_incremental_return": -0.02,
        },
    )
    monkeypatch.setattr(
        scanner, "validate_experiment", fake_validate_experiment
    )

    scanner.analyze_stock("TEST")

    assert captured["oos_incremental_return"] == pytest.approx(-0.02)
