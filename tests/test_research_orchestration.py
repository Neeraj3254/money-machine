import pandas as pd
import unittest
import csv
import io
import hashlib
from research.orchestration import run_research_analysis
from research.orchestration import run_ingested_records
from research.market.ingestion import parse_delimited, schema_from_dict
from research.v2_engine.results import ExperimentResult


def request():
    return {"schema_version": "research-analysis-request-v1", "symbol": "SYNTH",
            "as_of_date": "2025-01-30", "horizon_days": 5}


def market_frame():
    dates = pd.date_range(end="2025-01-30", periods=260, freq="D")
    closes = [100 + i * 0.1 + (0 if i % 4 == 0 else 2 if i % 4 == 1 else -1 if i % 4 == 2 else 1)
              for i in range(len(dates))]
    previous = [closes[0] - 1, *closes[:-1]]
    opens = previous
    return pd.DataFrame({
        "TRADE_DATE": dates, "ISIN": "SYNTH-ISIN", "SYMBOL": "SYNTH",
        "OPNPRIC": opens, "HGHPRIC": [max(o, c) + 1 for o, c in zip(opens, closes)],
        "LWPRIC": [min(o, c) - 1 for o, c in zip(opens, closes)], "CLSPRIC": closes,
        "PRVSCLSGPRIC": previous, "TTLTRADGVOL": [0 if i == 0 else 1000 for i in range(len(dates))],
        "TTLTRFVAL": [0 if i == 0 else c * 1000 for i, c in enumerate(closes)],
    })


def nifty_frame():
    dates = pd.date_range(end="2025-01-30", periods=260, freq="D")
    values = [20000 + i * 2 + (0 if i % 4 == 0 else 3 if i % 4 == 1 else -2 if i % 4 == 2 else 1)
              for i in range(len(dates))]
    return pd.DataFrame({"TRADE_DATE": dates, "NIFTY_CLOSE": values})


class ResearchOrchestrationTests(unittest.TestCase):
    def test_orchestrator_runs_existing_features_and_fails_closed_without_evidence(self):
        result = run_research_analysis(request(), market_frame(), provenance={"source_sha256": "a" * 64})
        self.assertEqual(result["decision"], "NO_TRADE")
        self.assertEqual(result["stages"]["features"]["status"], "NOT_RUN")
        self.assertEqual(result["stages"]["opportunity_scanner"]["status"], "NOT_RUN")
        self.assertEqual(result["stages"]["timestamp_gate"]["status"], "INCONCLUSIVE")
        self.assertEqual(result["stages"]["provenance"]["status"], "INCONCLUSIVE")
        self.assertEqual(result["stages"]["validation"]["status"], "INCONCLUSIVE")
        self.assertEqual(result["stages"]["expected_value"]["status"], "INCONCLUSIVE")
        self.assertIsNone(result["proposal"])
        self.assertFalse(result["execution"]["automatic_execution"])


    def test_failed_symbol_quality_gate_blocks_features_and_downstream_stages(self):
        data = market_frame()
        data.loc[0, "SYMBOL"] = "OTHER"
        result = run_research_analysis(request(), data)
        self.assertEqual(result["decision"], "NO_TRADE")
        self.assertEqual(result["stages"]["market_data"]["status"], "FAIL")
        self.assertIn("symbol_identity_mismatch", result["stages"]["market_data"]["issues"])
        self.assertEqual(result["stages"]["features"]["status"], "NOT_RUN")
        self.assertEqual(result["stages"]["expected_value"]["status"], "INCONCLUSIVE")

    def test_duplicate_symbol_date_observation_fails_market_quality(self):
        data = pd.concat([market_frame(), market_frame().iloc[[-1]]], ignore_index=True)
        result = run_research_analysis(request(), data)
        self.assertEqual(result["stages"]["market_data"]["status"], "FAIL")
        self.assertIn("duplicate_symbol_date_observation", result["stages"]["market_data"]["issues"])
        self.assertEqual(result["stages"]["features"]["status"], "NOT_RUN")
        self.assertEqual(result["decision"], "NO_TRADE")


    def test_zero_volume_is_structurally_allowed_but_not_a_trade_signal(self):
        data = market_frame()
        data.loc[0, "TTLTRADGVOL"] = 0
        result = run_research_analysis(request(), data)
        self.assertEqual(result["stages"]["market_data"]["status"], "PASS")
        self.assertEqual(result["stages"]["freshness"]["status"], "PASS")
        self.assertEqual(result["stages"]["timestamp_gate"]["status"], "INCONCLUSIVE")
        self.assertEqual(result["stages"]["features"]["status"], "NOT_RUN")
        self.assertEqual(result["decision"], "NO_TRADE")

    def test_missing_point_in_time_availability_never_reaches_feature_scanner(self):
        result = run_research_analysis(request(), market_frame())
        self.assertEqual(result["stages"]["timestamp_gate"]["status"], "INCONCLUSIVE")
        self.assertEqual(result["stages"]["features"]["status"], "NOT_RUN")
        self.assertEqual(result["stages"]["opportunity_scanner"]["status"], "NOT_RUN")
        self.assertEqual(result["stages"]["ai_critic"]["status"], "INCONCLUSIVE")

    def test_observed_temporal_leakage_blocks_downstream_critic(self):
        called = []
        timing = pd.DataFrame({"TRADE_DATE": ["2025-01-01", "2025-01-02"],
                               "TARGET_DATE": ["2025-01-01", None]})
        result = run_research_analysis(request(), market_frame(), target_timing=timing,
                                       critic_evaluator=lambda _: called.append(True))
        self.assertEqual(result["stages"]["temporal"]["status"], "FAIL")
        self.assertEqual(result["stages"]["ai_critic"]["status"], "NOT_RUN")
        self.assertEqual(called, [])
        self.assertEqual(result["decision"], "NO_TRADE")

    def test_missing_target_dates_make_leakage_check_inconclusive(self):
        timing = pd.DataFrame({"TRADE_DATE": ["2025-01-01", "2025-01-02"],
                               "TARGET_DATE": ["2025-01-10", None]})
        result = run_research_analysis(request(), market_frame(), target_timing=timing)
        self.assertEqual(result["stages"]["temporal"]["status"], "INCONCLUSIVE")
        self.assertEqual(result["decision"], "NO_TRADE")
        self.assertIsNone(result["proposal"])

    def test_stale_date_does_not_pass_freshness_gate(self):
        data = market_frame().iloc[:-1].copy()
        result = run_research_analysis(request(), data)
        self.assertEqual(result["stages"]["freshness"]["status"], "INCONCLUSIVE")
        self.assertEqual(result["decision"], "NO_TRADE")

    def test_synthetic_fully_gated_path_can_only_emit_human_review_proposal(self):
        source_hash, validation_hash = "a" * 64, "b" * 64
        validation = ExperimentResult(
            experiment_id="SYNTHETIC_FIXTURE", hypothesis="synthetic test only", sample_size=120,
            baseline_return=0.01, signal_return=0.03, incremental_return=0.02,
            baseline_positive_rate=0.51, signal_positive_rate=0.58, incremental_positive_rate=0.07,
            cost_adjusted_return=0.02, oos_return=0.02, oos_incremental_return=0.01,
            parameter_stability=0.9, cross_stock_consistency=0.8, permutation_p_value=0.01,
            leakage_passed=True, baseline_passed=True, cost_passed=True,
            temporal_stability_passed=True, oos_passed=True, robustness_passed=True,
            adversarial_passed=True,
        )
        probability = {"status": "VALIDATED", "probability": 0.6, "expected_gain": 0.05,
                       "expected_loss": 0.04, "calibration_sample_size": 120,
                       "calibration_method": "synthetic_fixture", "evidence_sha256": "c" * 64,
                       "calibration_report_sha256": "d" * 64,
                       "source_sha256": source_hash, "validation_evidence_sha256": validation_hash}
        costs = {key: 0.001 for key in ("brokerage", "exchange_fees", "taxes", "spread", "slippage")}
        timing = pd.DataFrame({"TRADE_DATE": ["2025-01-01", "2025-01-02"],
                               "TARGET_DATE": ["2025-01-10", "2025-01-11"]})
        result = run_research_analysis(
            request(), market_frame(), nifty_context=nifty_frame(),
            provenance={"source_sha256": source_hash, "source": "SYNTHETIC_FIXTURE_ONLY",
                        "schema_version": "synthetic-v1", "adjustment_status": "unadjusted",
                        "membership_status": "verified_point_in_time", "readiness_status": "RESEARCH_READY",
                        "readiness_report_sha256": "f" * 64,
                        "validation_evidence_sha256": validation_hash, "validated_source_sha256": source_hash},
            ingestion_evidence={"status": "PASS", "schema_version": "synthetic-v1", "source_sha256": source_hash},
            target_timing=timing,
            availability_evidence={"event_time": "2025-01-30T15:30:00+05:30",
                                   "source_available_time": "2025-01-30T15:31:00+05:30",
                                   "local_receipt_time": "2025-01-30T15:32:00+05:30",
                                   "decision_cutoff_utc": "2025-01-30T11:00:00Z"},
            validation_evidence=validation, probability_evidence=probability, costs=costs,
            risk_inputs={"capital": 100000, "max_loss_fraction": 0.01, "price": 100,
                         "stop_distance": 2, "portfolio_exposure": 0,
                         "max_portfolio_exposure_fraction": 0.2,
                         "average_daily_value": 10000, "max_adv_fraction": 0.1},
            critic_evaluator=lambda _: {"status": "PASS", "model": "synthetic-fixture-only",
                                        "review_id": "fixture", "critic_sha256": "e" * 64},
        )
        self.assertEqual(result["decision"], "RESEARCH_PROPOSAL")
        self.assertEqual(result["stages"]["timestamp_gate"]["status"], "PASS")
        self.assertTrue(result["proposal"]["human_approval_required"])
        self.assertFalse(result["proposal"]["automatic_execution"])
        self.assertFalse(result["execution"]["automatic_execution"])


    def test_request_validation_is_explicit(self):
        payloads = [
            {"symbol": " SYNTH", "as_of_date": "2025-02-11", "horizon_days": 5},
            {"symbol": "SYNTH", "as_of_date": "2025-02-30", "horizon_days": 5},
            {"symbol": "SYNTH", "as_of_date": "2025-02-11", "horizon_days": True},
        ]
        for payload in payloads:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                run_research_analysis(payload)


    def test_missing_dataset_is_explicit_no_trade(self):
        result = run_research_analysis(request())
        self.assertEqual(result["decision"], "NO_TRADE")
        self.assertEqual(result["stages"]["market_data"]["reason"], "dataset_not_attached")
        self.assertIsNone(result["proposal"])

    def test_parser_output_flows_into_existing_features_and_final_decision(self):
        fields = [
            ("trading_date", "Date", "date"), ("symbol", "Symbol", "string"),
            ("open", "Open", "float"), ("high", "High", "float"),
            ("low", "Low", "float"), ("close", "Close", "float"),
            ("previous_close", "PreviousClose", "float"),
            ("net_traded_quantity", "Volume", "int"), ("net_traded_value", "Turnover", "float"),
        ]
        schema = schema_from_dict({
            "format_id": "SYNTHETIC_DAILY_EOD", "parser_id": "delimited", "schema_version": "fixture-v1",
            "dataset_type": "daily_security_bhavcopy", "record_type": "synthetic_daily_eod",
            "delimiter": ",", "encoding": "utf-8", "header_mode": "headered",
            "fields": [{"name": name, "source": source, "value_type": kind,
                        **({"date_format": "%Y-%m-%d"} if kind == "date" else {})}
                       for name, source, kind in fields],
            "duplicate_key": ["trading_date", "symbol"], "trading_date_field": "trading_date",
            "quality_profile": "ohlcv", "positive_fields": ["open", "high", "low", "close"],
            "nonnegative_fields": ["net_traded_quantity", "net_traded_value"],
        })
        text = io.StringIO()
        writer = csv.writer(text)
        writer.writerow([source for _, source, _ in fields])
        source_data = market_frame()
        for _, row in source_data.iterrows():
            writer.writerow([row.TRADE_DATE.date().isoformat(), row.SYMBOL, row.OPNPRIC, row.HGHPRIC,
                             row.LWPRIC, row.CLSPRIC, row.PRVSCLSGPRIC, row.TTLTRADGVOL, row.TTLTRFVAL])
        text.seek(0)
        parsed = parse_delimited(text, schema)
        self.assertEqual(len(parsed.accepted), 260)
        self.assertEqual(len(parsed.rejected), 0)
        source_hash = hashlib.sha256(text.getvalue().encode("utf-8")).hexdigest()
        run_id = "synthetic-run-001"
        records = [
            {
                **record,
                "source_sha256": source_hash,
                "ingestion_run_id": run_id,
            }
            for record in parsed.accepted
        ]
        result = run_ingested_records(request(), records, isin_by_symbol={"SYNTH": "SYNTH-ISIN"},
                                      instrument_master_sha256="b" * 64,
                                      provenance={"source_sha256": source_hash, "ingestion_run_id": run_id,
                                                  "source": "SYNTHETIC_FIXTURE_ONLY",
                                                  "schema_version": "fixture-v1", "adjustment_status": "unadjusted",
                                                  "membership_status": "verified_point_in_time",
                                                  "readiness_status": "RESEARCH_READY", "readiness_report_sha256": "f" * 64},
                                      nifty_context=nifty_frame(),
                                      availability_evidence={"event_time": "2025-01-30T14:30:00+05:30",
                                                             "source_available_time": "2025-01-30T14:35:00+05:30",
                                                             "local_receipt_time": "2025-01-30T14:40:00+05:30",
                                                             "decision_cutoff_utc": "2025-01-30T09:30:00Z"})
        self.assertEqual(result["stages"]["ingestion"]["status"], "PASS")
        self.assertEqual(result["stages"]["features"]["status"], "PASS")
        self.assertEqual(result["stages"]["opportunity_scanner"]["status"], "PASS")
        self.assertEqual(result["stages"]["timestamp_gate"]["status"], "PASS")
        self.assertEqual(result["stages"]["opportunity_scanner"]["candidate"]["evidence_refs"]["source_sha256"], source_hash)
        self.assertEqual(result["stages"]["opportunity_scanner"]["candidate"]["evidence_refs"]["instrument_master_sha256"], "b" * 64)
        self.assertEqual(result["decision"], "NO_TRADE")
        self.assertIsNone(result["proposal"])

    def test_synthetic_scanner_preserves_identity_features_and_evidence_references(self):
        result = run_research_analysis(
            request(), market_frame(), nifty_context=nifty_frame(),
            provenance={"source_sha256": "a" * 64, "source": "SYNTHETIC_FIXTURE_ONLY",
                        "schema_version": "synthetic-v1", "adjustment_status": "unadjusted",
                        "membership_status": "verified_point_in_time", "readiness_status": "RESEARCH_READY",
                        "readiness_report_sha256": "f" * 64},
            ingestion_evidence={"status": "PASS", "schema_version": "synthetic-v1", "source_sha256": "a" * 64},
            availability_evidence={"event_time": "2025-01-30T14:30:00+05:30",
                                   "source_available_time": "2025-01-30T14:35:00+05:30",
                                   "local_receipt_time": "2025-01-30T14:40:00+05:30",
                                   "decision_cutoff_utc": "2025-01-30T09:30:00Z"},
        )
        self.assertEqual(result["stages"]["opportunity_scanner"]["status"], "PASS")
        candidate = result["stages"]["opportunity_scanner"]["candidate"]
        self.assertEqual(candidate["isin"], "SYNTH-ISIN")
        self.assertEqual(candidate["trade_date"], request()["as_of_date"])
        self.assertGreater(len(candidate["feature_values"]), 0)
        self.assertEqual(candidate["evidence_refs"]["source_sha256"], "a" * 64)
        self.assertFalse(candidate["ranking_is_probability"])
    def test_bridge_rejects_source_hash_mismatch(self):
        record = {
            "schema_version": "fixture-v1",
            "source_sha256": "b" * 64,
            "ingestion_run_id": "synthetic-run-001",
            "values": {},
        }
        result = run_ingested_records(
            request(), [record],
            isin_by_symbol={"SYNTH": "SYNTH-ISIN"},
            instrument_master_sha256="c" * 64,
            provenance={
                "source_sha256": "a" * 64,
                "ingestion_run_id": "synthetic-run-001",
                "source": "SYNTHETIC_FIXTURE_ONLY",
                "schema_version": "fixture-v1",
            },
        )
        self.assertEqual(result["decision"], "NO_TRADE")
        self.assertEqual(
            result["stages"]["ingestion"]["reason"],
            "source_hash_mismatch:1",
        )
        self.assertIsNone(result["proposal"])
    def test_bridge_rejects_run_id_mismatch(self):
        record = {
            "schema_version": "fixture-v1",
            "source_sha256": "a" * 64,
            "ingestion_run_id": "wrong-run",
            "values": {},
        }
        result = run_ingested_records(
            request(), [record],
            isin_by_symbol={"SYNTH": "SYNTH-ISIN"},
            instrument_master_sha256="c" * 64,
            provenance={
                "source_sha256": "a" * 64,
                "ingestion_run_id": "synthetic-run-001",
                "source": "SYNTHETIC_FIXTURE_ONLY",
                "schema_version": "fixture-v1",
            },
        )
        self.assertEqual(result["decision"], "NO_TRADE")
        self.assertEqual(
            result["stages"]["ingestion"]["reason"],
            "ingestion_run_id_mismatch:1",
        )
    def test_bridge_rejects_schema_version_mismatch(self):
        record = {
            "schema_version": "wrong-schema",
            "source_sha256": "a" * 64,
            "ingestion_run_id": "synthetic-run-001",
            "values": {},
        }
        result = run_ingested_records(
            request(), [record],
            isin_by_symbol={"SYNTH": "SYNTH-ISIN"},
            instrument_master_sha256="c" * 64,
            provenance={
                "source_sha256": "a" * 64,
                "ingestion_run_id": "synthetic-run-001",
                "source": "SYNTHETIC_FIXTURE_ONLY",
                "schema_version": "fixture-v1",
            },
        )
        self.assertEqual(result["decision"], "NO_TRADE")
        self.assertEqual(
            result["stages"]["ingestion"]["reason"],
            "schema_version_mismatch:1",
        )


