"""Cloud archive health check for Open-Meteo forecast manifest.

Evaluates archive freshness and run frequency:
- Age in hours of the latest fetch
- Number of distinct runs (fetches clustered within 10 minutes) in the last 24 hours
- Missing 6-hour UTC windows (00, 06, 12, 18) in the last 48 hours
- Exit code 1 if age > max_age_hours or runs_24h < min_runs_24h.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

DEFAULT_CONFIG_PATH = "configs/archive_health.json"
DEFAULT_MANIFEST_PATH = "data/raw/open_meteo/manifest.jsonl"
DEFAULT_MAX_AGE_HOURS = 14.0
DEFAULT_MIN_RUNS_24H = 3


def load_health_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load health thresholds from JSON config or return defaults."""
    defaults = {
        "max_age_hours": DEFAULT_MAX_AGE_HOURS,
        "min_runs_24h": DEFAULT_MIN_RUNS_24H,
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
                return {**defaults, **data}
        except Exception:
            return defaults
    return defaults


def parse_manifest_fetches(manifest_path: str) -> list[datetime]:
    """Parse and return sorted list of unique fetch timestamps from manifest."""
    if not os.path.exists(manifest_path):
        return []

    fetch_times: set[datetime] = set()
    with open(manifest_path, encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                entry = json.loads(line_str)
                ts_str = entry.get("fetch_time_utc")
                if ts_str:
                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=UTC)
                    else:
                        dt = dt.astimezone(UTC)
                    fetch_times.add(dt)
            except Exception:
                continue

    return sorted(fetch_times)


def cluster_fetches_into_runs(
    fetch_times: list[datetime],
    cluster_minutes: int = 10,
) -> list[list[datetime]]:
    """Cluster timestamps within cluster_minutes into discrete runs."""
    if not fetch_times:
        return []

    runs: list[list[datetime]] = []
    current_run: list[datetime] = [fetch_times[0]]

    for dt in fetch_times[1:]:
        if (dt - current_run[-1]).total_seconds() <= cluster_minutes * 60:
            current_run.append(dt)
        else:
            runs.append(current_run)
            current_run = [dt]

    if current_run:
        runs.append(current_run)

    return runs


def find_missing_6h_windows(
    fetch_times: list[datetime],
    now_utc: datetime,
) -> list[str]:
    """Find missing 6-hour UTC windows (00, 06, 12, 18) in the last 48 hours."""
    start_bound = now_utc - timedelta(hours=48)

    # Align start_bound back to the nearest 6-hour UTC boundary (00, 06, 12, 18)
    hour_slot = (start_bound.hour // 6) * 6
    curr_slot = datetime(
        start_bound.year,
        start_bound.month,
        start_bound.day,
        hour_slot,
        0,
        0,
        tzinfo=UTC,
    )

    missing: list[str] = []

    while curr_slot < now_utc:
        slot_end = curr_slot + timedelta(hours=6)
        # Check if any fetch falls in [curr_slot, slot_end)
        has_fetch = any(curr_slot <= ft < slot_end for ft in fetch_times)
        if not has_fetch:
            missing.append(curr_slot.strftime("%Y-%m-%dT%H:%M:%SZ"))
        curr_slot = slot_end

    return missing


def evaluate_archive_health(
    manifest_path: str = DEFAULT_MANIFEST_PATH,
    config_path: str = DEFAULT_CONFIG_PATH,
    now_utc: datetime | None = None,
) -> tuple[int, dict[str, Any], str]:
    """Evaluate archive health against configured freshness and frequency thresholds.

    Returns (exit_code, metrics_dict, human_readable_report).
    """
    if now_utc is None:
        now_utc = datetime.now(UTC)

    config = load_health_config(config_path)
    max_age_hours = float(config.get("max_age_hours", DEFAULT_MAX_AGE_HOURS))
    min_runs_24h = int(config.get("min_runs_24h", DEFAULT_MIN_RUNS_24H))

    fetch_times = parse_manifest_fetches(manifest_path)

    if not fetch_times:
        report = (
            "================ ARCHIVE HEALTH REPORT ================\n"
            f"Manifest: {manifest_path}\n"
            "Status: [STALE] (Manifest missing or contains no valid fetch records)\n"
            "========================================================"
        )
        metrics = {
            "last_fetch_utc": None,
            "age_hours": None,
            "runs_last_24h": 0,
            "missing_windows_48h": [],
            "status": "stale",
            "failures": ["Manifest is empty or missing"],
        }
        return 1, metrics, report

    latest_fetch = fetch_times[-1]
    age_hours = round((now_utc - latest_fetch).total_seconds() / 3600.0, 2)

    # 24-hour window
    cutoff_24h = now_utc - timedelta(hours=24)
    fetches_24h = [ft for ft in fetch_times if ft >= cutoff_24h]
    runs_24h = len(cluster_fetches_into_runs(fetches_24h, cluster_minutes=10))

    # 48-hour missing windows
    missing_windows = find_missing_6h_windows(fetch_times, now_utc)

    # Evaluation
    failures: list[str] = []
    if age_hours > max_age_hours:
        failures.append(
            f"Last fetch age ({age_hours}h) exceeds max threshold ({max_age_hours}h)"
        )
    if runs_24h < min_runs_24h:
        failures.append(
            f"Distinct runs in last 24h ({runs_24h}) is below min threshold "
            f"({min_runs_24h})"
        )

    is_healthy = len(failures) == 0
    status_label = "HEALTHY" if is_healthy else "STALE"
    exit_code = 0 if is_healthy else 1

    lines = [
        "================ ARCHIVE HEALTH REPORT ================",
        f"Manifest Path: {manifest_path}",
        f"Evaluation Time (UTC): {now_utc.strftime('%Y-%m-%d %H:%M:%SZ')}",
        f"Last Fetch Time (UTC): {latest_fetch.strftime('%Y-%m-%d %H:%M:%SZ')}",
        f"Age of Last Fetch: {age_hours} hours (max allowed: {max_age_hours}h)",
        f"Distinct Runs in Last 24h: {runs_24h} (min required: {min_runs_24h})",
        f"Missing 6h UTC Windows (Last 48h): {len(missing_windows)}",
    ]

    if missing_windows:
        lines.append("Missing Windows:")
        for w in missing_windows:
            lines.append(f"  - {w}")

    lines.append(f"Overall Status: [{status_label}]")
    if failures:
        lines.append("Failure Details:")
        for f in failures:
            lines.append(f"  * {f}")
    lines.append("========================================================")

    report_text = "\n".join(lines)
    metrics = {
        "last_fetch_utc": latest_fetch.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "age_hours": age_hours,
        "runs_last_24h": runs_24h,
        "missing_windows_48h": missing_windows,
        "status": status_label.lower(),
        "failures": failures,
    }

    return exit_code, metrics, report_text


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for archive health check."""
    parser = argparse.ArgumentParser(
        description="Verify freshness and run frequency of Open-Meteo forecast archive."
    )
    parser.add_argument(
        "--manifest",
        default=DEFAULT_MANIFEST_PATH,
        help=f"Path to manifest.jsonl (default: {DEFAULT_MANIFEST_PATH})",
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to archive health config JSON (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--now",
        default=None,
        help="Custom ISO UTC timestamp for evaluation reference time (testing)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional file path to write health report to",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI execution entrypoint."""
    args = parse_args(argv)
    now_dt = None
    if args.now:
        now_dt = datetime.fromisoformat(args.now.replace("Z", "+00:00"))
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=UTC)
        else:
            now_dt = now_dt.astimezone(UTC)

    exit_code, _metrics, report = evaluate_archive_health(
        manifest_path=args.manifest,
        config_path=args.config,
        now_utc=now_dt,
    )

    print(report)

    if args.output:
        parent = os.path.dirname(args.output)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report + "\n")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
