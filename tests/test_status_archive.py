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


def test_hand_made_manifest_complete_run(tmp_path: Any) -> None:
    """Clustered run with all expected forecast targets is flagged COMPLETE."""
    areas_cfg = tmp_path / "areas.json"
    vars_cfg = tmp_path / "vars.json"
    manifest_file = tmp_path / "manifest.jsonl"

    areas_cfg.write_text(
        json.dumps(
            {
                "areas": [
                    {"area_id": "area_a"},
                    {"area_id": "area_b"},
                ]
            }
        ),
        encoding="utf-8",
    )
    vars_cfg.write_text(
        json.dumps(
            {
                "weather": {
                    "models": [
                        {"model": "ecmwf_ifs025"},
                        {"model": "ncep_gfs_seamless"},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    # 2 areas * (1 cams + 2 weather) = 6 expected files per run
    entries = [
        {
            "fetch_time_utc": "2026-11-20T01:17:00Z",
            "source": "cams",
            "area_id": "area_a",
            "model": "default",
        },
        {
            "fetch_time_utc": "2026-11-20T01:17:01Z",
            "source": "cams",
            "area_id": "area_b",
            "model": "default",
        },
        {
            "fetch_time_utc": "2026-11-20T01:17:02Z",
            "source": "weather",
            "area_id": "area_a",
            "model": "ecmwf_ifs025",
        },
        {
            "fetch_time_utc": "2026-11-20T01:17:03Z",
            "source": "weather",
            "area_id": "area_b",
            "model": "ecmwf_ifs025",
        },
        {
            "fetch_time_utc": "2026-11-20T01:17:04Z",
            "source": "weather",
            "area_id": "area_a",
            "model": "ncep_gfs_seamless",
        },
        {
            "fetch_time_utc": "2026-11-20T01:17:05Z",
            "source": "weather",
            "area_id": "area_b",
            "model": "ncep_gfs_seamless",
        },
    ]
    with open(manifest_file, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    status = compute_archive_status(
        manifest_path=str(manifest_file),
        areas_path=str(areas_cfg),
        vars_path=str(vars_cfg),
        now_utc=datetime(2026, 11, 20, 2, 0, 0, tzinfo=UTC),
    )

    assert status["runs_count"] == 1
    assert status["expected_files_per_run"] == 6
    run1 = status["runs"][0]
    assert run1["file_count"] == 6
    assert run1["is_incomplete"] is False
    assert run1["status"] == "COMPLETE"
    assert run1["missing"] == []

    report = format_status_report(status)
    assert "Expected files per run: 6" in report
    assert "Run 1 (2026-11-20T01:17:00Z -> 2026-11-20T01:17:05Z): 6/6 files" in report
    assert "[INCOMPLETE]" not in report


def test_hand_made_manifest_incomplete_run(tmp_path: Any) -> None:
    """Clustered run missing targets is flagged INCOMPLETE with details."""
    areas_cfg = tmp_path / "areas.json"
    vars_cfg = tmp_path / "vars.json"
    manifest_file = tmp_path / "manifest.jsonl"

    areas_cfg.write_text(
        json.dumps(
            {
                "areas": [
                    {"area_id": "delhi"},
                    {"area_id": "noida"},
                ]
            }
        ),
        encoding="utf-8",
    )
    vars_cfg.write_text(
        json.dumps(
            {
                "weather": {
                    "models": [
                        {"model": "ecmwf_ifs025"},
                        {"model": "ncep_gfs_seamless"},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    # 6 expected, but only 4 provided:
    # missing cams/noida and weather[ncep_gfs_seamless]/delhi
    entries = [
        {
            "fetch_time_utc": "2026-11-20T01:17:00Z",
            "source": "cams",
            "area_id": "delhi",
            "model": "default",
        },
        {
            "fetch_time_utc": "2026-11-20T01:17:02Z",
            "source": "weather",
            "area_id": "delhi",
            "model": "ecmwf_ifs025",
        },
        {
            "fetch_time_utc": "2026-11-20T01:17:03Z",
            "source": "weather",
            "area_id": "noida",
            "model": "ecmwf_ifs025",
        },
        {
            "fetch_time_utc": "2026-11-20T01:17:05Z",
            "source": "weather",
            "area_id": "noida",
            "model": "ncep_gfs_seamless",
        },
    ]
    with open(manifest_file, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    status = compute_archive_status(
        manifest_path=str(manifest_file),
        areas_path=str(areas_cfg),
        vars_path=str(vars_cfg),
        now_utc=datetime(2026, 11, 20, 2, 0, 0, tzinfo=UTC),
    )

    assert status["runs_count"] == 1
    run1 = status["runs"][0]
    assert run1["file_count"] == 4
    assert run1["expected_count"] == 6
    assert run1["is_incomplete"] is True
    assert run1["status"] == "INCOMPLETE"
    assert "cams/noida" in run1["missing"]
    assert "weather[ncep_gfs_seamless]/delhi" in run1["missing"]

    report = format_status_report(status)
    assert "[INCOMPLETE]" in report
    assert "cams/noida" in report
    assert "weather[ncep_gfs_seamless]/delhi" in report


def test_hand_made_log_start_without_exit(tmp_path: Any) -> None:
    """Flag start lines lacking matching exit= as START WITHOUT EXIT."""
    manifest_file = tmp_path / "manifest.jsonl"
    manifest_file.write_text("", encoding="utf-8")
    log_file = tmp_path / "run.log"

    log_content = (
        "2026-11-20T01:17:00Z start archive run\n"
        "2026-11-20T01:17:15Z exit=0\n"
        "2026-11-20T07:17:00Z start archive run\n"  # Missing exit before next start!
        "2026-11-20T13:17:00Z start archive run\n"
        "2026-11-20T13:17:15Z exit=0\n"
        "2026-11-20T19:17:00Z start archive run\n"  # Missing exit before EOF!
    )
    log_file.write_text(log_content, encoding="utf-8")

    status = compute_archive_status(
        manifest_path=str(manifest_file),
        log_path=str(log_file),
    )

    log_info = status["log_status"]
    assert log_info is not None
    assert log_info["exists"] is True
    assert log_info["total_starts"] == 4
    assert len(log_info["unmatched_starts"]) == 2

    # Line 3 and Line 6 flagged
    flagged_lines = [item["line_num"] for item in log_info["unmatched_starts"]]
    assert flagged_lines == [3, 6]
    for item in log_info["unmatched_starts"]:
        assert item["flag"] == "START WITHOUT EXIT"

    report = format_status_report(status)
    assert (
        'Line 3: "2026-11-20T07:17:00Z start archive run" [START WITHOUT EXIT]'
        in report
    )
    assert (
        'Line 6: "2026-11-20T19:17:00Z start archive run" [START WITHOUT EXIT]'
        in report
    )


def test_hand_made_log_empty(tmp_path: Any) -> None:
    """Empty run log parses cleanly with 0 starts and no flags."""
    manifest_file = tmp_path / "manifest.jsonl"
    manifest_file.write_text("", encoding="utf-8")
    log_file = tmp_path / "run.log"
    log_file.write_text("", encoding="utf-8")

    status = compute_archive_status(
        manifest_path=str(manifest_file),
        log_path=str(log_file),
    )

    log_info = status["log_status"]
    assert log_info is not None
    assert log_info["exists"] is True
    assert log_info["total_lines"] == 0
    assert log_info["total_starts"] == 0
    assert log_info["unmatched_starts"] == []

    report = format_status_report(status)
    assert "File is empty." in report
    assert "[START WITHOUT EXIT]" not in report


def test_legacy_layout_run_labeled_not_incomplete(tmp_path: Any) -> None:
    """Clustered run without model field is labeled [LEGACY LAYOUT], not INCOMPLETE."""
    areas_cfg = tmp_path / "areas.json"
    vars_cfg = tmp_path / "vars.json"
    manifest_file = tmp_path / "manifest.jsonl"

    areas_cfg.write_text(
        json.dumps(
            {
                "areas": [
                    {"area_id": "area_1"},
                    {"area_id": "area_2"},
                ]
            }
        ),
        encoding="utf-8",
    )
    vars_cfg.write_text(
        json.dumps(
            {
                "weather": {
                    "models": [
                        {"model": "ecmwf_ifs025"},
                        {"model": "ncep_gfs_seamless"},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    # Legacy entries omit 'model' field; expect 2 areas * 2 = 4 files
    entries = [
        {
            "fetch_time_utc": "2026-11-19T00:00:00Z",
            "source": "cams",
            "area_id": "area_1",
        },
        {
            "fetch_time_utc": "2026-11-19T00:00:01Z",
            "source": "cams",
            "area_id": "area_2",
        },
        {
            "fetch_time_utc": "2026-11-19T00:00:02Z",
            "source": "weather",
            "area_id": "area_1",
        },
        {
            "fetch_time_utc": "2026-11-19T00:00:03Z",
            "source": "weather",
            "area_id": "area_2",
        },
    ]
    with open(manifest_file, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    status = compute_archive_status(
        manifest_path=str(manifest_file),
        areas_path=str(areas_cfg),
        vars_path=str(vars_cfg),
    )

    assert status["runs_count"] == 1
    run1 = status["runs"][0]
    assert run1["is_legacy"] is True
    assert run1["is_incomplete"] is False
    assert run1["expected_count"] == 4
    assert run1["file_count"] == 4
    assert run1["status"] == "LEGACY"

    report = format_status_report(status)
    assert "[LEGACY LAYOUT]" in report
    assert "[INCOMPLETE]" not in report
    assert "2026-11-19T00:00:00Z -> 2026-11-19T00:00:03Z" in report


def test_files_ge_expected_incomplete_only_when_target_missing(
    tmp_path: Any,
) -> None:
    """When file_count >= expected, flag INCOMPLETE only if named target is missing."""
    areas_cfg = tmp_path / "areas.json"
    vars_cfg = tmp_path / "vars.json"
    manifest_file = tmp_path / "manifest.jsonl"

    areas_cfg.write_text(
        json.dumps({"areas": [{"area_id": "delhi"}]}),
        encoding="utf-8",
    )
    vars_cfg.write_text(
        json.dumps({"weather": {"models": [{"model": "ecmwf_ifs025"}]}}),
        encoding="utf-8",
    )
    # Expected: 1 area * (1 cams + 1 weather) = 2 files

    # Case: 2 files, but both are cams/delhi; weather[ecmwf_ifs025]/delhi is missing
    entries = [
        {
            "fetch_time_utc": "2026-11-20T00:00:00Z",
            "source": "cams",
            "area_id": "delhi",
            "model": "default",
        },
        {
            "fetch_time_utc": "2026-11-20T00:00:01Z",
            "source": "cams",
            "area_id": "delhi",
            "model": "default",
        },
    ]
    with open(manifest_file, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    status = compute_archive_status(
        manifest_path=str(manifest_file),
        areas_path=str(areas_cfg),
        vars_path=str(vars_cfg),
    )

    run = status["runs"][0]
    assert run["file_count"] == 2
    assert run["expected_count"] == 2
    assert run["is_incomplete"] is True
    assert run["missing"] == ["weather[ecmwf_ifs025]/delhi"]

    report = format_status_report(status)
    assert "[INCOMPLETE]" in report
    assert "missing: weather[ecmwf_ifs025]/delhi" in report
    assert "cams/delhi" not in report.split("missing:")[1]


def test_since_option_filters_older_entries(tmp_path: Any) -> None:
    """--since <YYYY-MM-DD> ignores older entries."""
    manifest_file = tmp_path / "manifest.jsonl"

    entries = [
        {
            "fetch_time_utc": "2026-11-18T23:55:00Z",
            "source": "cams",
            "area_id": "delhi",
            "model": "default",
        },
        {
            "fetch_time_utc": "2026-11-19T01:17:00Z",
            "source": "cams",
            "area_id": "delhi",
            "model": "default",
        },
        {
            "fetch_time_utc": "2026-11-20T01:17:00Z",
            "source": "cams",
            "area_id": "delhi",
            "model": "default",
        },
    ]
    with open(manifest_file, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    # Without since: 3 entries, 3 runs
    s_all = compute_archive_status(str(manifest_file))
    assert s_all["total_entries"] == 3
    assert s_all["runs_count"] == 3

    # With since="2026-11-19": ignores 2026-11-18 entry
    s_since = compute_archive_status(str(manifest_file), since="2026-11-19")
    assert s_since["total_entries"] == 2
    assert s_since["runs_count"] == 2
    assert "2026-11-18" not in s_since["runs_per_day"]
    assert "2026-11-19" in s_since["runs_per_day"]
    assert "2026-11-20" in s_since["runs_per_day"]


def test_merge_two_manifests_deduplication_and_missing_6h_windows(
    tmp_path: Any,
) -> None:
    """--merge combines manifests, deduplicates, and flags 6h windows."""
    man1 = tmp_path / "manifest_laptop.jsonl"
    man2 = tmp_path / "manifest_actions.jsonl"

    # Reference evaluation time: 2026-11-20 20:00 UTC
    ref_now = datetime(2026, 11, 20, 20, 0, 0, tzinfo=UTC)

    # Window 00 (00-06 UTC): Laptop at 01:17, Actions also at 01:17 (duplicate)
    # Window 06 (06-12 UTC): Laptop has data at 07:17
    # Window 12 (12-18 UTC): NO DATA in either manifest!
    # Window 18 (18-24 UTC): Actions has data at 19:17
    entries_laptop = [
        {
            "fetch_time_utc": "2026-11-20T01:17:00Z",
            "source": "cams",
            "area_id": "delhi",
            "model": "default",
        },
        {
            "fetch_time_utc": "2026-11-20T07:17:00Z",
            "source": "cams",
            "area_id": "delhi",
            "model": "default",
        },
    ]
    entries_actions = [
        {
            "fetch_time_utc": "2026-11-20T01:17:00Z",
            "source": "cams",
            "area_id": "delhi",
            "model": "default",
        },
        {
            "fetch_time_utc": "2026-11-20T19:17:00Z",
            "source": "cams",
            "area_id": "delhi",
            "model": "default",
        },
    ]

    with open(man1, "w", encoding="utf-8") as f:
        for e in entries_laptop:
            f.write(json.dumps(e) + "\n")
    with open(man2, "w", encoding="utf-8") as f:
        for e in entries_actions:
            f.write(json.dumps(e) + "\n")

    status = compute_archive_status(
        manifest_path=str(man1),
        merge_manifest_path=str(man2),
        since="2026-11-20",
        now_utc=ref_now,
    )

    m_info = status["merge_info"]
    assert m_info is not None
    assert m_info["primary_entries"] == 2
    assert m_info["merge_entries"] == 2
    # 2 + 2 - 1 duplicate = 3 unique entries
    assert m_info["deduped_entries"] == 3

    # Check missing windows: only Window 12 (12:00 to 18:00) is missing
    missing_windows = m_info["missing_windows"]
    assert len(missing_windows) == 1
    assert missing_windows[0]["hour"] == 12
    assert missing_windows[0]["date"] == "2026-11-20"

    report = format_status_report(status)
    assert "Merged manifests view:" in report
    assert "De-duplicated total entries: 3" in report
    assert "2026-11-20 12:00 UTC (12:00 - 18:00) [NO DATA]" in report
    assert "00:00" not in report.split("Missing 6-hour UTC windows")[1]
