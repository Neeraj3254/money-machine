"""Fail-closed, versioned orchestration for evidence-bound research proposals.

This service connects existing daily-market features and validation code. It
does not fetch data, estimate probabilities, or execute trades.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
import re
from typing import Any, Mapping
from datetime import datetime
from collections.abc import Callable

import pandas as pd

from research.market.premove import add_premove_features, add_premove_scores
from research.risk_engine import evaluate_cash_equity_risk
from research.validation.leakage import check_temporal_leakage
from research.v2_engine.results import ExperimentResult
from research.v2_engine.validation import validate_experiment


REQUEST_SCHEMA_VERSION = "research-analysis-request-v1"
RESPONSE_SCHEMA_VERSION = "research-analysis-response-v1"
REQUIRED_MARKET_COLUMNS = (
    "TRADE_DATE", "ISIN", "SYMBOL", "OPNPRIC", "HGHPRIC", "LWPRIC",
    "CLSPRIC", "PRVSCLSGPRIC", "TTLTRADGVOL", "TTLTRFVAL",
)
REQUIRED_COSTS = ("brokerage", "exchange_fees", "taxes", "spread", "slippage")
SHA256_LENGTH = 64
SCANNER_EVIDENCE_COLUMNS = (
    "RVOL_5D", "RVOL_20D", "ATR_Range_Ratio", "EMA_20", "EMA_50", "EMA_200",
    "Return_5D", "Return_20D", "Breakout_5D", "Breakout_20D", "Breakout_50D",
    "Breakout_52W", "RSI_14", "MACD", "MACD_Signal", "Relative_Strength_NIFTY_20D",
    "Gap_Pct", "Distance_From_20D_High", "Liquidity_20D",
)


@dataclass(frozen=True)
class AnalysisRequest:
    symbol: str
    as_of_date: str
    horizon_days: int
    schema_version: str = REQUEST_SCHEMA_VERSION

    @classmethod
    def parse(cls, payload: Mapping[str, Any]) -> "AnalysisRequest":
        if not isinstance(payload, Mapping):
            raise ValueError("request_must_be_an_object")
        unknown = set(payload) - {"schema_version", "symbol", "as_of_date", "horizon_days"}
        if unknown:
            raise ValueError("unsupported_request_fields:" + ",".join(sorted(str(key) for key in unknown)))
        version = payload.get("schema_version", REQUEST_SCHEMA_VERSION)
        if version != REQUEST_SCHEMA_VERSION:
            raise ValueError("unsupported_request_schema_version")
        symbol = payload.get("symbol")
        if not isinstance(symbol, str) or not symbol.strip() or symbol != symbol.strip():
            raise ValueError("symbol_must_be_a_nonblank_trimmed_string")
        symbol = symbol.upper()
        if not re.fullmatch(r"[A-Z0-9&-]{1,30}", symbol):
            raise ValueError("symbol_contains_unsupported_characters")
        raw_date = payload.get("as_of_date")
        if not isinstance(raw_date, str):
            raise ValueError("as_of_date_must_be_iso_date")
        try:
            parsed_date = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise ValueError("as_of_date_must_be_iso_date") from exc
        if parsed_date.isoformat() != raw_date:
            raise ValueError("as_of_date_must_be_iso_date")
        horizon = payload.get("horizon_days")
        if isinstance(horizon, bool) or not isinstance(horizon, int) or not 1 <= horizon <= 252:
            raise ValueError("horizon_days_must_be_integer_between_1_and_252")
        return cls(symbol=symbol, as_of_date=raw_date, horizon_days=horizon)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _finite_nonnegative(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == SHA256_LENGTH and all(c in "0123456789abcdefABCDEF" for c in value)


def _timestamp_gate(evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(evidence, Mapping):
        return {"status": "INCONCLUSIVE", "reason": "point_in_time_timestamp_evidence_missing"}
    names = ("event_time", "source_available_time", "local_receipt_time", "decision_cutoff_utc")
    parsed = {}
    try:
        for name in names:
            value = evidence.get(name)
            if not isinstance(value, str):
                raise ValueError(name)
            moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if moment.tzinfo is None or moment.utcoffset() is None:
                raise ValueError(name)
            parsed[name] = moment
    except ValueError as exc:
        return {"status": "INCONCLUSIVE", "reason": "missing_or_naive_timestamp:" + str(exc)}
    if parsed["source_available_time"] < parsed["event_time"] or parsed["local_receipt_time"] < parsed["source_available_time"]:
        return {"status": "FAIL", "reason": "timestamp_order_invalid"}
    if max(parsed["source_available_time"], parsed["local_receipt_time"]) > parsed["decision_cutoff_utc"]:
        return {"status": "FAIL", "reason": "observation_unavailable_at_decision_cutoff"}
    return {"status": "PASS", "decision_cutoff_utc": parsed["decision_cutoff_utc"].isoformat()}


def _market_quality(frame: pd.DataFrame, request: AnalysisRequest) -> tuple[pd.DataFrame | None, list[str]]:
    issues: list[str] = []
    missing = [column for column in REQUIRED_MARKET_COLUMNS if column not in frame.columns]
    if missing:
        return None, ["missing_required_columns:" + ",".join(missing)]
    data = frame.loc[:, list(REQUIRED_MARKET_COLUMNS)].copy()
    data["TRADE_DATE"] = pd.to_datetime(data["TRADE_DATE"], errors="coerce")
    if data["TRADE_DATE"].isna().any():
        issues.append("invalid_or_missing_trade_date")
    if data["ISIN"].isna().any() or data["ISIN"].astype(str).str.strip().eq("").any():
        issues.append("missing_instrument_identity")
    symbols = data["SYMBOL"].astype(str).str.upper().unique().tolist()
    if symbols != [request.symbol]:
        issues.append("symbol_identity_mismatch")
    if data.duplicated(["TRADE_DATE", "ISIN"]).any():
        issues.append("duplicate_symbol_date_observation")
    if data["TRADE_DATE"].notna().any() and (data["TRADE_DATE"].dt.date > date.fromisoformat(request.as_of_date)).any():
        issues.append("future_observation_after_as_of_date")
    numeric = ("OPNPRIC", "HGHPRIC", "LWPRIC", "CLSPRIC", "PRVSCLSGPRIC", "TTLTRADGVOL", "TTLTRFVAL")
    for column in numeric:
        data[column] = pd.to_numeric(data[column], errors="coerce")
        if data[column].isna().any() or not data[column].map(lambda x: math.isfinite(float(x))).all():
            issues.append("invalid_numeric_field:" + column)
    if not issues:
        positive = data[["OPNPRIC", "HGHPRIC", "LWPRIC", "CLSPRIC", "PRVSCLSGPRIC"]].gt(0).all(axis=1)
        o, h, low, close = (data[name] for name in ("OPNPRIC", "HGHPRIC", "LWPRIC", "CLSPRIC"))
        if not positive.all() or (h < pd.concat([o, low, close], axis=1).max(axis=1)).any() or (low > pd.concat([o, h, close], axis=1).min(axis=1)).any():
            issues.append("invalid_ohlc_relationship")
        if (data["TTLTRADGVOL"] < 0).any() or (data["TTLTRFVAL"] < 0).any():
            issues.append("negative_quantity_or_turnover")
        if not data["TRADE_DATE"].is_monotonic_increasing:
            issues.append("observations_not_chronological")
    if issues:
        return None, issues
    data["SYMBOL"] = data["SYMBOL"].astype(str).str.upper()
    return data.reset_index(drop=True), []


def _benchmark_quality(frame: pd.DataFrame | None, as_of_date: str) -> tuple[pd.DataFrame | None, str | None]:
    if frame is None:
        return None, "nifty_benchmark_history_missing"
    if not isinstance(frame, pd.DataFrame) or not {"TRADE_DATE", "NIFTY_CLOSE"}.issubset(frame.columns):
        return None, "nifty_benchmark_schema_missing"
    data = frame.loc[:, ["TRADE_DATE", "NIFTY_CLOSE"]].copy()
    data["TRADE_DATE"] = pd.to_datetime(data["TRADE_DATE"], errors="coerce")
    data["NIFTY_CLOSE"] = pd.to_numeric(data["NIFTY_CLOSE"], errors="coerce")
    if data["TRADE_DATE"].isna().any() or data["NIFTY_CLOSE"].isna().any():
        return None, "nifty_benchmark_has_invalid_observations"
    if not data["NIFTY_CLOSE"].map(lambda value: math.isfinite(float(value)) and float(value) > 0).all():
        return None, "nifty_benchmark_close_must_be_positive_finite"
    if data["TRADE_DATE"].duplicated().any() or not data["TRADE_DATE"].is_monotonic_increasing:
        return None, "nifty_benchmark_duplicate_or_unordered_dates"
    if (data["TRADE_DATE"].dt.date > date.fromisoformat(as_of_date)).any():
        return None, "nifty_benchmark_future_observation_after_as_of_date"
    return data.reset_index(drop=True), None


def _validate_probability(probability: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(probability, Mapping) or probability.get("status") != "VALIDATED":
        return {"status": "INCONCLUSIVE", "reason": "validated_probability_evidence_missing"}
    p = probability.get("probability")
    gain = probability.get("expected_gain")
    loss = probability.get("expected_loss")
    sample = probability.get("calibration_sample_size")
    if (not isinstance(p, (int, float)) or isinstance(p, bool) or not math.isfinite(p) or not 0 <= p <= 1
            or not isinstance(sample, int) or isinstance(sample, bool) or sample < 100
            or not _finite_nonnegative(gain) or not _finite_nonnegative(loss)
            or gain == 0 or loss == 0 or not _valid_sha256(probability.get("evidence_sha256"))
            or not _valid_sha256(probability.get("calibration_report_sha256"))
            or not isinstance(probability.get("calibration_method"), str) or not probability.get("calibration_method")):
        return {"status": "INCONCLUSIVE", "reason": "invalid_or_untraceable_probability_evidence"}
    return {"status": "PASS", "probability": float(p), "expected_gain": float(gain),
            "expected_loss": float(loss), "calibration_sample_size": sample,
            "evidence_sha256": probability["evidence_sha256"]}


def _expected_value(probability: Mapping[str, Any] | None, costs: Mapping[str, Any] | None) -> dict[str, Any]:
    """Calculate per-unit return fractions only from validated evidence and itemized costs."""
    probability_check = _validate_probability(probability)
    if probability_check["status"] != "PASS":
        return {"status": "INCONCLUSIVE", "reason": probability_check["reason"], "value": None}
    if not isinstance(costs, Mapping) or any(not _finite_nonnegative(costs.get(key)) for key in REQUIRED_COSTS):
        return {"status": "INCONCLUSIVE", "reason": "itemized_transaction_costs_required", "value": None}
    total_cost = sum(float(costs[key]) for key in REQUIRED_COSTS)
    value = probability_check["probability"] * probability_check["expected_gain"] - (1 - probability_check["probability"]) * probability_check["expected_loss"] - total_cost
    return {"status": "PASS" if value > 0 else "FAIL", "value": value, "costs": dict(costs), "total_cost": total_cost}


class _ScannerEvidenceUnavailable(Exception):
    """Internal control flow when score inputs are missing instead of neutral."""


def run_research_analysis(
    payload: Mapping[str, Any],
    market_data: pd.DataFrame | None = None,
    *,
    provenance: Mapping[str, Any] | None = None,
    nifty_context: pd.DataFrame | None = None,
    ingestion_evidence: Mapping[str, Any] | None = None,
    target_timing: pd.DataFrame | None = None,
    availability_evidence: Mapping[str, Any] | None = None,
    validation_evidence: ExperimentResult | None = None,
    probability_evidence: Mapping[str, Any] | None = None,
    costs: Mapping[str, Any] | None = None,
    risk_inputs: Mapping[str, Any] | None = None,
    critic_evaluator: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run candidate discovery through proposal gates; default is always NO_TRADE."""
    request = AnalysisRequest.parse(payload)
    canonical_request = {"schema_version": request.schema_version, "symbol": request.symbol,
                         "as_of_date": request.as_of_date, "horizon_days": request.horizon_days}
    issues: list[str] = []
    stages: dict[str, Any] = {}
    candidate: dict[str, Any] | None = None
    features: pd.DataFrame | None = None
    prov = dict(provenance or {})
    digest = prov.get("source_sha256")
    ingestion_pass = (isinstance(ingestion_evidence, Mapping) and ingestion_evidence.get("status") == "PASS"
                      and _valid_sha256(ingestion_evidence.get("source_sha256"))
                      and str(ingestion_evidence.get("source_sha256")).lower() == str(digest).lower()
                      and isinstance(ingestion_evidence.get("schema_version"), str)
                      and bool(ingestion_evidence.get("schema_version")))
    provenance_pass = (_valid_sha256(digest) and isinstance(prov.get("source"), str) and bool(prov.get("source"))
                       and isinstance(prov.get("schema_version"), str) and bool(prov.get("schema_version"))
                       and prov.get("adjustment_status") in {"adjusted", "unadjusted"}
                       and prov.get("membership_status") == "verified_point_in_time")
    readiness_pass = (prov.get("readiness_status") == "RESEARCH_READY"
                      and _valid_sha256(prov.get("readiness_report_sha256")))
    stages["timestamp_gate"] = _timestamp_gate(availability_evidence)
    stages["ingestion"] = ({"status": "PASS", "schema_version": ingestion_evidence["schema_version"],
                             "source_sha256": ingestion_evidence["source_sha256"].lower()}
                            if ingestion_pass else {"status": "INCONCLUSIVE", "reason": "hash_bound_parser_lineage_required"})
    stages["provenance"] = ({"status": "PASS", "source_sha256": digest.lower(), "source": prov["source"],
                             "schema_version": prov["schema_version"], "adjustment_status": prov["adjustment_status"],
                             "membership_status": prov["membership_status"]}
                            if provenance_pass else {"status": "INCONCLUSIVE", "reason": "hash_source_schema_adjustment_and_point_in_time_membership_evidence_required"})
    stages["readiness"] = ({"status": "PASS", "readiness_report_sha256": prov["readiness_report_sha256"].lower()}
                           if readiness_pass else {"status": "INCONCLUSIVE", "reason": "hash_bound_research_readiness_evidence_required"})

    if market_data is None:
        stages["market_data"] = {"status": "INCONCLUSIVE", "reason": "dataset_not_attached"}
        stages["freshness"] = {"status": "INCONCLUSIVE", "reason": "dataset_not_attached"}
        stages["features"] = {"status": "NOT_RUN", "reason": "market_data_gate_not_passed"}
        stages["opportunity_scanner"] = {"status": "NOT_RUN", "reason": "market_data_gate_not_passed"}
    else:
        clean, quality_issues = _market_quality(market_data, request)
        if quality_issues:
            stages["market_data"] = {"status": "FAIL", "issues": quality_issues}
            stages["freshness"] = {"status": "NOT_RUN", "reason": "market_data_quality_failed"}
            stages["features"] = {"status": "NOT_RUN", "reason": "market_data_gate_failed"}
            stages["opportunity_scanner"] = {"status": "NOT_RUN", "reason": "market_data_gate_failed"}
            issues.extend(quality_issues)
        else:
            stages["market_data"] = {"status": "PASS", "rows": len(clean), "zero_volume_rows_allowed": True}
            latest_date = clean["TRADE_DATE"].max().date()
            requested_date = date.fromisoformat(request.as_of_date)
            if latest_date == requested_date:
                stages["freshness"] = {"status": "PASS", "latest_observation_date": latest_date.isoformat()}
            else:
                stages["freshness"] = {"status": "INCONCLUSIVE", "reason": "latest_observation_does_not_match_as_of_and_exchange_calendar_is_unverified",
                                       "latest_observation_date": latest_date.isoformat(), "requested_as_of_date": request.as_of_date}
            if not (ingestion_pass and provenance_pass and readiness_pass):
                stages["features"] = {"status": "NOT_RUN", "reason": "source_provenance_or_readiness_gate_not_passed"}
                stages["opportunity_scanner"] = {"status": "NOT_RUN", "reason": "source_provenance_or_readiness_gate_not_passed"}
            elif stages["timestamp_gate"]["status"] != "PASS":
                stages["features"] = {"status": "NOT_RUN", "reason": "point_in_time_availability_not_verified"}
                stages["opportunity_scanner"] = {"status": "NOT_RUN", "reason": "point_in_time_availability_not_verified"}
            elif stages["freshness"]["status"] != "PASS":
                stages["features"] = {"status": "NOT_RUN", "reason": "freshness_gate_not_passed"}
                stages["opportunity_scanner"] = {"status": "NOT_RUN", "reason": "freshness_gate_not_passed"}
            elif len(clean) < 2:
                stages["features"] = {"status": "INCONCLUSIVE", "reason": "insufficient_history"}
                stages["opportunity_scanner"] = {"status": "NOT_RUN", "reason": "feature_warmup_not_satisfied"}
            else:
                benchmark, benchmark_issue = _benchmark_quality(nifty_context, request.as_of_date)
                if benchmark_issue:
                    stages["features"] = {"status": "INCONCLUSIVE", "reason": benchmark_issue}
                    stages["opportunity_scanner"] = {"status": "NOT_RUN", "reason": "benchmark_gate_not_passed"}
                else:
                  try:
                    features = add_premove_features(clean, nifty_context=benchmark)
                    features = add_premove_scores(features)
                    score_columns = ("Setup_Score", "Chase_Risk", "Adjusted_Setup_Score")
                    if any(column not in features.columns for column in score_columns):
                        raise ValueError("required_scanner_score_missing")
                    latest = features.loc[features["TRADE_DATE"].dt.date == date.fromisoformat(request.as_of_date)]
                    if latest.empty:
                        stages["features"] = {"status": "PASS", "feature_engine": "research.market.premove.add_premove_features"}
                        stages["opportunity_scanner"] = {"status": "INCONCLUSIVE", "reason": "no_observation_on_requested_as_of_date"}
                    else:
                        row = latest.iloc[-1]
                        required_features = score_columns + SCANNER_EVIDENCE_COLUMNS
                        if any(column not in features.columns for column in required_features):
                            stages["features"] = {"status": "INCONCLUSIVE", "reason": "required_scanner_feature_column_missing"}
                            stages["opportunity_scanner"] = {"status": "INCONCLUSIVE", "reason": "missing_features_are_not_neutral_scores"}
                            raise _ScannerEvidenceUnavailable
                        if any(pd.isna(row[column]) or not math.isfinite(float(row[column])) for column in required_features):
                            stages["features"] = {"status": "INCONCLUSIVE", "reason": "required_scanner_features_missing_or_non_finite"}
                            stages["opportunity_scanner"] = {"status": "INCONCLUSIVE", "reason": "missing_features_are_not_neutral_scores"}
                            raise _ScannerEvidenceUnavailable
                        stages["features"] = {"status": "PASS", "feature_engine": "research.market.premove.add_premove_features"}
                        candidate = {"symbol": request.symbol, "trade_date": request.as_of_date,
                                     "isin": str(row["ISIN"]),
                                     "setup_score": float(row["Setup_Score"]),
                                     "chase_risk": float(row["Chase_Risk"]),
                                     "adjusted_setup_score": float(row["Adjusted_Setup_Score"]),
                                     "feature_values": {column: float(row[column]) for column in SCANNER_EVIDENCE_COLUMNS},
                                     "evidence_refs": {"source_sha256": provenance.get("source_sha256") if isinstance(provenance, Mapping) else None,
                                                       "instrument_master_sha256": ingestion_evidence.get("instrument_master_sha256") if isinstance(ingestion_evidence, Mapping) else None,
                                                       "benchmark_observation_date": request.as_of_date},
                                     "ranking_is_probability": False}
                        stages["opportunity_scanner"] = {"status": "PASS", "scanner": "research.market.premove.add_premove_scores",
                                                           "candidate": candidate}
                  except _ScannerEvidenceUnavailable:
                    features = None
                    candidate = None
                  except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                    features = None
                    candidate = None
                    stages["features"] = {"status": "INCONCLUSIVE", "reason": "feature_engine_error", "error_type": type(exc).__name__}
                    stages["opportunity_scanner"] = {"status": "NOT_RUN", "reason": "feature_engine_did_not_complete"}

    prov = dict(provenance or {})
    digest = prov.get("source_sha256")
    if (isinstance(ingestion_evidence, Mapping) and ingestion_evidence.get("status") == "PASS"
            and _valid_sha256(ingestion_evidence.get("source_sha256"))
            and str(ingestion_evidence.get("source_sha256")).lower() == str(digest).lower()
            and isinstance(ingestion_evidence.get("schema_version"), str) and ingestion_evidence.get("schema_version")):
        stages["ingestion"] = {"status": "PASS", "schema_version": ingestion_evidence["schema_version"],
                               "source_sha256": ingestion_evidence["source_sha256"].lower()}
    else:
        stages["ingestion"] = {"status": "INCONCLUSIVE", "reason": "hash_bound_parser_lineage_required"}
    provenance_requirements = (
        _valid_sha256(digest)
        and isinstance(prov.get("source"), str) and bool(prov.get("source"))
        and isinstance(prov.get("schema_version"), str) and bool(prov.get("schema_version"))
        and prov.get("adjustment_status") in {"adjusted", "unadjusted"}
        and prov.get("membership_status") == "verified_point_in_time"
    )
    if not provenance_requirements:
        stages["provenance"] = {"status": "INCONCLUSIVE", "reason": "hash_source_schema_adjustment_and_point_in_time_membership_evidence_required"}
    else:
        stages["provenance"] = {"status": "PASS", "source_sha256": digest.lower(),
                                "source": prov["source"], "schema_version": prov["schema_version"],
                                "adjustment_status": prov["adjustment_status"],
                                "membership_status": prov["membership_status"]}
    if not readiness_pass:
        stages["readiness"] = {"status": "INCONCLUSIVE", "reason": "hash_bound_research_readiness_evidence_required"}
    else:
        stages["readiness"] = {"status": "PASS"}
    if target_timing is not None:
        if not isinstance(target_timing, pd.DataFrame) or not {"TRADE_DATE", "TARGET_DATE"}.issubset(target_timing.columns):
            stages["temporal"] = {"status": "INCONCLUSIVE", "reason": "target_dates_not_supplied_for_validation"}
        else:
            temporal = check_temporal_leakage(target_timing)
            stages["temporal"] = {"status": temporal.status, "message": temporal.message, "evidence": temporal.evidence}
    else:
        stages["temporal"] = {"status": "INCONCLUSIVE", "reason": "target_dates_not_supplied_for_validation"}

    if validation_evidence is None:
        stages["validation"] = {"status": "INCONCLUSIVE", "reason": "experiment_validation_evidence_missing"}
    else:
        validated = validate_experiment(validation_evidence)
        validation_hash = prov.get("validation_evidence_sha256")
        experiment_passed = validated.status in {"VALIDATED", "VALIDATED_RESEARCH_EDGE"}
        hashes_bound = (_valid_sha256(validation_hash)
                        and _valid_sha256(prov.get("validated_source_sha256"))
                        and str(prov.get("validated_source_sha256")).lower() == str(digest).lower()
                        and isinstance(probability_evidence, Mapping)
                        and str(probability_evidence.get("source_sha256", "")).lower() == str(digest).lower()
                        and str(probability_evidence.get("validation_evidence_sha256", "")).lower() == str(validation_hash).lower())
        stage_status = "PASS" if experiment_passed and hashes_bound else (validated.status if not experiment_passed else "INCONCLUSIVE")
        stages["validation"] = {"status": stage_status,
                                 "failure_reason": validated.failure_reason if not experiment_passed else (None if hashes_bound else "validation_probability_source_hash_chain_missing_or_mismatched"),
                                 "experiment_id": validated.experiment_id,
                                 "evidence_hash_bound_to_source": hashes_bound}

    probability_check = _validate_probability(probability_evidence)
    stages["probability_validation"] = probability_check
    ev = _expected_value(probability_evidence, costs)
    if stages["validation"]["status"] != "PASS" and ev["status"] != "INCONCLUSIVE":
        ev = {"status": "INCONCLUSIVE", "reason": "validated_experiment_and_hash_chain_required", "value": None}
    stages["expected_value"] = ev
    risk: dict[str, Any] = ({"status": "INCONCLUSIVE", "reason": "validated_positive_expected_value_required"}
                            if ev["status"] != "PASS" else evaluate_cash_equity_risk(risk_inputs))
    stages["risk"] = risk

    failed = [name for name, value in stages.items() if value.get("status") != "PASS"]
    critic = {"status": "REVIEW_REQUIRED", "blocking_gates": failed,
              "ranking_is_probability": False,
              "limitations": ["No AI-generated estimates are used.", "Unadjusted corporate-action status and historical membership require explicit evidence.",
                              "Daily EOD data does not establish intraday availability or option-chain evidence."]}
    if critic_evaluator is None:
        stages["ai_critic"] = {"status": "INCONCLUSIVE", "reason": "AI_critic_adapter_not_configured",
                               "deterministic_evidence_summary": True}
    elif failed:
        stages["ai_critic"] = {"status": "NOT_RUN", "reason": "upstream_gates_not_passed"}
    else:
        try:
            review = dict(critic_evaluator({"request": canonical_request, "stages": stages, "candidate": candidate,
                                            "expected_value": ev, "risk": risk}))
        except Exception as exc:
            review = {}
            stages["ai_critic"] = {"status": "INCONCLUSIVE", "reason": "critic_adapter_error", "error_type": type(exc).__name__}
        if not stages.get("ai_critic"):
            review_hash = review.get("critic_sha256")
            if (review.get("status") == "PASS" and isinstance(review_hash, str) and len(review_hash) == SHA256_LENGTH
                    and all(c in "0123456789abcdefABCDEF" for c in review_hash)
                    and isinstance(review.get("model"), str) and isinstance(review.get("review_id"), str)):
                stages["ai_critic"] = {"status": "PASS", "model": review["model"],
                                       "review_id": review["review_id"], "critic_sha256": review_hash.lower()}
            else:
                stages["ai_critic"] = {"status": "INCONCLUSIVE", "reason": "critic_review_schema_or_hash_invalid"}
    if stages["ai_critic"]["status"] != "PASS":
        failed.append("ai_critic")
    critic["blocking_gates"] = failed
    critic["status"] = "PASS" if stages["ai_critic"]["status"] == "PASS" else "REVIEW_REQUIRED"
    gates_pass = not failed
    gates_pass = gates_pass and stages["ai_critic"]["status"] == "PASS"
    proposal = None
    if gates_pass and candidate is not None:
        proposal = {"type": "RESEARCH_PROPOSAL", "symbol": request.symbol,
                   "human_approval_required": True, "automatic_execution": False,
                   "expected_value": ev["value"], "max_units": risk["max_units"]}
    stages["proposal"] = {"status": "PASS" if proposal else "NOT_RUN", "reason": "proposal_gates_passed" if proposal else "blocking_gates_present"}
    stages["human_approval"] = {"status": "REQUIRED" if proposal else "NOT_RUN", "automatic_execution": False}
    decision = "RESEARCH_PROPOSAL" if proposal else "NO_TRADE"
    fingerprint = _sha256(json.dumps({"request": canonical_request, "source_sha256": digest}, sort_keys=True).encode())[:24]
    return {"schema_version": RESPONSE_SCHEMA_VERSION, "run_id": fingerprint, "request": canonical_request,
            "decision": decision, "reason": "all_research_gates_passed_pending_human_approval" if proposal else "one_or_more_required_gates_not_passed",
            "stages": stages, "critic": critic, "proposal": proposal,
            "execution": {"human_approval_required": True, "automatic_execution": False}}



def run_ingested_records(
    payload: Mapping[str, Any],
    accepted_records: list[Mapping[str, Any]],
    *,
    isin_by_symbol: Mapping[str, str],
    instrument_master_sha256: str | None,
    provenance: Mapping[str, Any],
    **evidence: Any,
) -> dict[str, Any]:
    """Bridge provenance-bound normalized records into research analysis.

    Every record must match the supplied source hash, ingestion run ID,
    and schema version. Instrument identity and research readiness remain
    separate required gates. No trades are executed.
    """
    request = AnalysisRequest.parse(payload)

    def reject_ingestion(status: str, reason: str) -> dict[str, Any]:
        result = run_research_analysis(
            payload, None, provenance=provenance, **evidence
        )
        result["stages"]["ingestion"] = {
            "status": status,
            "reason": reason,
        }
        result["decision"] = "NO_TRADE"
        result["proposal"] = None
        result["execution"] = {
            "human_approval_required": True,
            "automatic_execution": False,
        }
        return result

    if not _valid_sha256(instrument_master_sha256):
        return reject_ingestion(
            "INCONCLUSIVE",
            "hashed_instrument_master_required_for_symbol_to_isin_mapping",
        )

    if not accepted_records:
        return reject_ingestion(
            "INCONCLUSIVE",
            "no_accepted_normalized_rows",
        )

    expected_source_hash = provenance.get("source_sha256")
    expected_run_id = provenance.get("ingestion_run_id")
    expected_schema = provenance.get("schema_version")

    if not _valid_sha256(expected_source_hash):
        return reject_ingestion(
            "INCONCLUSIVE",
            "valid_provenance_source_sha256_required",
        )

    if not isinstance(expected_run_id, str) or not expected_run_id.strip():
        return reject_ingestion(
            "INCONCLUSIVE",
            "ingestion_run_id_required",
        )

    if not isinstance(expected_schema, str) or not expected_schema.strip():
        return reject_ingestion(
            "INCONCLUSIVE",
            "provenance_schema_version_required",
        )

    expected_source_hash = expected_source_hash.lower()
    rows = []

    for index, record in enumerate(accepted_records, start=1):
        if not isinstance(record, Mapping):
            return reject_ingestion(
                "FAIL",
                f"invalid_normalized_record:{index}",
            )

        record_hash = record.get("source_sha256")
        if (
            not _valid_sha256(record_hash)
            or record_hash.lower() != expected_source_hash
        ):
            return reject_ingestion(
                "FAIL",
                f"source_hash_mismatch:{index}",
            )

        if record.get("ingestion_run_id") != expected_run_id:
            return reject_ingestion(
                "FAIL",
                f"ingestion_run_id_mismatch:{index}",
            )

        if record.get("schema_version") != expected_schema:
            return reject_ingestion(
                "FAIL",
                f"schema_version_mismatch:{index}",
            )

        values = record.get("values")
        if not isinstance(values, Mapping):
            return reject_ingestion(
                "FAIL",
                f"normalized_record_values_invalid:{index}",
            )

        symbol = str(values.get("symbol") or "").strip().upper()
        isin = isin_by_symbol.get(symbol)

        required = (
            "trading_date",
            "open",
            "high",
            "low",
            "close",
            "previous_close",
            "net_traded_quantity",
            "net_traded_value",
        )

        if (
            not symbol
            or symbol != request.symbol
            or not isinstance(isin, str)
            or not isin.strip()
            or any(values.get(key) is None for key in required)
        ):
            return reject_ingestion(
                "INCONCLUSIVE",
                "normalized_rows_lack_required_fields_or_verified_symbol_to_isin_mapping",
            )

        rows.append({
            "TRADE_DATE": values["trading_date"],
            "ISIN": isin.strip(),
            "SYMBOL": symbol,
            "OPNPRIC": values["open"],
            "HGHPRIC": values["high"],
            "LWPRIC": values["low"],
            "CLSPRIC": values["close"],
            "PRVSCLSGPRIC": values["previous_close"],
            "TTLTRADGVOL": values["net_traded_quantity"],
            "TTLTRFVAL": values["net_traded_value"],
        })

    ingestion_evidence = {
        "status": "PASS",
        "schema_version": expected_schema,
        "source_sha256": expected_source_hash,
        "ingestion_run_id": expected_run_id,
        "instrument_master_sha256": instrument_master_sha256.lower(),
    }

    result = run_research_analysis(
        payload,
        pd.DataFrame(rows),
        provenance=provenance,
        nifty_context=evidence.pop("nifty_context", None),
        ingestion_evidence=ingestion_evidence,
        **evidence,
    )

    result["stages"]["ingestion"].update({
        "accepted_rows": len(rows),
        "adapter": "provenance_bound_normalized_records_to_daily_research_frame",
        "raw_source_mutated": False,
        "ingestion_run_id": expected_run_id,
    })

    return result
