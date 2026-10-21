"""Synthetic software fixtures for explicit-path dataset readiness inventory."""
import hashlib
import json
from pathlib import Path

import pytest

from research.market.dataset_readiness import build_readiness_report, render_markdown


REQUIREMENTS = ["source_authorization", "schema_and_units_review", "coverage_calendar",
                "instrument_identity", "availability_semantics", "independent_evaluation_protocol"]


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_inventory_only_reads_configured_roots_and_hashes_files(tmp_path):
    configured = tmp_path / "data" / "included"
    configured.mkdir(parents=True)
    payload = configured / "one.csv"
    payload.write_text("SYNTHETIC_FIXTURE_ONLY\n", encoding="utf-8")
    unrelated = tmp_path / "unrelated" / "private.csv"
    unrelated.parent.mkdir()
    unrelated.write_text("DO_NOT_INVENTORY\n", encoding="utf-8")
    config = {
        "datasets": [{"dataset_id": "fixture", "category": "daily_equity_eod",
                      "schema_version": None, "paths": ["data/included"],
                      "research_requirements": REQUIREMENTS, "limitations": []}]
    }
    write_json(tmp_path / "config.json", config)

    report = build_readiness_report(tmp_path, Path("config.json"))
    dataset = report["datasets"][0]
    assert dataset["state"] == "PRESENT_UNVALIDATED"
    assert dataset["file_count"] == 1
    assert dataset["configured_paths"][0]["files"][0]["sha256"] == hashlib.sha256(payload.read_bytes()).hexdigest()
    assert "unrelated/private.csv" not in json.dumps(report)
    assert report["research_ready_dataset_ids"] == []
    assert build_readiness_report(tmp_path, Path("config.json")) == report


def test_missing_and_present_empty_directories_are_distinct(tmp_path):
    (tmp_path / "data" / "present-empty").mkdir(parents=True)
    write_json(tmp_path / "config.json", {"datasets": [
        {"dataset_id": "missing", "category": "trades", "paths": ["data/missing"], "research_requirements": REQUIREMENTS},
        {"dataset_id": "empty", "category": "order_book_snapshot_fixture", "paths": ["data/present-empty"], "research_requirements": REQUIREMENTS},
    ]})
    report = build_readiness_report(tmp_path, Path("config.json"))
    assert [item["state"] for item in report["datasets"]] == ["MISSING", "PRESENT_UNVALIDATED"]
    assert [item["availability_state"] for item in report["datasets"]] == ["NO_DATA", "NO_DATA"]
    assert report["datasets"][1]["file_count"] == 0


def test_matching_format_evidence_is_not_enough_for_research_readiness(tmp_path):
    source = tmp_path / "data/source.csv"
    source.parent.mkdir(parents=True)
    source.write_text("SYNTHETIC_FIXTURE_ONLY\n", encoding="utf-8")
    schema_path = tmp_path / "schemas/example.json"
    write_json(schema_path, {"schema_version": "test-v1"})
    audit = tmp_path / "reports/audit.md"
    audit.parent.mkdir()
    audit.write_text("SYNTHETIC_FIXTURE_ONLY format audit", encoding="utf-8")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    validation = tmp_path / "reports/validation.json"
    write_json(validation, {"source_filename": "source.csv", "source_sha256": source_hash, "schema_version": "test-v1",
                            "parser_error": None, "row_count": 2, "accepted_count": 1,
                            "rejected_count": 1})
    config = {"datasets": [{
        "dataset_id": "validated-fixture", "category": "daily_equity_eod",
        "schema_version": "test-v1", "paths": ["data/source.csv"],
        "schema_path": "schemas/example.json",
        "format_validation": {"validation_report": "reports/validation.json", "audit_report": "reports/audit.md"},
        "research_requirements": REQUIREMENTS,
    }]}
    write_json(tmp_path / "config.json", config)
    report = build_readiness_report(tmp_path, Path("config.json"))
    dataset = report["datasets"][0]
    assert dataset["state"] == "VALIDATED_FORMAT"
    assert dataset["format_validation_evidence"]["source_hash_matches_validation"] is True
    assert dataset["missing_research_requirements"] == REQUIREMENTS

    evidence = tmp_path / "reports/authorization.txt"
    evidence.write_text("SYNTHETIC_FIXTURE_ONLY evidence", encoding="utf-8")
    config["datasets"][0]["research_evidence"] = {
        name: {"path": "reports/authorization.txt", "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest()}
        for name in REQUIREMENTS
    }
    write_json(tmp_path / "config.json", config)
    hash_only = build_readiness_report(tmp_path, Path("config.json"))["datasets"][0]
    assert hash_only["state"] == "VALIDATED_FORMAT"
    assert all(item["status"] == "missing_or_invalid_human_attestation" for item in hash_only["research_evidence"].values())
    config["datasets"][0]["research_evidence"] = {
        name: {"path": "reports/authorization.txt", "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
               "verification_status": "verified", "reviewed_by": "synthetic-test-reviewer",
               "reviewed_at": "2026-10-17T12:00:00Z", "assessment": "SYNTHETIC_FIXTURE_ONLY"}
        for name in REQUIREMENTS
    }
    write_json(tmp_path / "config.json", config)
    ready = build_readiness_report(tmp_path, Path("config.json"))["datasets"][0]
    assert ready["state"] == "RESEARCH_READY"


def test_format_validation_rejects_mismatched_source_hash(tmp_path):
    source = tmp_path / "data/source.csv"
    source.parent.mkdir(parents=True)
    source.write_text("SYNTHETIC_FIXTURE_ONLY\n", encoding="utf-8")
    write_json(tmp_path / "schema.json", {"schema_version": "test-v1"})
    (tmp_path / "audit.md").write_text("SYNTHETIC_FIXTURE_ONLY", encoding="utf-8")
    write_json(tmp_path / "validation.json", {"source_filename": "source.csv", "source_sha256": "0" * 64,
        "schema_version": "test-v1", "parser_error": None, "row_count": 1,
        "accepted_count": 1, "rejected_count": 0})
    write_json(tmp_path / "config.json", {"datasets": [{
        "dataset_id": "mismatch", "category": "daily_index_eod", "schema_version": "test-v1",
        "paths": ["data/source.csv"], "schema_path": "schema.json",
        "format_validation": {"validation_report": "validation.json", "audit_report": "audit.md"},
        "research_requirements": REQUIREMENTS,
    }]})
    dataset = build_readiness_report(tmp_path, Path("config.json"))["datasets"][0]
    assert dataset["state"] == "PRESENT_UNVALIDATED"
    assert dataset["format_validation_evidence"] is None


def test_filename_date_coverage_is_labelled_unverified_and_markdown_is_portable(tmp_path):
    dataset_dir = tmp_path / "data/raw"
    dataset_dir.mkdir(parents=True)
    (dataset_dir / "BhavCopy_20240102.csv").write_text("fixture", encoding="utf-8")
    (dataset_dir / "BhavCopy_20240231.csv").write_text("fixture", encoding="utf-8")
    write_json(tmp_path / "config.json", {"datasets": [{
        "dataset_id": "dated-fixture", "category": "daily_equity_eod", "paths": ["data/raw"],
        "date_filename_pattern": "^BhavCopy_(?P<date>\\d{8})\\.csv$", "date_format": "%Y%m%d",
        "research_requirements": REQUIREMENTS,
    }]})
    report = build_readiness_report(tmp_path, Path("config.json"))
    coverage = report["datasets"][0]["configured_paths"][0]["date_coverage"]
    assert coverage["first_filename_date"] == "2024-01-02"
    assert coverage["unique_filename_dates"] == 1
    assert coverage["files_without_valid_filename_date"] == 1
    assert coverage["verified_trading_dates"] is False
    markdown = render_markdown(report)
    assert "not verified trading dates" in markdown
    assert str(tmp_path) not in markdown


@pytest.mark.parametrize("bad_path", ["../outside", "C:/outside", "/outside"])
def test_paths_cannot_escape_configured_project_root(tmp_path, bad_path):
    write_json(tmp_path / "config.json", {"datasets": [{
        "dataset_id": "bad", "category": "daily_index_eod", "paths": [bad_path],
        "research_requirements": REQUIREMENTS,
    }]})
    with pytest.raises(ValueError, match="project_relative|escapes"):
        build_readiness_report(tmp_path, Path("config.json"))


def test_markdown_contains_no_data_and_no_trade_state_when_no_dataset_ready(tmp_path):
    write_json(tmp_path / "config.json", {"datasets": [{
        "dataset_id": "missing-index", "category": "daily_index_eod", "paths": ["data/missing"],
        "research_requirements": REQUIREMENTS,
    }]})
    report = build_readiness_report(tmp_path, Path("config.json"))
    markdown = render_markdown(report)
    assert report["decision_state"] == "NO_TRADE"
    assert report["state_counts"]["MISSING"] == 1
    assert report["datasets"][0]["availability_state"] == "NO_DATA"
    assert "**MISSING**" in markdown
    assert "**NO_TRADE**" in markdown


def test_config_cannot_remove_category_minimum_research_evidence(tmp_path):
    write_json(tmp_path / "config.json", {"datasets": [{
        "dataset_id": "incomplete-index-policy", "category": "daily_index_eod",
        "paths": ["data/index"], "research_requirements": ["source_authorization"],
    }]})
    with pytest.raises(ValueError, match="research_requirements_below_category_minimum"):
        build_readiness_report(tmp_path, Path("config.json"))
