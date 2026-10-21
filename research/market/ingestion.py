"""Provider-neutral, local-only market data ingestion.

Formats and schemas must be selected explicitly. This module does not infer
NSE field meanings, fetch data, execute orders, or treat file retrieval time as
historical market availability.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from enum import Enum
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import tempfile
from typing import Any, Callable, Iterable, Mapping, Sequence, TextIO
import zipfile
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

PIPELINE_VERSION = "5f.1"


class DatasetType(str, Enum):
    DAILY_SECURITY_BHAVCOPY = "daily_security_bhavcopy"
    DAILY_INDEX = "daily_index"
    INTRADAY_INDEX = "intraday_index"
    TRADE = "trade"
    ORDER_BOOK_SNAPSHOT = "order_book_snapshot"
    DERIVATIVE_DAILY = "derivative_daily"
    REFERENCE_MASTER = "reference_master"


class HeaderMode(str, Enum):
    HEADERED = "headered"
    HEADERLESS = "headerless"


@dataclass(frozen=True)
class FieldSpec:
    name: str
    source: str | int
    value_type: str
    required: bool = True
    date_format: str | None = None
    timezone: str | None = None
    unit: str | None = None


@dataclass(frozen=True)
class IngestionSchema:
    format_id: str
    parser_id: str
    schema_version: str
    dataset_type: DatasetType
    record_type: str
    delimiter: str
    encoding: str
    header_mode: HeaderMode
    fields: tuple[FieldSpec, ...]
    duplicate_key: tuple[str, ...]
    trading_date_field: str | None = None
    event_time_field: str | None = None
    source_available_time_field: str | None = None
    local_receipt_time_field: str | None = None
    quality_profile: str = "none"
    positive_fields: tuple[str, ...] = ()
    nonnegative_fields: tuple[str, ...] = ()

    def validate(self) -> tuple[str, ...]:
        issues: list[str] = []
        if not self.format_id.strip() or not self.schema_version.strip():
            issues.append("format_id_and_schema_version_required")
        if len(self.delimiter) != 1:
            issues.append("delimiter_must_be_one_character")
        if not self.encoding.strip():
            issues.append("encoding_required")
        if not self.record_type.strip():
            issues.append("record_type_required")
        if not self.fields:
            issues.append("at_least_one_field_required")
        names = [field.name for field in self.fields]
        fields_by_name = {field.name: field for field in self.fields}
        if len(names) != len(set(names)):
            issues.append("duplicate_canonical_field_name")
        sources = [field.source for field in self.fields]
        if len(sources) != len(set(sources)):
            issues.append("duplicate_source_field")
        allowed_types = {"string", "int", "float", "date", "datetime"}
        for field in self.fields:
            if not field.name.strip() or field.value_type not in allowed_types:
                issues.append(f"invalid_field_definition:{field.name}")
            if self.header_mode == HeaderMode.HEADERED and not isinstance(field.source, str):
                issues.append(f"headered_source_must_be_name:{field.name}")
            if self.header_mode == HeaderMode.HEADERLESS and (
                not isinstance(field.source, int) or isinstance(field.source, bool) or field.source < 0
            ):
                issues.append(f"headerless_source_must_be_nonnegative_index:{field.name}")
            if field.timezone:
                try:
                    ZoneInfo(field.timezone)
                except ZoneInfoNotFoundError:
                    issues.append(f"unknown_timezone:{field.timezone}")
        for name in (
            self.trading_date_field,
            self.event_time_field,
            self.source_available_time_field,
            self.local_receipt_time_field,
        ):
            if name is not None and name not in names:
                issues.append(f"timestamp_field_not_mapped:{name}")
        if self.trading_date_field in fields_by_name and fields_by_name[self.trading_date_field].value_type != "date":
            issues.append("trading_date_field_must_be_date")
        for name in (self.event_time_field, self.source_available_time_field, self.local_receipt_time_field):
            if name in fields_by_name and fields_by_name[name].value_type != "datetime":
                issues.append(f"timestamp_field_must_be_datetime:{name}")
        if not self.duplicate_key or any(name not in names for name in self.duplicate_key):
            issues.append("duplicate_key_must_name_mapped_fields")
        if self.quality_profile not in {"none", "ohlcv"}:
            issues.append(f"unsupported_quality_profile:{self.quality_profile}")
        if self.quality_profile == "ohlcv":
            for name in ("open", "high", "low", "close"):
                if name not in names or self._field(name).value_type not in {"int", "float"}:
                    issues.append(f"ohlcv_profile_requires_numeric_{name}")
                elif name not in self.positive_fields:
                    issues.append(f"ohlcv_profile_requires_positive_constraint:{name}")
            if "volume" in names and "volume" not in self.nonnegative_fields:
                issues.append("ohlcv_profile_requires_nonnegative_volume_constraint")
        for name in (*self.positive_fields, *self.nonnegative_fields):
            if name not in names or self._field(name).value_type not in {"int", "float"}:
                issues.append(f"numeric_constraint_requires_numeric_field:{name}")
        return tuple(dict.fromkeys(issues))

    def _field(self, name: str) -> FieldSpec:
        return next(field for field in self.fields if field.name == name)

    def canonical_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["dataset_type"] = self.dataset_type.value
        value["header_mode"] = self.header_mode.value
        return value


@dataclass(frozen=True)
class RowRejection:
    source_row_number: int
    reasons: tuple[str, ...]
    source_values: Mapping[str, str]


@dataclass(frozen=True)
class ParseResult:
    accepted: tuple[Mapping[str, Any], ...]
    rejected: tuple[RowRejection, ...]
    row_count: int
    warnings: tuple[str, ...]
    parser_error: str | None = None


ParserFunction = Callable[[TextIO, IngestionSchema], ParseResult]
PARSER_REGISTRY: dict[str, ParserFunction] = {}
PARSER_DESCRIPTIONS: dict[str, str] = {}


def register_parser(parser_id: str, parser: ParserFunction, *, description: str) -> None:
    """Register an explicit parser implementation for a schema's parser ID."""
    if not parser_id.strip() or not description.strip() or not callable(parser):
        raise ValueError("parser_id, callable parser, and description are required")
    PARSER_REGISTRY[parser_id] = parser
    PARSER_DESCRIPTIONS[parser_id] = description


def schema_from_dict(raw: Mapping[str, Any]) -> IngestionSchema:
    """Build and validate an explicit schema configuration."""
    try:
        fields = tuple(FieldSpec(**item) for item in raw["fields"])
        schema = IngestionSchema(
            format_id=str(raw["format_id"]),
            parser_id=str(raw["parser_id"]),
            schema_version=str(raw["schema_version"]),
            dataset_type=DatasetType(raw["dataset_type"]),
            record_type=str(raw["record_type"]),
            delimiter=str(raw["delimiter"]),
            encoding=str(raw["encoding"]),
            header_mode=HeaderMode(raw["header_mode"]),
            fields=fields,
            duplicate_key=tuple(raw["duplicate_key"]),
            trading_date_field=raw.get("trading_date_field"),
            event_time_field=raw.get("event_time_field"),
            source_available_time_field=raw.get("source_available_time_field"),
            local_receipt_time_field=raw.get("local_receipt_time_field"),
            quality_profile=str(raw.get("quality_profile", "none")),
            positive_fields=tuple(raw.get("positive_fields", ())),
            nonnegative_fields=tuple(raw.get("nonnegative_fields", ())),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid schema configuration: {exc}") from exc
    issues = schema.validate()
    if issues:
        raise ValueError("invalid schema configuration: " + ", ".join(issues))
    if schema.parser_id not in PARSER_REGISTRY:
        raise ValueError(f"unsupported parser_id {schema.parser_id!r}; registered: {sorted(PARSER_REGISTRY)}")
    return schema


def load_schema(path: Path) -> IngestionSchema:
    """Read a caller-selected local JSON schema; no discovery/guessing."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read schema file {path}: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise ValueError("schema root must be a JSON object")
    return schema_from_dict(raw)


def _parse_value(raw: str, field: FieldSpec) -> Any:
    value = raw.strip()
    if not value:
        return None
    if field.value_type == "string":
        return raw
    if field.value_type == "int":
        if not re.fullmatch(r"[+-]?\d+", value):
            raise ValueError("invalid_integer")
        return int(value)
    if field.value_type == "float":
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("non_finite_number")
        return number
    if field.value_type == "date":
        parsed_date = datetime.strptime(value, field.date_format).date() if field.date_format else date.fromisoformat(value)
        return parsed_date.isoformat()
    if field.value_type == "datetime":
        if field.date_format:
            parsed_dt = datetime.strptime(value, field.date_format)
        else:
            normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
            parsed_dt = datetime.fromisoformat(normalized)
        if parsed_dt.tzinfo is None or parsed_dt.utcoffset() is None:
            if not field.timezone:
                raise ValueError("naive_datetime_without_configured_timezone")
            parsed_dt = parsed_dt.replace(tzinfo=ZoneInfo(field.timezone))
        return parsed_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    raise ValueError(f"unsupported_type:{field.value_type}")


def _source_values(row: Sequence[str], header: Sequence[str] | None) -> dict[str, str]:
    if header is None:
        return {str(index): value for index, value in enumerate(row)}
    return {name: row[index] for index, name in enumerate(header) if index < len(row)}


def _quality_issues(values: Mapping[str, Any], schema: IngestionSchema) -> list[str]:
    issues: list[str] = []
    for name in schema.positive_fields:
        value = values.get(name)
        if value is not None and value <= 0:
            issues.append(f"non_positive_{name}")
    for name in schema.nonnegative_fields:
        value = values.get(name)
        if value is not None and value < 0:
            issues.append(f"negative_{name}")
    if schema.quality_profile == "ohlcv":
        o, h, low, c = (values.get(name) for name in ("open", "high", "low", "close"))
        if None not in (o, h, low, c):
            if h < max(o, c, low):
                issues.append("ohlc_high_below_open_close_or_low")
            if low > min(o, c, h):
                issues.append("ohlc_low_above_open_close_or_high")
        volume = values.get("volume")
        if volume is not None and volume < 0:
            issues.append("negative_volume")
    return issues


def parse_delimited(stream: TextIO, schema: IngestionSchema) -> ParseResult:
    """Parse exactly the configured delimited representation."""
    reader = csv.reader(stream, delimiter=schema.delimiter, strict=True)
    first_line = stream.readline()
    if first_line == "":
        return ParseResult((), (), 0, (), "empty_file_or_missing_header")
    stream.seek(0)
    reader = csv.reader(stream, delimiter=schema.delimiter, strict=True)
    header: list[str] | None = None
    warnings: list[str] = []
    rejected: list[RowRejection] = []
    accepted: list[Mapping[str, Any]] = []
    seen_keys: set[tuple[Any, ...]] = set()
    row_count = 0
    try:
        if schema.header_mode == HeaderMode.HEADERED:
            try:
                header = next(reader)
            except StopIteration:
                return ParseResult((), (), 0, (), "empty_file_or_missing_header")
            if not header or any(not name.strip() for name in header) or len(header) != len(set(header)):
                return ParseResult((), (), 0, (), "invalid_or_duplicate_header_columns")
            required_sources = {field.source for field in schema.fields if field.required}
            missing_headers = sorted(required_sources - set(header))
            if missing_headers:
                return ParseResult((), (), 0, (), "required_header_missing:" + ",".join(missing_headers))
            known_headers = {field.source for field in schema.fields}
            extras = sorted(set(header) - known_headers)
            if extras:
                warnings.append("unmapped_source_columns:" + ",".join(extras))

        index_by_name = {name: index for index, name in enumerate(header or ())}
        for row in reader:
            row_count += 1
            line_number = reader.line_num
            raw_map = _source_values(row, header)
            reasons: list[str] = []
            if not row or all(not value.strip() for value in row):
                reasons.append("empty_row")
            expected_len = len(header) if header is not None else max(
                int(field.source) for field in schema.fields
            ) + 1
            if len(row) != expected_len:
                reasons.append("malformed_delimiter_or_field_count")
            values: dict[str, Any] = {}
            for field in schema.fields:
                index = index_by_name.get(field.source) if header is not None else int(field.source)
                raw_value = row[index] if index is not None and index < len(row) else ""
                try:
                    parsed = _parse_value(raw_value, field)
                except (ValueError, OverflowError):
                    parsed = None
                    reasons.append(f"invalid_{field.value_type}:{field.name}")
                if parsed is None and field.required:
                    reasons.append(f"missing_required:{field.name}")
                values[field.name] = parsed
            reasons.extend(_quality_issues(values, schema))
            key = tuple(values.get(name) for name in schema.duplicate_key)
            if any(value is None for value in key):
                reasons.append("duplicate_key_missing_value")
            elif key in seen_keys:
                reasons.append("duplicate_record_key")
            else:
                seen_keys.add(key)
            if reasons:
                rejected.append(RowRejection(line_number, tuple(dict.fromkeys(reasons)), raw_map))
                continue
            normalized = {
                "dataset_type": schema.dataset_type.value,
                "record_type": schema.record_type,
                "format_id": schema.format_id,
                "schema_version": schema.schema_version,
                "source_row_number": line_number,
                "trading_date": values.get(schema.trading_date_field) if schema.trading_date_field else None,
                "event_time": values.get(schema.event_time_field) if schema.event_time_field else None,
                "source_available_time": values.get(schema.source_available_time_field) if schema.source_available_time_field else None,
                "local_receipt_time": values.get(schema.local_receipt_time_field) if schema.local_receipt_time_field else None,
                "values": values,
                "source_values": raw_map,
            }
            time_issues = _timestamp_issues(normalized)
            if time_issues:
                rejected.append(RowRejection(line_number, tuple(time_issues), raw_map))
            else:
                accepted.append(normalized)
    except csv.Error as exc:
        return ParseResult(tuple(accepted), tuple(rejected), row_count, tuple(warnings), f"csv_parse_error:{exc}")
    return ParseResult(tuple(accepted), tuple(rejected), row_count, tuple(warnings))


register_parser(
    "delimited",
    parse_delimited,
    description="Delimited text with explicitly configured delimiter, encoding, and header mode",
)
register_parser(
    "zip_delimited",
    parse_delimited,
    description="ZIP containing exactly one verified delimited text member",
)


def _timestamp_issues(record: Mapping[str, Any]) -> list[str]:
    event = record.get("event_time")
    published = record.get("source_available_time")
    received = record.get("local_receipt_time")
    if event is None:
        return []
    try:
        event_dt = _aware_datetime(event)
        published_dt = _aware_datetime(published) if published is not None else None
        received_dt = _aware_datetime(received) if received is not None else None
    except ValueError:
        return ["invalid_normalized_timestamp"]
    issues: list[str] = []
    if published_dt is not None and published_dt < event_dt:
        issues.append("source_available_before_event")
    if received_dt is not None and received_dt < event_dt:
        issues.append("local_receipt_before_event")
    if published_dt is not None and received_dt is not None and received_dt < published_dt:
        issues.append("local_receipt_before_source_available")
    return issues


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _iter_text(input_path: Path, schema: IngestionSchema) -> tuple[TextIO, Any]:
    """Open plain text or a verified one-member ZIP without extracting it."""
    if schema.parser_id == "delimited":
        handle = input_path.open("r", encoding=schema.encoding, newline="")
        return handle, handle
    if schema.parser_id != "zip_delimited":
        raise ValueError(f"unsupported parser_id {schema.parser_id!r}")
    archive = zipfile.ZipFile(input_path)
    bad_member = archive.testzip()
    if bad_member is not None:
        archive.close()
        raise ValueError(f"corrupt_zip_member:{bad_member}")
    members = [item for item in archive.infolist() if not item.is_dir()]
    if len(members) != 1:
        archive.close()
        raise ValueError(f"zip_must_contain_exactly_one_file_member:found_{len(members)}")
    member = archive.open(members[0])
    text = io.TextIOWrapper(member, encoding=schema.encoding, newline="")
    return text, (archive, text)


def _sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _safe_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")


def _failure_result(schema: IngestionSchema, reason: str) -> dict[str, Any]:
    return {
        "dataset_type": schema.dataset_type.value,
        "format_id": schema.format_id,
        "schema_version": schema.schema_version,
        "row_count": 0,
        "accepted_count": 0,
        "rejected_count": 0,
        "rejection_counts": {},
        "warnings": [],
        "parser_error": reason,
        "research_state": "NO_DATA",
        "decision_state": "NO_TRADE",
    }


def assess_replay_eligibility(
    records: Iterable[Mapping[str, Any]], decision_cutoff: datetime | str
) -> dict[str, Any]:
    """Apply a strict point-in-time gate; never substitute missing times."""
    cutoff = _aware_datetime(decision_cutoff) if isinstance(decision_cutoff, str) else decision_cutoff
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("decision_cutoff must be timezone-aware")
    cutoff = cutoff.astimezone(timezone.utc)
    items = list(records)
    if not items:
        return {
            "state": "NO_DATA",
            "eligible_count": 0,
            "unavailable_count": 0,
            "outside_cutoff_count": 0,
            "eligible_source_row_numbers": [],
        }
    eligible: list[int] = []
    unavailable = 0
    outside_cutoff = 0
    for item in items:
        event = item.get("event_time")
        available = item.get("source_available_time")
        received = item.get("local_receipt_time")
        if not event or not available or not received:
            unavailable += 1
            continue
        try:
            event_dt, available_dt, received_dt = map(_aware_datetime, (event, available, received))
        except (TypeError, ValueError):
            unavailable += 1
            continue
        if available_dt < event_dt or received_dt < available_dt:
            unavailable += 1
            continue
        if max(available_dt, received_dt) <= cutoff:
            eligible.append(int(item["source_row_number"]))
        else:
            outside_cutoff += 1
    if unavailable:
        state = "INSUFFICIENT_EVIDENCE"
    elif not eligible:
        state = "NO_TRADE"
    else:
        # Ingestion does not generate hypotheses or trading decisions.
        state = "NO_TRADE"
    return {
        "state": state,
        "eligible_count": len(eligible),
        "unavailable_count": unavailable,
        "outside_cutoff_count": outside_cutoff,
        "eligible_source_row_numbers": eligible,
        "decision_cutoff_utc": cutoff.isoformat().replace("+00:00", "Z"),
        "note": "Eligible records can be reviewed by research replay; ingestion never creates a trade candidate.",
    }


def validate_constituent_membership(
    daily_records: Iterable[Mapping[str, Any]],
    membership_records: Iterable[Mapping[str, Any]],
    *,
    index_symbol: str = "NIFTY 50",
) -> dict[str, Any]:
    """Compare daily symbols with explicitly supplied effective-dated members.

    This checks membership only on dates covered by the supplied constituent
    records. It cannot establish that the reference list is complete or
    official, and it returns INCONCLUSIVE where no dated membership applies.
    """
    daily = list(daily_records)
    members = list(membership_records)
    normalized_index = index_symbol.strip().upper()
    if not daily or not members or not normalized_index:
        return {"status": "INCONCLUSIVE", "checked_count": 0, "uncovered_count": len(daily),
                "invalid_count": 0, "issues": [],
                "reason": "daily_records_membership_records_and_index_identity_are_required"}
    intervals: list[tuple[str, str, str]] = []
    for row in members:
        values = row.get("values", row)
        if not isinstance(values, Mapping):
            return {"status": "INCONCLUSIVE", "checked_count": 0, "uncovered_count": len(daily),
                    "invalid_count": 0, "issues": [], "reason": "malformed_membership_record"}
        index_value = str(values.get("index_symbol") or "").strip().upper()
        symbol = str(values.get("symbol") or "").strip().upper()
        start = values.get("effective_from")
        end = values.get("effective_to")
        if index_value != normalized_index:
            continue
        if not symbol or not isinstance(start, str):
            return {"status": "INCONCLUSIVE", "checked_count": 0, "uncovered_count": len(daily),
                    "invalid_count": 0, "issues": [], "reason": "membership_identity_or_effective_start_missing"}
        try:
            date.fromisoformat(start)
            if end is not None:
                date.fromisoformat(str(end))
                if str(end) < start:
                    raise ValueError("effective_to_before_effective_from")
        except ValueError:
            return {"status": "INCONCLUSIVE", "checked_count": 0, "uncovered_count": len(daily),
                    "invalid_count": 0, "issues": [], "reason": "invalid_membership_effective_dates"}
        intervals.append((symbol, start, str(end) if end is not None else "9999-12-31"))
    issues: list[dict[str, Any]] = []
    checked = uncovered = invalid = 0
    for row in daily:
        values = row.get("values", row)
        trading_date = row.get("trading_date") or (values.get("trading_date") if isinstance(values, Mapping) else None)
        symbol = values.get("symbol") if isinstance(values, Mapping) else None
        if not isinstance(trading_date, str) or not isinstance(symbol, str) or not symbol.strip():
            issues.append({"source_row_number": row.get("source_row_number"), "reason": "daily_symbol_or_date_missing"})
            invalid += 1
            continue
        try:
            date.fromisoformat(trading_date)
        except ValueError:
            issues.append({"source_row_number": row.get("source_row_number"), "reason": "invalid_daily_trading_date"})
            invalid += 1
            continue
        active = {member for member, start, end in intervals if start <= trading_date <= end}
        if not active:
            uncovered += 1
        elif symbol.strip().upper() not in active:
            invalid += 1
            issues.append({"source_row_number": row.get("source_row_number"), "reason": "symbol_not_in_supplied_constituent_membership",
                           "trading_date": trading_date, "symbol": symbol})
        else:
            checked += 1
    status = "FAIL" if invalid else ("INCONCLUSIVE" if uncovered else "PASS")
    return {"status": status, "checked_count": checked, "uncovered_count": uncovered,
            "invalid_count": invalid, "issues": issues,
            "limitations": ["Membership completeness, source provenance, and official index identity are not verified by this comparison."]}


def ingest_file(
    input_path: Path,
    schema: IngestionSchema,
    *,
    source_label: str,
    output_root: Path,
    processing_time: datetime | None = None,
    requested_start: date | None = None,
    requested_end: date | None = None,
    retrieved_at: datetime | None = None,
    output_layout: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Validate and persist one explicitly configured local input file.

    The source file is copied byte-for-byte into a new run's ``raw`` folder;
    it is never modified. Existing run folders are never overwritten.
    """
    issues = schema.validate()
    if issues:
        raise ValueError("invalid schema: " + ", ".join(issues))
    if schema.parser_id not in PARSER_REGISTRY:
        raise ValueError(f"unsupported parser_id {schema.parser_id!r}")
    # Avoid strict realpath resolution here: Windows managed workspaces may
    # deny handle-based final-path queries even when ordinary file reads are
    # permitted. Existence and file type are checked separately below.
    source = input_path.expanduser().absolute()
    if not source.is_file():
        raise ValueError("input path must name one local file")
    label = source_label.strip()
    if not label:
        raise ValueError("source_label is required")
    if len(label) > 160 or any(ord(character) < 32 for character in label):
        raise ValueError("source_label must be at most 160 printable characters")
    if re.search(r"\b(bearer\s+\S+|(?:api[_-]?key|secret|token|password)\s*[:=])", label, re.IGNORECASE):
        raise ValueError("source_label appears to contain credential material; use a non-secret source name")
    processed = processing_time or datetime.now(timezone.utc)
    if processed.tzinfo is None or processed.utcoffset() is None:
        raise ValueError("processing_time must be timezone-aware")
    processed = processed.astimezone(timezone.utc)
    if (requested_start is None) != (requested_end is None):
        raise ValueError("requested_start_and_end_must_be_supplied_together")
    if requested_start is not None and requested_end is not None and requested_start > requested_end:
        raise ValueError("requested_start_must_not_follow_requested_end")
    if retrieved_at is not None:
        if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
            raise ValueError("retrieved_at_must_be_timezone_aware")
        retrieved_at = retrieved_at.astimezone(timezone.utc)
        if retrieved_at > processed:
            raise ValueError("retrieved_at_must_not_follow_processing_time")
    layout = dict(output_layout or {
        "raw": "raw", "normalized": "normalized", "rejected": "rejected",
        "metadata": "metadata", "reports": "reports",
    })
    required_layout = {"raw", "normalized", "rejected", "metadata", "reports"}
    if set(layout) != required_layout or any(
        not isinstance(name, str) or not name or name in {".", ".."}
        or "/" in name or "\\" in name for name in layout.values()
    ) or len(set(layout.values())) != len(required_layout):
        raise ValueError("output_layout_must_use_five_distinct_safe_directory_names")

    output_root = output_root.expanduser().absolute()
    output_root.mkdir(parents=True, exist_ok=True)
    # A deterministic run identity makes exact repeats recognizable; no prior
    # output is overwritten, and users can preserve separate runs explicitly.
    schema_bytes = _safe_json_bytes(schema.canonical_dict())
    schema_hash = hashlib.sha256(schema_bytes).hexdigest()
    input_hash, input_size = _sha256(source)
    run_id = hashlib.sha256(
        (PIPELINE_VERSION + input_hash + schema_hash + label
         + (requested_start.isoformat() if requested_start else "")
         + (requested_end.isoformat() if requested_end else "")
         + (retrieved_at.isoformat() if retrieved_at else "")).encode("utf-8")
    ).hexdigest()[:24]
    run_name = f"{schema.dataset_type.value}-{run_id}"
    final_dir = output_root / run_name
    if final_dir.exists():
        raise FileExistsError(f"ingestion run already exists and was not overwritten: {final_dir}")

    staging = Path(tempfile.mkdtemp(prefix=f".{run_name}-", dir=output_root))
    try:
        for child in layout.values():
            (staging / child).mkdir()
        raw_copy = staging / layout["raw"] / source.name
        shutil.copyfile(source, raw_copy)
        copied_hash, copied_size = _sha256(raw_copy)
        if copied_hash != input_hash or copied_size != input_size:
            raise OSError("source changed while copying; raw-copy hash mismatch")

        parser_error: str | None = None
        try:
            text_handle, close_handles = _iter_text(raw_copy, schema)
            try:
                parsed = PARSER_REGISTRY[schema.parser_id](text_handle, schema)
            finally:
                if isinstance(close_handles, tuple):
                    close_handles[1].close()
                    close_handles[0].close()
                else:
                    close_handles.close()
        except (OSError, UnicodeError, zipfile.BadZipFile, RuntimeError, ValueError) as exc:
            parsed = ParseResult((), (), 0, (), f"input_parse_failure:{type(exc).__name__}:{exc}")
        parser_error = parsed.parser_error
        accepted = [
            {
                **record,
                "source_label": label,
                "source_filename": source.name,
                "source_sha256": input_hash,
                "ingestion_run_id": run_id,
            }
            for record in parsed.accepted
        ]
        rejected = [
            {
                "dataset_type": schema.dataset_type.value,
                "record_type": schema.record_type,
                "schema_version": schema.schema_version,
                "source_row_number": issue.source_row_number,
                "source_sha256": input_hash,
                "ingestion_run_id": run_id,
                "reasons": list(issue.reasons),
                "source_values": dict(issue.source_values),
            }
            for issue in parsed.rejected
        ]
        rejection_counts: dict[str, int] = {}
        for item in rejected:
            for reason in item["reasons"]:
                rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
        normalized_path = staging / layout["normalized"] / f"{schema.dataset_type.value}.jsonl"
        rejected_path = staging / layout["rejected"] / f"{schema.dataset_type.value}.jsonl"
        _write_jsonl(normalized_path, accepted)
        _write_jsonl(rejected_path, rejected)
        processing_iso = processed.isoformat().replace("+00:00", "Z")
        observed_dates = sorted({
            value
            for record in accepted
            for value in (
                record.get("trading_date"),
                record.get("values", {}).get("effective_from"),
                record.get("values", {}).get("effective_to"),
            )
            if value is not None
        })
        observed_symbols = sorted({
            value
            for record in accepted
            for value in (record.get("values", {}).get("symbol"), record.get("values", {}).get("index_symbol"))
            if value is not None
        })
        retrieved_iso = retrieved_at.isoformat().replace("+00:00", "Z") if retrieved_at else None
        technical_status = "FAIL" if parser_error or rejected else ("PASS" if accepted else "INCONCLUSIVE")
        # Without a reviewed source identity, coverage calendar, membership
        # reference, and freshness policy, row parsing alone cannot establish
        # dataset validation. Keep the top-level gate fail-closed.
        validation_status = "FAIL" if technical_status == "FAIL" else "INCONCLUSIVE"
        has_time_fields = all((schema.event_time_field, schema.source_available_time_field, schema.local_receipt_time_field))
        report = {
            "ingestion_run_id": run_id,
            "dataset_type": schema.dataset_type.value,
            "record_type": schema.record_type,
            "format_id": schema.format_id,
            "schema_version": schema.schema_version,
            "pipeline_version": PIPELINE_VERSION,
            "python_version": platform.python_version(),
            "source_label": label,
            "source_filename": source.name,
            "source_sha256": input_hash,
            "retrieved_at_utc": retrieved_iso,
            "requested_date_range": {
                "start": requested_start.isoformat() if requested_start else None,
                "end": requested_end.isoformat() if requested_end else None,
            },
            "observed_date_range": {
                "start": observed_dates[0] if observed_dates else None,
                "end": observed_dates[-1] if observed_dates else None,
                "unique_dates": len(observed_dates),
                "calendar_completeness": "INCONCLUSIVE; no exchange calendar supplied",
            },
            "observed_symbols": observed_symbols,
            "schema_sha256": schema_hash,
            "source_size_bytes": input_size,
            "processing_time_utc": processing_iso,
            "row_count": parsed.row_count,
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "rejection_counts": dict(sorted(rejection_counts.items())),
            "validation_status": validation_status,
            "technical_validation_status": technical_status,
            "freshness_status": "INCONCLUSIVE; no freshness policy supplied",
            "warnings": list(parsed.warnings),
            "parser_error": parser_error,
            "timestamp_fields": {
                "trading_date": schema.trading_date_field,
                "event_time": schema.event_time_field,
                "source_available_time": schema.source_available_time_field,
                "local_receipt_time": schema.local_receipt_time_field,
                "processing_time": "processing_time_utc (this run only; not historical availability)",
            },
            "research_state": "NO_DATA" if not accepted else "INSUFFICIENT_EVIDENCE",
            "decision_state": "NO_TRADE",
            "replay_time_gate_configured": has_time_fields,
            "limitations": [
                "No instrument-master, calendar, licensing, or provider-field semantics are inferred by this pipeline.",
                "File retrieval/processing time is not substituted for market event, source availability, or original local receipt time.",
                "Passing row-level technical checks does not establish research validity or profitability.",
                "Ingestion does not generate hypotheses, recommendations, or execution orders.",
            ],
        }
        manifest = {
            "ingestion_run_id": run_id,
            "created_at_utc": processing_iso,
            "source_label": label,
            "source_filename": source.name,
            "source_size_bytes": input_size,
            "source_sha256": input_hash,
            "retrieved_at_utc": retrieved_iso,
            "requested_date_range": report["requested_date_range"],
            "observed_date_range": report["observed_date_range"],
            "validation_status": validation_status,
            "technical_validation_status": technical_status,
            "freshness_status": "INCONCLUSIVE; no freshness policy supplied",
            "schema_sha256": schema_hash,
            "pipeline_version": PIPELINE_VERSION,
            "source_format": schema.format_id,
            "archive_retrieval_time": None,
            "schema": schema.canonical_dict(),
            "outputs": {
                "raw": f"{layout['raw']}/{source.name}",
                "normalized": f"{layout['normalized']}/{normalized_path.name}",
                "rejected": f"{layout['rejected']}/{rejected_path.name}",
                "report": f"{layout['reports']}/validation-report.json",
                "metadata": f"{layout['metadata']}/manifest.json",
            },
        }
        _write_jsonl(staging / layout["reports"] / "validation-report.json", [report])
        (staging / layout["metadata"] / "manifest.json").write_bytes(_safe_json_bytes(manifest))
        if final_dir.exists():
            raise FileExistsError(f"ingestion run already exists and was not overwritten: {final_dir}")
        os.replace(staging, final_dir)
        return {**report, "output_directory": str(final_dir)}
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def _cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and ingest one explicitly configured local market-data file.")
    parser.add_argument("input_file", type=Path, help="one file relative to configured source-data root; never modified")
    parser.add_argument("--schema", required=True, type=Path, help="explicit JSON schema mapping derived from the provider specification")
    parser.add_argument("--source-label", required=True, help="provenance label supplied by the operator")
    parser.add_argument("--decision-cutoff", help="optional aware ISO timestamp for point-in-time eligibility audit")
    parser.add_argument("--requested-start", type=date.fromisoformat)
    parser.add_argument("--requested-end", type=date.fromisoformat)
    parser.add_argument("--retrieved-at", help="source retrieval time as an aware ISO timestamp; do not use processing time")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _cli_parser().parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    try:
        paths = json.loads((root / "data" / "market" / "ingestion" / "paths.json").read_text(encoding="utf-8"))
        source_root = _contained_project_path(root, paths["source_data_root"])
        output_root = _contained_project_path(root, paths["outputs"]["runs"])
        layout = paths["outputs"].get("layout")
        input_path = _contained_source_path(source_root, args.input_file)
        schema_path = _contained_project_path(root, str(args.schema))
        schema = load_schema(schema_path)
        retrieved_at = datetime.fromisoformat(args.retrieved_at.replace("Z", "+00:00")) if args.retrieved_at else None
        result = ingest_file(input_path, schema, source_label=args.source_label, output_root=output_root,
                             requested_start=args.requested_start, requested_end=args.requested_end,
                             retrieved_at=retrieved_at, output_layout=layout)
        if args.decision_cutoff:
            normalized_dir = (layout or {"normalized": "normalized"})["normalized"]
            report_dir = (layout or {"reports": "reports"})["reports"]
            normalized_path = Path(result["output_directory"]) / normalized_dir / f"{schema.dataset_type.value}.jsonl"
            records = [json.loads(line) for line in normalized_path.read_text(encoding="utf-8").splitlines() if line]
            result["replay_eligibility"] = assess_replay_eligibility(records, args.decision_cutoff)
            (Path(result["output_directory"]) / report_dir / "validation-report.json").write_bytes(_safe_json_bytes(result))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
        return 2 if result.get("parser_error") or result.get("rejected_count") else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"state": "NO_DATA", "decision_state": "NO_TRADE", "error": str(exc)}, ensure_ascii=False))
        return 2


def _contained_project_path(project_root: Path, configured: str) -> Path:
    candidate = Path(configured)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("configured_path_must_be_project_relative")
    base = project_root.resolve()
    target = (base / candidate).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise ValueError("configured_path_escapes_project_root") from exc
    probe = base
    for part in candidate.parts:
        probe = probe / part
        if probe.is_symlink():
            raise ValueError("configured_path_must_not_use_symlink")
    return target


def _contained_source_path(source_root: Path, requested: Path) -> Path:
    if requested.is_absolute() or ".." in requested.parts:
        raise ValueError("input_path_must_stay_under_configured_source_root")
    target = (source_root / requested).resolve()
    try:
        target.relative_to(source_root.resolve())
    except ValueError as exc:
        raise ValueError("input_path_escapes_configured_source_root") from exc
    if not target.is_file():
        raise ValueError("input_path_must_name_file_under_configured_source_root")
    return target


if __name__ == "__main__":
    raise SystemExit(main())
