"""Read-only structural audit for nested NSE CM sample archives."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any
CLOCK_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$")
EXPECTED_FIELDS = {"trades": 7, "snapshots": 14}
def _member_bytes(outer: zipfile.ZipFile, keyword: str) -> tuple[str, bytes]:
    matches = [
        name for name in outer.namelist()
        if keyword in name.upper() and name.lower().endswith(".zip")
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one nested ZIP for {keyword}; found {len(matches)}"
        )
    with zipfile.ZipFile(outer.open(matches[0])) as inner:
        files = [
            item for item in inner.infolist()
            if not item.is_dir() and keyword in item.filename.upper()
        ]
        if len(files) != 1:
            raise ValueError(
                f"Expected exactly one {keyword} data member; found {len(files)}"
            )
        return files[0].filename, inner.read(files[0])
def _audit_records(raw: bytes, kind: str) -> dict[str, Any]:
    if kind not in EXPECTED_FIELDS:
        raise ValueError(f"Unsupported record type: {kind}")
    expected = EXPECTED_FIELDS[kind]
    lines = raw.splitlines()
    field_counts: Counter[str] = Counter()
    malformed = invalid_clocks = invalid_numbers = valid_numbers = 0
    symbols: set[str] = set()
    times: list[str] = []
    identifiers: list[str] = []
    for line in lines:
        text = line.decode("utf-8", errors="replace")
        if not text.strip():
            malformed += 1
            continue
        fields = text.split("|")
        field_counts[str(len(fields))] += 1
        if len(fields) != expected:
            malformed += 1
            continue
        if kind == "trades":
            identifier, symbol, clock, price, quantity = (
                fields[1], fields[2], fields[4], fields[5], fields[6]
            )
        else:
            identifier, symbol, clock, price, quantity = (
                fields[0], fields[1], fields[5], fields[4], fields[3]
            )
        identifiers.append(identifier)
        symbols.add(symbol)
        if CLOCK_RE.fullmatch(clock):
            times.append(clock)
        else:
            invalid_clocks += 1
        try:
            price_value, quantity_value = float(price), float(quantity)
            if (
                not math.isfinite(price_value)
                or not math.isfinite(quantity_value)
                or price_value <= 0
                or quantity_value <= 0
            ):
                invalid_numbers += 1
            else:
                valid_numbers += 1
        except (TypeError, ValueError, OverflowError):
            invalid_numbers += 1
    duplicate_count = len(identifiers) - len(set(identifiers))
    numeric_ids = bool(identifiers) and all(x.isdigit() for x in identifiers)
    strictly_increasing = (
        all(int(a) < int(b) for a, b in zip(identifiers, identifiers[1:]))
        if numeric_ids else None
    )
    return {
        "record_type": kind,
        "row_count": len(lines),
        "field_count_distribution": dict(sorted(field_counts.items())),
        "expected_field_count": expected,
        "malformed_row_count": malformed,
        "distinct_symbol_count": len(symbols),
        "time_range_observed": {
            "first": min(times) if times else None,
            "last": max(times) if times else None,
            "valid_clock_rows": len(times),
            "invalid_clock_rows": invalid_clocks,
        },
        "invalid_or_nonpositive_price_quantity_rows": invalid_numbers,
        "rows_with_valid_positive_price_and_quantity": valid_numbers,
        "duplicate_identifier_count": duplicate_count,
        "identifier_strictly_increasing": strictly_increasing,
        "coverage_status": "observed range only; full-session coverage unverified",
    }
def audit_archive(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with zipfile.ZipFile(path) as outer:
        trades_name, trades_raw = _member_bytes(outer, "CM_TRADES")
        snapshot_name, snapshot_raw = _member_bytes(outer, "CM_SNAPSHOT")
    return {
        "audit_version": 1,
        "archive": path.name,
        "archive_sha256": digest,
        "source_archive_modified": False,
        "trade_member": trades_name,
        "snapshot_member": snapshot_name,
        "trades": _audit_records(trades_raw, "trades"),
        "snapshots": _audit_records(snapshot_raw, "snapshots"),
        "unresolved_questions": [
            "Trade rows have seven fields; the reviewed historical specification describes six.",
            "The meaning of the leading trade field is not inferred.",
            "Observed clock ranges do not establish full-session coverage.",
            "Source-availability and local-receipt timestamps are not assessed.",
            "Snapshot rows are order-book records, not executed trade volume.",
        ],
        "profitability_or_predictive_edge_assessed": False,
    }
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only structural audit of nested NSE CM sample ZIPs"
    )
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = audit_archive(args.archive)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
