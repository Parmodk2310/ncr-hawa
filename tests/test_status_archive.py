"""Tests for scripts/status_archive.py with hand-made manifests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from scripts.status_archive import (
    cluster_fetches_into_runs,
    compute_archive_status,
    format_status_report,
    main,
    parse_iso_utc,
)


def test_parse_iso_utc() -> None:
    """Test ISO UTC timestamp parsing with Z and offset."""
    dt1 = parse_iso_utc("2026-11-20T05:00:00Z")
    assert dt1.tzinfo == UTC
    assert dt1.year == 2026
    assert dt1.hour == 5

    dt2 = parse_iso_utc("2026-11-20T05:00:00+00:00")
    assert dt2.tzinfo == UTC
    assert dt2 == dt1


def test_cluster_fetches_into_runs_10_minute_window() -> None:
    """Fetches within 10 minutes cluster into one run; >10 minutes start new run."""
    ts1 = datetime(2026, 11, 20, 5, 0, 0, tzinfo=UTC)
    ts2 = datetime(2026, 11, 20, 5, 3, 0, tzinfo=UTC)
    ts3 = datetime(2026, 11, 20, 5, 9, 0, tzinfo=UTC)
    # 25 minutes later -> separate run
    ts4 = datetime(2026, 11, 20, 5, 34, 0, tzinfo=UTC)
    ts5 = datetime(2026, 11, 20, 5, 36, 0, tzinfo=UTC)

    runs = cluster_fetches_into_runs([ts3, ts1, ts2, ts5, ts4], max_gap_minutes=10.0)
    assert len(runs) == 2
    assert len(runs[0]) == 3
    assert len(runs[1]) == 2
    assert runs[0][0] == ts1
    assert runs[1][0] == ts4


def test_empty_or_nonexistent_manifest(tmp_path: Any) -> None:
    """Non-existent or empty manifest handles gracefully without error."""
    missing_path = str(tmp_path / "does_not_exist.jsonl")
    s1 = compute_archive_status(missing_path)
    assert s1["exists"] is False
    assert s1["total_entries"] == 0
    assert s1["runs_count"] == 0
    assert s1["file_count"] == 0
    assert s1["total_size_mb"] == 0.0
    assert s1["age_hours"] is None

    empty_path = tmp_path / "empty.jsonl"
    empty_path.write_text("", encoding="utf-8")
    s2 = compute_archive_status(str(empty_path))
    assert s2["exists"] is True
    assert s2["total_entries"] == 0
    assert s2["runs_count"] == 0

    report = format_status_report(s2)
    assert "Age of last fetch: N/A" in report
    assert "Total clustered runs: 0" in report


def test_hand_made_manifest_with_gap_flag_and_runs_per_day(tmp_path: Any) -> None:
    """Hand-made manifest verifies runs per day, run intervals, and gap > 7h flag."""
    manifest_file = tmp_path / "manifest.jsonl"

    # Create dummy files for size computation
    f1 = tmp_path / "ecmwf_1.json"
    f2 = tmp_path / "gfs_1.json"
    f3 = tmp_path / "ecmwf_2.json"
    f4 = tmp_path / "ecmwf_3.json"

    # Write 512 KB and 1024 KB files
    f1.write_bytes(b"0" * (512 * 1024))
    f2.write_bytes(b"0" * (512 * 1024))
    f3.write_bytes(b"0" * (1024 * 1024))
    f4.write_bytes(b"0" * (1024 * 1024))

    entries = [
        # Run 1: 2026-11-19 at 00:00:00Z and 00:02:00Z (clustered into 1 run)
        {
            "fetch_time_utc": "2026-11-19T00:00:00Z",
            "source": "weather",
            "area_id": "delhi",
            "model": "ecmwf_ifs025",
            "request_url_has_models": True,
            "file_path": str(f1),
        },
        {
            "fetch_time_utc": "2026-11-19T00:02:00Z",
            "source": "weather",
            "area_id": "delhi",
            "model": "ncep_gfs_seamless",
            "request_url_has_models": True,
            "file_path": str(f2),
        },
        # Run 2: 2026-11-19 at 06:00:00Z (6h after Run 1 -> no gap)
        {
            "fetch_time_utc": "2026-11-19T06:00:00Z",
            "source": "weather",
            "area_id": "delhi",
            "model": "ecmwf_ifs025",
            "request_url_has_models": True,
            "file_path": str(f3),
        },
        # Run 3: 2026-11-19 at 15:00:00Z (9h after Run 2 -> GAP!)
        {
            "fetch_time_utc": "2026-11-19T15:00:00Z",
            "source": "weather",
            "area_id": "delhi",
            "model": "ecmwf_ifs025",
            "request_url_has_models": True,
            "file_path": str(f4),
        },
        # Run 4: 2026-11-20 at 02:00:00Z (11h after Run 3 on next calendar day -> GAP!)
        {
            "fetch_time_utc": "2026-11-20T02:00:00Z",
            "source": "cams",
            "area_id": "delhi",
            "model": "default",
            "request_url_has_models": False,
            "file_path": str(f1),
        },
    ]

    with open(manifest_file, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    # Evaluate with fixed reference time
    ref_now = datetime(2026, 11, 20, 4, 30, 0, tzinfo=UTC)

    status = compute_archive_status(
        manifest_path=str(manifest_file),
        now_utc=ref_now,
        gap_threshold_hours=7.0,
    )

    assert status["total_entries"] == 5
    assert status["runs_count"] == 4
    assert status["file_count"] == 5

    # Runs per day
    assert status["runs_per_day"] == {
        "2026-11-19": 3,
        "2026-11-20": 1,
    }

    # Intervals
    intervals = status["intervals"]
    assert len(intervals) == 3

    # Run 1 -> Run 2: 6.00 hours -> NOT a gap
    assert intervals[0]["hours"] == 6.0
    assert intervals[0]["is_gap"] is False

    # Run 2 -> Run 3: 9.00 hours -> GAP
    assert intervals[1]["hours"] == 9.0
    assert intervals[1]["is_gap"] is True

    # Run 3 -> Run 4: 11.00 hours -> GAP
    assert intervals[2]["hours"] == 11.0
    assert intervals[2]["is_gap"] is True

    # Age of last fetch: 2026-11-20T04:30 - 2026-11-20T02:00 = 2.50 hours
    assert status["age_hours"] == 2.5
    assert status["last_fetch_utc"] == "2026-11-20T02:00:00Z"

    # Total size: 512 + 512 + 1024 + 1024 + 512 KB = 3.5 MB
    assert status["total_size_mb"] == 3.5

    # Check formatted report string
    report = format_status_report(status)
    assert "2026-11-19: 3 run(s)" in report
    assert "2026-11-20: 1 run(s)" in report
    assert "6.00 hours" in report
    assert "9.00 hours [GAP]" in report
    assert "11.00 hours [GAP]" in report
    assert "Age of last fetch: 2.50 hours" in report
    assert "3.50 MB" in report


def test_status_archive_cli_execution(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Any,
) -> None:
    """main() CLI prints full status report to stdout."""
    manifest_file = tmp_path / "manifest.jsonl"
    entry = {
        "fetch_time_utc": "2026-11-20T08:00:00Z",
        "source": "cams",
        "area_id": "delhi",
        "model": "default",
        "request_url_has_models": False,
        "file_path": str(manifest_file),
    }
    manifest_file.write_text(json.dumps(entry) + "\n", encoding="utf-8")

    main(["--manifest", str(manifest_file), "--now", "2026-11-20T10:00:00Z"])
    captured = capsys.readouterr()

    assert "Open-Meteo Forecast Archive Status Report" in captured.out
    assert "Age of last fetch: 2.00 hours" in captured.out
    assert "2026-11-20: 1 run(s)" in captured.out
