"""Explicit-path, local-only dataset inventory and readiness reporting.

Only dataset paths named in the project readiness JSON are traversed. The
inventory hashes files but does not parse market rows or infer research merit.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sys
from typing import Any, Mapping


TOOL_VERSION = "5i.1"
DATASET_STATES = ("MISSING", "PRESENT_UNVALIDATED", "VALIDATED_FORMAT", "RESEARCH_READY")
_SENSITIVE_NAMES = {".env", ".env.local", "id_rsa", "id_ed25519"}
_CATEGORY_REQUIREMENTS = {
    "daily_equity_eod": {"source_authorization", "schema_and_units_review", "coverage_calendar", "instrument_identity", "availability_semantics", "independent_evaluation_protocol"},
    "daily_index_eod": {"source_authorization", "schema_and_units_review", "coverage_calendar", "instrument_identity", "availability_semantics", "independent_evaluation_protocol"},
    "intraday_bars": {"source_authorization", "schema_and_units_review", "coverage_calendar", "instrument_identity", "event_publication_receipt_times", "independent_evaluation_protocol"},
    "historical_trades": {"source_authorization", "schema_and_units_review", "coverage_calendar", "instrument_identity", "event_publication_receipt_times", "independent_evaluation_protocol"},
    "order_book_snapshots": {"source_authorization", "schema_and_units_review", "coverage_calendar", "instrument_identity", "capture_publication_receipt_times", "independent_evaluation_protocol"},
    "futures_options": {"source_authorization", "schema_and_units_review", "coverage_calendar", "contract_identity_and_reference", "event_publication_receipt_times", "independent_evaluation_protocol"},
}


def _relative_path(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("configured_path_must_be_nonempty_string")
    relative = PurePosixPath(value.replace("\\", "/"))
    if (relative.is_absolute() or PureWindowsPath(value).is_absolute()
            or PureWindowsPath(value).drive
            or any(part in {"..", ""} for part in relative.parts)):
        raise ValueError("configured_path_must_stay_project_relative")
    candidate = root.joinpath(*relative.parts)
    if candidate.is_symlink():
        raise ValueError("configured_path_must_not_be_symlink")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("configured_path_escapes_project_root") from exc
    return candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sensitive(name: str) -> bool:
    lowered = name.lower()
    return (
        lowered in _SENSITIVE_NAMES
        or lowered.startswith(".env.")
        or "credential" in lowered
        or "secret" in lowered
        or lowered.endswith((".pem", ".key"))
    )


def _files_under(path: Path) -> tuple[list[Path], int]:
    if path.is_file():
        if _is_sensitive(path.name):
            return [], 1
        return [path], 0
    files: list[Path] = []
    excluded_sensitive = 0
    for directory, dirnames, filenames in os.walk(path, followlinks=False):
        current = Path(directory)
        dirnames[:] = sorted(
            name for name in dirnames
            if not (current / name).is_symlink() and not _is_sensitive(name)
        )
        for name in sorted(filenames):
            file_path = current / name
            if file_path.is_symlink():
                continue
            if _is_sensitive(name):
                excluded_sensitive += 1
                continue
            if file_path.is_file():
                files.append(file_path)
    return files, excluded_sensitive


def _inventory_path(root: Path, relative: str, date_pattern: re.Pattern[str] | None,
                    date_format: str | None) -> dict[str, Any]:
    path = _relative_path(root, relative)
    base = {"configured_path": relative.replace("\\", "/"), "exists": path.exists()}
    if not path.exists():
        return {**base, "file_count": 0, "total_bytes": 0, "files": [], "date_coverage": None}
    if not path.is_file() and not path.is_dir():
        return {**base, "file_count": 0, "total_bytes": 0, "files": [],
                "inspection_error": "configured_path_is_not_file_or_directory", "date_coverage": None}
    files, excluded_sensitive_count = _files_under(path)
    entries = []
    observed_dates: set[str] = set()
    for file_path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        relative_file = file_path.relative_to(root).as_posix()
        date_value = None
        if date_pattern is not None and date_format is not None:
            match = date_pattern.fullmatch(file_path.name)
            if match is not None:
                try:
                    date_value = datetime.strptime(match.group("date"), date_format).date().isoformat()
                    observed_dates.add(date_value)
                except ValueError:
                    date_value = None
        entries.append({"path": relative_file, "size_bytes": file_path.stat().st_size,
                        "sha256": _sha256(file_path), "filename_date_observed": date_value})
    coverage = None
    if date_pattern is not None:
        dates = sorted(observed_dates)
        coverage = {
            "method": "configured_filename_pattern_only",
            "verified_trading_dates": False,
            "unique_filename_dates": len(dates),
            "first_filename_date": dates[0] if dates else None,
            "last_filename_date": dates[-1] if dates else None,
            "files_without_valid_filename_date": len(files) - sum(
                entry["filename_date_observed"] is not None for entry in entries
            ),
        }
    return {
        **base,
        "is_directory": path.is_dir(),
        "file_count": len(entries),
        "total_bytes": sum(entry["size_bytes"] for entry in entries),
        "excluded_sensitive_name_count": excluded_sensitive_count,
        "files": entries,
        "date_coverage": coverage,
    }


def _verify_format_evidence(root: Path, dataset: Mapping[str, Any], paths: list[dict[str, Any]],
                            schema_version: str | None, schema_path: str | None) -> dict[str, Any] | None:
    evidence_spec = dataset.get("format_validation")
    if not isinstance(evidence_spec, Mapping):
        return None
    source_entries = [entry for inspected in paths for entry in inspected["files"]]
    if not source_entries:
        return None
    validation_rels = evidence_spec.get("validation_reports")
    if validation_rels is None:
        validation_rel = evidence_spec.get("validation_report")
        validation_rels = [validation_rel] if isinstance(validation_rel, str) else []
    audit_rel = evidence_spec.get("audit_report")
    if (not isinstance(validation_rels, list) or not validation_rels
            or not all(isinstance(item, str) for item in validation_rels)
            or not isinstance(audit_rel, str)):
        return None
    try:
        audit_path = _relative_path(root, audit_rel)
        if not audit_path.is_file():
            return None
        expected_sources = {(entry["path"].rsplit("/", 1)[-1], entry["sha256"]) for entry in source_entries}
        if len(expected_sources) != len(source_entries):
            return None
        covered_sources: set[tuple[str, str]] = set()
        validation_reports = []
        for validation_rel in validation_rels:
            validation_path = _relative_path(root, validation_rel)
            if not validation_path.is_file():
                return None
            validation = json.loads(validation_path.read_text(encoding="utf-8"))
            source_key = (validation.get("source_filename"), validation.get("source_sha256"))
            if source_key not in expected_sources or source_key in covered_sources:
                return None
            if validation.get("schema_version") != schema_version or validation.get("parser_error") is not None:
                return None
            if (not isinstance(validation.get("row_count"), int) or validation["row_count"] <= 0
                    or not isinstance(validation.get("accepted_count"), int)
                    or not isinstance(validation.get("rejected_count"), int)
                    or validation["accepted_count"] + validation["rejected_count"] != validation["row_count"]):
                return None
            covered_sources.add(source_key)
            validation_reports.append({
                "path": validation_rel,
                "sha256": _sha256(validation_path),
                "source_filename": validation.get("source_filename"),
                "source_sha256": validation.get("source_sha256"),
                "accepted_count": validation["accepted_count"],
                "rejected_count": validation["rejected_count"],
            })
        if covered_sources != expected_sources:
            return None
        if schema_path is None:
            return None
        schema_file = _relative_path(root, schema_path)
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
        if schema.get("schema_version") != schema_version:
            return None
        return {
            "status": "verified_format_evidence",
            "validation_reports": validation_reports,
            "audit_report": audit_rel,
            "audit_report_sha256": _sha256(audit_path),
            "schema_path": schema_path,
            "schema_sha256": _sha256(schema_file),
            "source_hash_matches_validation": True,
        }
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _research_evidence(root: Path, dataset: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    required = dataset.get("research_requirements", [])
    evidence = dataset.get("research_evidence", {})
    if not isinstance(required, list) or not required or not all(isinstance(item, str) and item for item in required):
        raise ValueError("research_requirements_must_be_a_nonempty_list_of_ids")
    if not isinstance(evidence, Mapping):
        raise ValueError("research_evidence_must_be_an_object")
    checks: dict[str, Any] = {}
    missing: list[str] = []
    for requirement in required:
        artifact = evidence.get(requirement)
        verified = False
        detail: dict[str, Any] = {"status": "missing_evidence"}
        if isinstance(artifact, Mapping) and isinstance(artifact.get("path"), str):
            try:
                path = _relative_path(root, artifact["path"])
                if path.is_file():
                    actual_hash = _sha256(path)
                    reviewed_by = artifact.get("reviewed_by")
                    assessment = artifact.get("assessment")
                    reviewed_at = artifact.get("reviewed_at")
                    reviewed_time = None
                    if isinstance(reviewed_at, str):
                        try:
                            reviewed_time = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
                        except ValueError:
                            reviewed_time = None
                    verified = (
                        artifact.get("verification_status") == "verified"
                        and artifact.get("sha256") == actual_hash
                        and isinstance(reviewed_by, str) and bool(reviewed_by.strip())
                        and isinstance(assessment, str) and bool(assessment.strip())
                        and reviewed_time is not None and reviewed_time.tzinfo is not None
                        and reviewed_time.utcoffset() is not None
                    )
                    if verified:
                        evidence_status = "verified_artifact"
                    elif artifact.get("sha256") != actual_hash:
                        evidence_status = "evidence_hash_mismatch"
                    else:
                        evidence_status = "missing_or_invalid_human_attestation"
                    detail = {
                        "status": evidence_status,
                        "path": artifact["path"],
                        "sha256": actual_hash,
                        "review_status": artifact.get("verification_status", "not_attested"),
                    }
            except (OSError, ValueError):
                detail = {"status": "invalid_or_missing_evidence_path"}
        checks[requirement] = detail
        if not verified:
            missing.append(requirement)
    return checks, missing


def build_readiness_report(project_root: Path, config_path: Path) -> dict[str, Any]:
    """Build deterministic inventory from one explicit, project-local config."""
    root = project_root.resolve()
    config_file = config_path if config_path.is_absolute() else root / config_path
    try:
        config_file.resolve().relative_to(root)
    except ValueError as exc:
        raise ValueError("config_must_be_inside_project_root") from exc
    if config_file.is_symlink() or not config_file.is_file():
        raise ValueError("config_file_missing_or_symlink")
    config = json.loads(config_file.read_text(encoding="utf-8"))
    datasets = config.get("datasets")
    if not isinstance(datasets, list):
        raise ValueError("config_datasets_must_be_a_list")
    ids: set[str] = set()
    result = []
    for dataset in datasets:
        if not isinstance(dataset, Mapping):
            raise ValueError("dataset_entry_must_be_an_object")
        dataset_id = dataset.get("dataset_id")
        category = dataset.get("category")
        paths = dataset.get("paths")
        if not isinstance(dataset_id, str) or not dataset_id or dataset_id in ids:
            raise ValueError("dataset_ids_must_be_unique_nonempty_strings")
        ids.add(dataset_id)
        if not isinstance(category, str) or not category:
            raise ValueError(f"{dataset_id}:category_required")
        if not isinstance(paths, list) or not paths or not all(isinstance(p, str) for p in paths):
            raise ValueError(f"{dataset_id}:paths_must_be_a_nonempty_string_list")
        configured_requirements = dataset.get("research_requirements", [])
        if (not isinstance(configured_requirements, list)
                or not all(isinstance(item, str) for item in configured_requirements)):
            raise ValueError(f"{dataset_id}:research_requirements_must_be_a_list")
        minimum_requirements = _CATEGORY_REQUIREMENTS.get(category)
        if minimum_requirements and not minimum_requirements.issubset(set(configured_requirements)):
            raise ValueError(f"{dataset_id}:research_requirements_below_category_minimum")
        date_pattern = None
        pattern = dataset.get("date_filename_pattern")
        date_format = dataset.get("date_format")
        if pattern is not None:
            if not isinstance(pattern, str) or "(?P<date>" not in pattern or not isinstance(date_format, str):
                raise ValueError(f"{dataset_id}:invalid_date_filename_rule")
            try:
                date_pattern = re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                raise ValueError(f"{dataset_id}:invalid_date_filename_rule") from exc
        path_reports = [_inventory_path(root, value, date_pattern, date_format) for value in paths]
        file_count = sum(item["file_count"] for item in path_reports)
        present = any(item["exists"] for item in path_reports)
        schema_path = dataset.get("schema_path")
        schema_version = dataset.get("schema_version")
        schema_digest = None
        if schema_path is not None:
            schema_file = _relative_path(root, schema_path)
            if schema_file.is_file():
                schema_digest = _sha256(schema_file)
                try:
                    on_disk_schema = json.loads(schema_file.read_text(encoding="utf-8"))
                    schema_version = on_disk_schema.get("schema_version", schema_version)
                except (OSError, ValueError, TypeError):
                    pass
        format_evidence = _verify_format_evidence(root, dataset, path_reports, schema_version, schema_path)
        checks, missing_research = _research_evidence(root, dataset)
        if not present:
            state = "MISSING"
        elif format_evidence is not None:
            state = "VALIDATED_FORMAT"
        else:
            state = "PRESENT_UNVALIDATED"
        if state == "VALIDATED_FORMAT" and dataset.get("research_requirements") and not missing_research:
            state = "RESEARCH_READY"
        result.append({
            "dataset_id": dataset_id,
            "category": category,
            "schema_version": schema_version,
            "schema_sha256": schema_digest,
            "availability_state": "DATA_PRESENT" if file_count else "NO_DATA",
            "state": state,
            "configured_paths": path_reports,
            "file_count": file_count,
            "total_bytes": sum(item["total_bytes"] for item in path_reports),
            "format_validation_evidence": format_evidence,
            "research_evidence": checks,
            "missing_research_requirements": missing_research,
            "limitations": list(dataset.get("limitations", [])),
        })
    return {
        "manifest_version": "1",
        "tool_version": TOOL_VERSION,
        "python_version": sys.version.split()[0],
        "inventory_scope": f"only paths explicitly listed in {config_file.relative_to(root).as_posix()}; project-relative paths; no external path traversal",
        "config_path": config_file.relative_to(root).as_posix(),
        "datasets": result,
        "state_counts": {state: sum(item["state"] == state for item in result) for state in DATASET_STATES},
        "research_ready_dataset_ids": [item["dataset_id"] for item in result if item["state"] == "RESEARCH_READY"],
        "decision_state": "NO_TRADE",
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Dataset Readiness Inventory",
        "",
        f"- Tool version: `{report['tool_version']}`",
        f"- Python: `{report['python_version']}`",
        f"- Config: `{report['config_path']}`",
        f"- Scope: {report['inventory_scope']}",
        f"- Decision state: **{report['decision_state']}**",
        "",
        "| Dataset | Category | Availability | Readiness | Files | Size | Schema version | Date coverage |",
        "|---|---|---|---|---:|---:|---|---|",
    ]
    for item in report["datasets"]:
        coverages = [path["date_coverage"] for path in item["configured_paths"] if path.get("date_coverage")]
        date_text = "; ".join(
            f"filename dates {coverage['first_filename_date']}–{coverage['last_filename_date']} ({coverage['unique_filename_dates']} unique; not verified trading dates)"
            if coverage["unique_filename_dates"] else "filename pattern yielded no valid dates"
            for coverage in coverages
        ) or "not established"
        size = f"{item['total_bytes']:,} B"
        schema = item["schema_version"] or "unknown"
        lines.append(f"| `{item['dataset_id']}` | `{item['category']}` | **{item['availability_state']}** | **{item['state']}** | {item['file_count']} | {size} | `{schema}` | {date_text} |")
        if item["missing_research_requirements"]:
            lines.append(f"|  | Missing research evidence | {', '.join(item['missing_research_requirements'])} |  |  |  |  |  |")
        for limitation in item["limitations"]:
            lines.append(f"|  | Limitation | {limitation.replace('|', '\\|')} |  |  |  |  |  |")
    lines += [
        "",
        "## State meanings",
        "",
        "- `MISSING`: a configured path was inspected and did not exist.",
        "- `PRESENT_UNVALIDATED`: configured files or directories exist, but matching format-validation evidence was not verified.",
        "- `VALIDATED_FORMAT`: schema/version and source hash match a saved validation report, and a format-audit report exists. This says nothing about licensing, completeness, or predictive value.",
        "- `RESEARCH_READY`: format evidence plus every explicitly required, hash-verified research artifact. File presence or parse success alone cannot produce this state.",
        "",
        "Date coverage is filename-derived where configured and is labelled as such; it is not proof of trading sessions or complete market coverage. No files outside configured project-relative paths are inspected. No secret or `.env` contents are read.",
        "",
    ]
    return "\n".join(lines)


def _write_new(root: Path, relative: str, content: str) -> None:
    destination = _relative_path(root, relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite existing report: {relative}")
    destination.write_text(content, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Inventory explicitly configured local dataset paths; no market data is ingested.")
    parser.add_argument("--config", default="data/market/readiness/dataset_config.json", help="project-relative readiness config")
    parser.add_argument("--json-output", default="reports/PHASE5I_DATASET_READINESS.json", help="new project-relative JSON report path")
    parser.add_argument("--markdown-output", default="reports/PHASE5I_DATASET_READINESS.md", help="new project-relative Markdown report path")
    args = parser.parse_args(argv)
    try:
        json_destination = _relative_path(root, args.json_output)
        markdown_destination = _relative_path(root, args.markdown_output)
        if json_destination.exists() or markdown_destination.exists():
            raise FileExistsError("refusing to overwrite an existing readiness report")
        report = build_readiness_report(root, Path(args.config))
        _write_new(root, args.json_output, json.dumps(report, indent=2, sort_keys=True) + "\n")
        _write_new(root, args.markdown_output, render_markdown(report))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps({"state_counts": report["state_counts"], "research_ready_dataset_ids": report["research_ready_dataset_ids"], "decision_state": report["decision_state"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
