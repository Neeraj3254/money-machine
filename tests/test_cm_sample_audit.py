"""Synthetic-only tests for the CM structural audit."""
import json
import zipfile
from research.market.cm_sample_audit import _audit_records, audit_archive
def test_trade_schema_and_numeric_validation():
    raw = (
        b"N|1|TEST|EQ|09:07:18|100.50|2\n"
        b"N|2|TEST|EQ|09:07:19|0|2\n"
        b"N|3|TEST|EQ|bad-time|101|1\n"
    )
    report = _audit_records(raw, "trades")
    assert report["row_count"] == 3
    assert report["field_count_distribution"] == {"7": 3}
    assert report["malformed_row_count"] == 0
    assert report["invalid_or_nonpositive_price_quantity_rows"] == 1
    assert report["time_range_observed"]["invalid_clock_rows"] == 1
def test_snapshot_trailing_empty_field_is_preserved():
    raw = b"123|TEST|EQ|5|100.5|09:21:50|S|ynnn|nnn|nnn|RL|0|0|\n"
    report = _audit_records(raw, "snapshots")
    assert report["field_count_distribution"] == {"14": 1}
    assert report["malformed_row_count"] == 0
def test_nonmonotonic_snapshot_ids_are_diagnostics_not_corruption():
    raw = (
        b"200|TEST|EQ|5|100|09:21:50|S|ynnn|nnn|nnn|RL|0|0|\n"
        b"100|TEST|EQ|5|101|09:21:51|S|ynnn|nnn|nnn|RL|0|0|\n"
    )
    report = _audit_records(raw, "snapshots")
    assert report["identifier_strictly_increasing"] is False
    assert report["malformed_row_count"] == 0
def test_wrong_field_count_is_reported():
    report = _audit_records(b"N|1|TEST|EQ|09:07:18|100\n", "trades")
    assert report["malformed_row_count"] == 1
def test_archive_audit_is_deterministic_and_read_only(tmp_path):
    archive = tmp_path / "sample.zip"
    trades_inner = tmp_path / "trades.zip"
    snapshot_inner = tmp_path / "snapshot.zip"
    with zipfile.ZipFile(trades_inner, "w") as inner:
        inner.writestr(
            "CM_TRADES/sample.txt",
            "N|1|TEST|EQ|09:07:18|100|2\n",
        )
    with zipfile.ZipFile(snapshot_inner, "w") as inner:
        inner.writestr(
            "CM_SNAPSHOT/sample.txt",
            "123|TEST|EQ|5|100|09:21:50|S|ynnn|nnn|nnn|RL|0|0|\n",
        )
    with zipfile.ZipFile(archive, "w") as outer:
        outer.writestr("CM_TRADES_nested.zip", trades_inner.read_bytes())
        outer.writestr("CM_SNAPSHOT_nested.zip", snapshot_inner.read_bytes())
    before = archive.read_bytes()
    first = audit_archive(archive)
    second = audit_archive(archive)
    assert first == second
    assert archive.read_bytes() == before
    assert first["source_archive_modified"] is False
    assert first["profitability_or_predictive_edge_assessed"] is False
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
