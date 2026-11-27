"""Tests for features/observations.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from features.observations import (
    apply_qc_flags,
    deduplicate_observations,
    parse_and_write_hourly_observations,
    parse_raw_observation_file,
)


def test_parse_from_fixtures() -> None:
    """Parse real fixture files and verify schema, types, and counts."""
    fixture_dir = Path("tests/fixtures")
    sample_file = str(fixture_dir / "openaq_hours_pm25_sample.json")
    gap_file = str(fixture_dir / "openaq_hours_gap_sample.json")

    records = parse_raw_observation_file(
        sample_file,
        fetch_time_utc="2026-11-16T12:00:00Z",
        station_id=8118,
        sensor_id=1001,
    )

    assert len(records) == 30
    for r in records:
        assert r["station_id"] == 8118
        assert r["sensor_id"] == 1001
        assert r["parameter"] == "pm25"
        assert r["unit"] == "µg/m³"
        assert isinstance(r["period_end_utc"], str)
        assert isinstance(r["period_start_utc"], str)
        assert isinstance(r["value"], (int, float))
        assert r["fetch_time_utc"] == "2026-11-16T12:00:00Z"

    gap_records = parse_raw_observation_file(
        gap_file,
        fetch_time_utc="2026-11-16T12:00:00Z",
        station_id=235,
        sensor_id=2001,
    )
    assert len(gap_records) == 6
    for r in gap_records:
        assert r["station_id"] == 235
        assert r["sensor_id"] == 2001
        assert r["parameter"] == "pm25"


def test_deduplicate_keeps_latest_fetch() -> None:
    """Verify deduplication keeps the latest fetch for identical timestamps."""
    records: list[dict[str, Any]] = [
        {
            "sensor_id": 1,
            "station_id": 10,
            "period_end_utc": "2026-11-01T01:30:00Z",
            "value": 45.0,
            "fetch_time_utc": "2026-11-16T10:00:00Z",
            "source_file": "old.json",
        },
        {
            "sensor_id": 1,
            "station_id": 10,
            "period_end_utc": "2026-11-01T01:30:00Z",
            "value": 45.0,
            "fetch_time_utc": "2026-11-16T14:00:00Z",
            "source_file": "new.json",
        },
    ]

    deduped, disagreements, details = deduplicate_observations(records)
    assert len(deduped) == 1
    assert deduped[0]["fetch_time_utc"] == "2026-11-16T14:00:00Z"
    assert deduped[0]["source_file"] == "new.json"
    assert disagreements == 0
    assert len(details) == 0


def test_deduplicate_detects_and_counts_disagreements() -> None:
    """Verify deduplication detects value disagreements across fetches."""
    records: list[dict[str, Any]] = [
        {
            "sensor_id": 1,
            "station_id": 10,
            "period_end_utc": "2026-11-01T01:30:00Z",
            "value": 45.0,
            "fetch_time_utc": "2026-11-16T10:00:00Z",
            "source_file": "old.json",
        },
        {
            "sensor_id": 1,
            "station_id": 10,
            "period_end_utc": "2026-11-01T01:30:00Z",
            "value": 55.0,
            "fetch_time_utc": "2026-11-16T14:00:00Z",
            "source_file": "new.json",
        },
        {
            "sensor_id": 2,
            "station_id": 10,
            "period_end_utc": "2026-11-01T01:30:00Z",
            "value": 80.0,
            "fetch_time_utc": "2026-11-16T10:00:00Z",
            "source_file": "old2.json",
        },
        {
            "sensor_id": 2,
            "station_id": 10,
            "period_end_utc": "2026-11-01T01:30:00Z",
            "value": 80.0,
            "fetch_time_utc": "2026-11-16T14:00:00Z",
            "source_file": "new2.json",
        },
    ]

    deduped, disagreements, details = deduplicate_observations(records)
    assert len(deduped) == 2
    assert disagreements == 1
    assert len(details) == 1
    assert details[0]["sensor_id"] == 1
    assert details[0]["period_end_utc"] == "2026-11-01T01:30:00Z"


def test_qc_flags_negative_null_and_very_high() -> None:
    """Verify negative, null, and very_high QC flags."""
    records: list[dict[str, Any]] = [
        {
            "sensor_id": 1,
            "station_id": 10,
            "parameter": "pm25",
            "period_end_utc": "2026-11-01T01:30:00Z",
            "value": -2.5,
        },
        {
            "sensor_id": 1,
            "station_id": 10,
            "parameter": "pm25",
            "period_end_utc": "2026-11-01T02:30:00Z",
            "value": None,
        },
        {
            "sensor_id": 1,
            "station_id": 10,
            "parameter": "pm25",
            "period_end_utc": "2026-11-01T03:30:00Z",
            "value": 1500.0,
        },
        {
            "sensor_id": 1,
            "station_id": 10,
            "parameter": "pm25",
            "period_end_utc": "2026-11-01T04:30:00Z",
            "value": 50.0,
        },
    ]

    flagged = apply_qc_flags(records, flatline_hours=6, very_high_threshold=1000.0)
    flag_dict = {r["period_end_utc"]: r["qc_flags"] for r in flagged}

    assert "negative" in flag_dict["2026-11-01T01:30:00Z"]
    assert "null" in flag_dict["2026-11-01T02:30:00Z"]
    assert "very_high" in flag_dict["2026-11-01T03:30:00Z"]
    assert flag_dict["2026-11-01T04:30:00Z"] == ""


def test_qc_flags_flatline_streak_and_sub_streak() -> None:
    """Test flatline with streak = flatline_hours and streak = flatline_hours - 1."""
    # Test exactly flatline_hours (6) consecutive identical values
    records_streak_6: list[dict[str, Any]] = [
        {
            "sensor_id": 1,
            "station_id": 10,
            "parameter": "pm25",
            "period_end_utc": f"2026-11-01T0{i}:30:00Z",
            "value": 75.0,
        }
        for i in range(1, 7)
    ]
    flagged_6 = apply_qc_flags(records_streak_6, flatline_hours=6)
    for r in flagged_6:
        assert "flatline" in r["qc_flags"]

    # Test flatline_hours - 1 (5) consecutive identical values: should NOT flag flatline
    records_streak_5: list[dict[str, Any]] = [
        {
            "sensor_id": 1,
            "station_id": 10,
            "parameter": "pm25",
            "period_end_utc": f"2026-11-01T0{i}:30:00Z",
            "value": 75.0,
        }
        for i in range(1, 6)
    ]
    flagged_5 = apply_qc_flags(records_streak_5, flatline_hours=6)
    for r in flagged_5:
        assert "flatline" not in r["qc_flags"]


def test_qc_flags_flatline_non_consecutive_hours() -> None:
    """Test that non-consecutive hours with the same value are NOT flagged flatline."""
    # 6 identical values, but spaced 2 hours apart (not consecutive hours)
    records: list[dict[str, Any]] = [
        {
            "sensor_id": 1,
            "station_id": 10,
            "parameter": "pm25",
            "period_end_utc": f"2026-11-01T{i:02d}:30:00Z",
            "value": 75.0,
        }
        for i in range(0, 12, 2)  # 00:30, 02:30, 04:30, 06:30, 08:30, 10:30
    ]
    assert len(records) == 6
    flagged = apply_qc_flags(records, flatline_hours=6)
    for r in flagged:
        assert "flatline" not in r["qc_flags"]


def test_parse_and_write_hourly_observations_integration(tmp_path: Path) -> None:
    """Test full integration parsing, deduplicating, QC, and writing CSV."""
    raw_dir = tmp_path / "raw"
    sensor_dir = raw_dir / "101" / "201"
    sensor_dir.mkdir(parents=True)

    sample_payload = {
        "results": [
            {
                "parameter": {"name": "pm25", "units": "µg/m³"},
                "period": {
                    "datetimeFrom": {"utc": "2026-11-01T00:30:00Z"},
                    "datetimeTo": {"utc": "2026-11-01T01:30:00Z"},
                },
                "value": 55.4,
            }
        ]
    }
    raw_file = sensor_dir / "20261116T120000Z_p1.json"
    with open(raw_file, "w", encoding="utf-8") as f:
        json.dump(sample_payload, f)

    manifest_file = raw_dir / "manifest.jsonl"
    with open(manifest_file, "w", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "station_id": 101,
                    "sensor_id": 201,
                    "file_path": str(raw_file),
                    "fetch_time_utc": "2026-11-16T12:00:00Z",
                }
            )
            + "\n"
        )

    out_csv = tmp_path / "hourly.csv"
    qc_cfg = tmp_path / "qc.json"
    with open(qc_cfg, "w", encoding="utf-8") as f:
        json.dump(
            {
                "flatline_hours": 6,
                "very_high_threshold": 1000.0,
                "min_hours_per_day": 18,
            },
            f,
        )

    summary = parse_and_write_hourly_observations(
        raw_dir=str(raw_dir),
        manifest_path=str(manifest_file),
        output_csv=str(out_csv),
        qc_config_path=str(qc_cfg),
    )

    assert summary["raw_records"] == 1
    assert summary["deduped_records"] == 1
    assert summary["disagreements"] == 0
    assert out_csv.exists()
