"""Unit tests for cloud archive health check script (scripts/archive_health.py)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from scripts.archive_health import (
    cluster_fetches_into_runs,
    evaluate_archive_health,
    find_missing_6h_windows,
    load_health_config,
    main,
    parse_manifest_fetches,
)


def make_manifest_line(
    fetch_time_utc: str,
    area_id: str = "central_delhi",
    source: str = "cams",
    model: str = "cams_global",
) -> str:
    """Helper to generate a valid manifest JSON line."""
    return json.dumps(
        {
            "fetch_time_utc": fetch_time_utc,
            "area_id": area_id,
            "source": source,
            "model": model,
            "http_status": 200,
            "sha256": "abcdef1234567890",
            "file_path": f"data/raw/open_meteo/{area_id}/{source}/{model}/sample.json",
        }
    )


def test_load_health_config(tmp_path: Any) -> None:
    """Verify loading custom thresholds and fallback to defaults."""
    # Fallback when non-existent
    non_existent = str(tmp_path / "missing.json")
    cfg = load_health_config(non_existent)
    assert cfg["max_age_hours"] == 14.0
    assert cfg["min_runs_24h"] == 3

    # Custom valid config
    cfg_path = tmp_path / "custom.json"
    cfg_path.write_text(
        json.dumps({"max_age_hours": 10.0, "min_runs_24h": 4}),
        encoding="utf-8",
    )
    loaded = load_health_config(str(cfg_path))
    assert loaded["max_age_hours"] == 10.0
    assert loaded["min_runs_24h"] == 4


def test_parse_manifest_fetches_and_cluster(tmp_path: Any) -> None:
    """Verify timestamp parsing and run clustering within 10-minute windows."""
    manifest = tmp_path / "manifest.jsonl"
    lines = [
        make_manifest_line("2026-11-20T01:17:00Z"),
        make_manifest_line("2026-11-20T01:19:00Z"),  # Same run
        make_manifest_line("2026-11-20T07:17:00Z"),  # Run 2
        make_manifest_line("invalid json line"),
        make_manifest_line("2026-11-20T13:17:00Z"),  # Run 3
    ]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fetches = parse_manifest_fetches(str(manifest))
    assert len(fetches) == 4
    assert fetches[0] == datetime(2026, 11, 20, 1, 17, 0, tzinfo=UTC)

    runs = cluster_fetches_into_runs(fetches, cluster_minutes=10)
    assert len(runs) == 3
    assert len(runs[0]) == 2
    assert len(runs[1]) == 1
    assert len(runs[2]) == 1


def test_find_missing_6h_windows() -> None:
    """Verify detection of missing 6h UTC windows in the last 48 hours."""
    now_utc = datetime(2026, 11, 22, 12, 0, 0, tzinfo=UTC)
    # Provide fetches covering only up to 24h ago
    fetches = [
        datetime(2026, 11, 21, 0, 15, 0, tzinfo=UTC),
        datetime(2026, 11, 21, 6, 15, 0, tzinfo=UTC),
        # Gap between 06:15 and 2026-11-22 00:00 (18h gap)
        datetime(2026, 11, 22, 0, 15, 0, tzinfo=UTC),
        datetime(2026, 11, 22, 6, 15, 0, tzinfo=UTC),
    ]

    missing = find_missing_6h_windows(fetches, now_utc)
    # Missing slots in the 18h gap: 12:00 and 18:00 on 2026-11-21
    assert "2026-11-21T12:00:00Z" in missing
    assert "2026-11-21T18:00:00Z" in missing


def test_healthy_archive(tmp_path: Any) -> None:
    """Recent fetch (<14h) and >=3 runs in 24h evaluates healthy (exit 0)."""
    now_utc = datetime(2026, 11, 22, 20, 0, 0, tzinfo=UTC)
    manifest = tmp_path / "manifest.jsonl"
    lines = [
        make_manifest_line("2026-11-22T02:17:00Z"),
        make_manifest_line("2026-11-22T08:17:00Z"),
        make_manifest_line("2026-11-22T14:17:00Z"),
        make_manifest_line("2026-11-22T19:17:00Z"),  # 43 minutes ago
    ]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")

    exit_code, metrics, report = evaluate_archive_health(
        manifest_path=str(manifest),
        now_utc=now_utc,
    )

    assert exit_code == 0
    assert metrics["status"] == "healthy"
    assert metrics["runs_last_24h"] == 4
    assert metrics["age_hours"] < 1.0
    assert "[HEALTHY]" in report


def test_stale_archive_age_exceeded(tmp_path: Any) -> None:
    """Latest fetch age exceeding threshold evaluates stale (exit 1)."""
    now_utc = datetime(2026, 11, 22, 20, 0, 0, tzinfo=UTC)
    manifest = tmp_path / "manifest.jsonl"
    # Latest fetch is 18 hours ago
    lines = [
        make_manifest_line("2026-11-21T20:17:00Z"),
        make_manifest_line("2026-11-22T02:00:00Z"),  # 18h ago
    ]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")

    exit_code, metrics, report = evaluate_archive_health(
        manifest_path=str(manifest),
        now_utc=now_utc,
    )

    assert exit_code == 1
    assert metrics["status"] == "stale"
    assert metrics["age_hours"] >= 18.0
    assert "[STALE]" in report
    assert any("exceeds max threshold" in f for f in metrics["failures"])


def test_insufficient_runs_in_24h(tmp_path: Any) -> None:
    """Fewer than 3 runs in last 24h evaluates stale (exit 1)."""
    now_utc = datetime(2026, 11, 22, 20, 0, 0, tzinfo=UTC)
    manifest = tmp_path / "manifest.jsonl"
    # Only 1 run in the last 24h (recent, but isolated)
    lines = [
        make_manifest_line("2026-11-22T18:00:00Z"),  # 2h ago
    ]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")

    exit_code, metrics, report = evaluate_archive_health(
        manifest_path=str(manifest),
        now_utc=now_utc,
    )

    assert exit_code == 1
    assert metrics["status"] == "stale"
    assert metrics["runs_last_24h"] == 1
    assert any("below min threshold" in f for f in metrics["failures"])


def test_empty_or_nonexistent_manifest(tmp_path: Any) -> None:
    """Missing or empty manifest file evaluates stale (exit 1)."""
    # Non-existent
    exit_code, metrics, report = evaluate_archive_health(
        manifest_path=str(tmp_path / "does_not_exist.jsonl"),
    )
    assert exit_code == 1
    assert metrics["status"] == "stale"
    assert "Manifest missing or contains no valid fetch records" in report

    # Empty
    empty_file = tmp_path / "empty.jsonl"
    empty_file.write_text("", encoding="utf-8")
    exit_code2, metrics2, report2 = evaluate_archive_health(
        manifest_path=str(empty_file),
    )
    assert exit_code2 == 1
    assert metrics2["status"] == "stale"


def test_main_cli(tmp_path: Any, monkeypatch: Any) -> None:
    """CLI execution returns appropriate exit code."""
    manifest = tmp_path / "manifest.jsonl"
    now_utc = datetime.now(UTC)
    lines = [
        make_manifest_line(
            (now_utc - timedelta(hours=18)).strftime("%Y-%m-%dT%H:%M:%SZ")
        ),
        make_manifest_line(
            (now_utc - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%SZ")
        ),
        make_manifest_line(
            (now_utc - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
        ),
        make_manifest_line(
            (now_utc - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        ),
    ]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Healthy run
    code = main(["--manifest", str(manifest)])
    assert code == 0

    # Nonexistent run -> code 1
    code_err = main(["--manifest", str(tmp_path / "missing.jsonl")])
    assert code_err == 1
