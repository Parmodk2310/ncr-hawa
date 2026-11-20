"""Archive status report for Open-Meteo forecast manifest."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from typing import Any


def parse_iso_utc(ts_str: str) -> datetime:
    """Parse ISO 8601 UTC timestamp to timezone-aware UTC datetime."""
    clean_str = ts_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(clean_str)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def cluster_fetches_into_runs(
    timestamps: list[datetime],
    max_gap_minutes: float = 10.0,
) -> list[list[datetime]]:
    """Cluster sorted timestamps into runs where fetches are within max_gap_minutes."""
    if not timestamps:
        return []

    sorted_ts = sorted(timestamps)
    runs: list[list[datetime]] = []
    current_run: list[datetime] = [sorted_ts[0]]

    max_gap_seconds = max_gap_minutes * 60.0

    for ts in sorted_ts[1:]:
        if (ts - current_run[-1]).total_seconds() <= max_gap_seconds:
            current_run.append(ts)
        else:
            runs.append(current_run)
            current_run = [ts]

    if current_run:
        runs.append(current_run)

    return runs


def compute_archive_status(
    manifest_path: str,
    now_utc: datetime | None = None,
    gap_threshold_hours: float = 7.0,
    run_gap_minutes: float = 10.0,
) -> dict[str, Any]:
    """Compute archive health and continuity metrics from manifest.jsonl."""
    current_time = now_utc or datetime.now(UTC)

    if not os.path.exists(manifest_path):
        return {
            "manifest_path": manifest_path,
            "exists": False,
            "total_entries": 0,
            "runs_count": 0,
            "runs_per_day": {},
            "intervals": [],
            "age_hours": None,
            "last_fetch_utc": None,
            "file_count": 0,
            "total_size_mb": 0.0,
        }

    entries: list[dict[str, Any]] = []
    with open(manifest_path, encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                entries.append(json.loads(line_str))
            except json.JSONDecodeError:
                continue

    if not entries:
        return {
            "manifest_path": manifest_path,
            "exists": True,
            "total_entries": 0,
            "runs_count": 0,
            "runs_per_day": {},
            "intervals": [],
            "age_hours": None,
            "last_fetch_utc": None,
            "file_count": 0,
            "total_size_mb": 0.0,
        }

    timestamps: list[datetime] = []
    file_paths: list[str] = []

    for entry in entries:
        ts_str = entry.get("fetch_time_utc")
        if ts_str:
            try:
                timestamps.append(parse_iso_utc(ts_str))
            except ValueError:
                pass
        f_path = entry.get("file_path")
        if f_path:
            file_paths.append(f_path)

    total_bytes = 0
    manifest_dir = os.path.dirname(os.path.abspath(manifest_path))
    workspace_dir = os.getcwd()

    for fp in file_paths:
        target = fp
        if not os.path.isabs(target):
            cand1 = os.path.join(workspace_dir, target)
            cand2 = os.path.join(manifest_dir, os.path.basename(target))
            cand3 = os.path.join(
                os.path.dirname(manifest_dir), os.path.basename(target)
            )
            if os.path.exists(cand1):
                target = cand1
            elif os.path.exists(cand2):
                target = cand2
            elif os.path.exists(cand3):
                target = cand3

        if os.path.exists(target):
            try:
                total_bytes += os.path.getsize(target)
            except OSError:
                pass

    total_size_mb = total_bytes / (1024.0 * 1024.0)
    runs = cluster_fetches_into_runs(timestamps, max_gap_minutes=run_gap_minutes)

    runs_per_day: dict[str, int] = {}
    run_start_times: list[datetime] = []

    for run in runs:
        start_t = run[0]
        run_start_times.append(start_t)
        day_str = start_t.strftime("%Y-%m-%d")
        runs_per_day[day_str] = runs_per_day.get(day_str, 0) + 1

    intervals: list[dict[str, Any]] = []
    for i in range(len(run_start_times) - 1):
        t_prev = run_start_times[i]
        t_next = run_start_times[i + 1]
        diff_hours = (t_next - t_prev).total_seconds() / 3600.0
        is_gap = diff_hours > gap_threshold_hours
        intervals.append(
            {
                "run_index_prev": i + 1,
                "run_index_next": i + 2,
                "from_utc": t_prev.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "to_utc": t_next.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "hours": round(diff_hours, 2),
                "is_gap": is_gap,
            }
        )

    last_fetch_utc = None
    age_hours = None
    if timestamps:
        latest_ts = max(timestamps)
        last_fetch_utc = latest_ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        age_hours = round((current_time - latest_ts).total_seconds() / 3600.0, 2)

    return {
        "manifest_path": manifest_path,
        "exists": True,
        "total_entries": len(entries),
        "runs_count": len(runs),
        "runs_per_day": runs_per_day,
        "intervals": intervals,
        "age_hours": age_hours,
        "last_fetch_utc": last_fetch_utc,
        "file_count": len(file_paths),
        "total_size_mb": round(total_size_mb, 2),
    }


def format_status_report(status: dict[str, Any]) -> str:
    """Format status report for readable console output."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("Open-Meteo Forecast Archive Status Report")
    lines.append("=" * 60)
    lines.append(f"Manifest: {status['manifest_path']}")
    lines.append(f"Total manifest entries: {status['total_entries']}")
    lines.append(f"Total clustered runs: {status['runs_count']}")
    lines.append(f"Total files recorded: {status['file_count']}")
    lines.append(f"Total storage size: {status['total_size_mb']:.2f} MB")

    if status["age_hours"] is not None:
        lines.append(
            f"Age of last fetch: {status['age_hours']:.2f} hours "
            f"(last fetch: {status['last_fetch_utc']})"
        )
    else:
        lines.append("Age of last fetch: N/A (no records)")

    lines.append("")
    lines.append("Runs per day (UTC):")
    if status["runs_per_day"]:
        for day, count in sorted(status["runs_per_day"].items()):
            lines.append(f"  {day}: {count} run(s)")
    else:
        lines.append("  None")

    lines.append("")
    lines.append("Intervals between consecutive runs:")
    if status["intervals"]:
        for item in status["intervals"]:
            flag = " [GAP]" if item["is_gap"] else ""
            lines.append(
                f"  Run {item['run_index_prev']} ({item['from_utc']}) -> "
                f"Run {item['run_index_next']} ({item['to_utc']}): "
                f"{item['hours']:.2f} hours{flag}"
            )
    else:
        if status["runs_count"] <= 1:
            lines.append("  Fewer than 2 runs recorded, no intervals to display.")
        else:
            lines.append("  None")

    lines.append("=" * 60)
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print archive status and health metrics from manifest.jsonl."
    )
    parser.add_argument(
        "--manifest",
        default="data/raw/open_meteo/manifest.jsonl",
        help="Path to manifest.jsonl (default: data/raw/open_meteo/manifest.jsonl).",
    )
    parser.add_argument(
        "--now",
        default=None,
        help=(
            "Reference UTC timestamp in ISO 8601 format "
            "(e.g. 2026-11-20T12:00:00Z) for age calculation."
        ),
    )
    parser.add_argument(
        "--gap-hours",
        type=float,
        default=7.0,
        help=(
            "Threshold in hours above which consecutive run gap is flagged "
            "GAP (default: 7.0)."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    now_utc = None
    if args.now:
        now_utc = parse_iso_utc(args.now)

    status = compute_archive_status(
        manifest_path=args.manifest,
        now_utc=now_utc,
        gap_threshold_hours=args.gap_hours,
    )
    print(format_status_report(status))


if __name__ == "__main__":
    main()
