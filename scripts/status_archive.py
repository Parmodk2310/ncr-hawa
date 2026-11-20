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


def load_forecast_configs(
    areas_path: str = "configs/areas.json",
    vars_path: str = "configs/variables.json",
) -> tuple[list[str], list[str]]:
    """Load area IDs and configured weather model names from config JSONs."""
    areas: list[str] = []
    if os.path.exists(areas_path):
        try:
            with open(areas_path, encoding="utf-8") as f:
                data = json.load(f)
                areas = [a["area_id"] for a in data.get("areas", []) if "area_id" in a]
        except (OSError, json.JSONDecodeError):
            pass

    weather_models: list[str] = []
    if os.path.exists(vars_path):
        try:
            with open(vars_path, encoding="utf-8") as f:
                vars_cfg = json.load(f)
                raw_models = vars_cfg.get("weather", {}).get("models", [])
                for item in raw_models:
                    if isinstance(item, dict) and "model" in item:
                        weather_models.append(item["model"])
                    elif isinstance(item, str):
                        weather_models.append(item)
        except (OSError, json.JSONDecodeError):
            pass

    return areas, weather_models


def get_expected_targets(
    areas: list[str],
    weather_models: list[str],
) -> list[tuple[str, str, str]]:
    """Generate list of expected (source, model, area_id) tuples."""
    targets: list[tuple[str, str, str]] = []
    for area in areas:
        targets.append(("cams", "default", area))
    for model in weather_models:
        for area in areas:
            targets.append(("weather", model, area))
    return targets


def format_target_label(source: str, model: str, area_id: str) -> str:
    """Format target as readable label, e.g. cams/area or weather[model]/area."""
    if source == "cams" or model == "default":
        return f"{source}/{area_id}"
    return f"{source}[{model}]/{area_id}"


def entry_matches_target(entry: dict[str, Any], target: tuple[str, str, str]) -> bool:
    """Check if a manifest entry satisfies an expected target tuple."""
    src, mdl, aid = target
    e_src = entry.get("source")
    e_aid = entry.get("area_id")
    e_mdl = entry.get("model", "default")
    if e_src != src or e_aid != aid:
        return False
    if src == "cams":
        return True
    return e_mdl == mdl or (e_mdl == "default" and mdl == "default")


def parse_run_log(log_path: str) -> dict[str, Any]:
    """Parse run log and flag starts without matching exit= before next start or EOF."""
    if not os.path.exists(log_path):
        return {
            "log_path": log_path,
            "exists": False,
            "total_lines": 0,
            "total_starts": 0,
            "unmatched_starts": [],
        }

    lines: list[str] = []
    with open(log_path, encoding="utf-8") as f:
        lines = f.readlines()

    total_starts = 0
    unmatched_starts: list[dict[str, Any]] = []
    current_start: dict[str, Any] | None = None

    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        lower_line = line.lower()
        is_start = "start" in lower_line and "exit=" not in lower_line
        is_exit = "exit=" in lower_line

        if is_start:
            total_starts += 1
            if current_start is not None:
                unmatched_starts.append(
                    {
                        "line_num": current_start["line_num"],
                        "line": current_start["line"],
                        "flag": "START WITHOUT EXIT",
                    }
                )
            current_start = {"line_num": idx, "line": line}
        elif is_exit:
            if current_start is not None:
                current_start = None

    if current_start is not None:
        unmatched_starts.append(
            {
                "line_num": current_start["line_num"],
                "line": current_start["line"],
                "flag": "START WITHOUT EXIT",
            }
        )

    return {
        "log_path": log_path,
        "exists": True,
        "total_lines": len(lines),
        "total_starts": total_starts,
        "unmatched_starts": unmatched_starts,
    }


def compute_archive_status(
    manifest_path: str,
    areas_path: str = "configs/areas.json",
    vars_path: str = "configs/variables.json",
    now_utc: datetime | None = None,
    gap_threshold_hours: float = 7.0,
    run_gap_minutes: float = 10.0,
    log_path: str | None = None,
) -> dict[str, Any]:
    """Compute archive health, completeness, and continuity metrics."""
    current_time = now_utc or datetime.now(UTC)

    areas, weather_models = load_forecast_configs(areas_path, vars_path)
    expected_files_per_run = len(areas) * (1 + len(weather_models)) if areas else 0
    expected_targets = get_expected_targets(areas, weather_models)

    log_status = parse_run_log(log_path) if log_path else None

    if not os.path.exists(manifest_path):
        return {
            "manifest_path": manifest_path,
            "exists": False,
            "total_entries": 0,
            "runs_count": 0,
            "expected_files_per_run": expected_files_per_run,
            "runs": [],
            "runs_per_day": {},
            "intervals": [],
            "age_hours": None,
            "last_fetch_utc": None,
            "file_count": 0,
            "total_size_mb": 0.0,
            "log_status": log_status,
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
            "expected_files_per_run": expected_files_per_run,
            "runs": [],
            "runs_per_day": {},
            "intervals": [],
            "age_hours": None,
            "last_fetch_utc": None,
            "file_count": 0,
            "total_size_mb": 0.0,
            "log_status": log_status,
        }

    valid_entries: list[tuple[datetime, dict[str, Any]]] = []
    file_paths: list[str] = []

    for entry in entries:
        ts_str = entry.get("fetch_time_utc")
        if ts_str:
            try:
                valid_entries.append((parse_iso_utc(ts_str), entry))
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

    # Cluster entries into runs
    valid_entries.sort(key=lambda x: x[0])
    max_gap_seconds = run_gap_minutes * 60.0
    clustered_entry_runs: list[list[dict[str, Any]]] = []
    clustered_ts_runs: list[list[datetime]] = []

    current_entry_run: list[dict[str, Any]] = []
    current_ts_run: list[datetime] = []

    for dt, entry in valid_entries:
        if not current_ts_run:
            current_ts_run.append(dt)
            current_entry_run.append(entry)
        elif (dt - current_ts_run[-1]).total_seconds() <= max_gap_seconds:
            current_ts_run.append(dt)
            current_entry_run.append(entry)
        else:
            clustered_ts_runs.append(current_ts_run)
            clustered_entry_runs.append(current_entry_run)
            current_ts_run = [dt]
            current_entry_run = [entry]

    if current_ts_run:
        clustered_ts_runs.append(current_ts_run)
        clustered_entry_runs.append(current_entry_run)

    runs_info: list[dict[str, Any]] = []
    runs_per_day: dict[str, int] = {}
    run_start_times: list[datetime] = []

    for i, run_entries in enumerate(clustered_entry_runs):
        start_t = clustered_ts_runs[i][0]
        end_t = clustered_ts_runs[i][-1]
        run_start_times.append(start_t)
        day_str = start_t.strftime("%Y-%m-%d")
        runs_per_day[day_str] = runs_per_day.get(day_str, 0) + 1

        missing: list[str] = []
        present: list[str] = []

        for target in expected_targets:
            label = format_target_label(*target)
            if any(entry_matches_target(e, target) for e in run_entries):
                present.append(label)
            else:
                missing.append(label)

        # Flag incomplete if fewer files than expected or missing expected targets
        is_incomplete = bool(missing) or (len(run_entries) < expected_files_per_run)

        runs_info.append(
            {
                "run_index": i + 1,
                "start_utc": start_t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end_utc": end_t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "file_count": len(run_entries),
                "expected_count": expected_files_per_run,
                "is_incomplete": is_incomplete,
                "status": "INCOMPLETE" if is_incomplete else "COMPLETE",
                "missing": missing,
                "present": present,
            }
        )

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
    all_timestamps = [dt for dt, _ in valid_entries]
    if all_timestamps:
        latest_ts = max(all_timestamps)
        last_fetch_utc = latest_ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        age_hours = round((current_time - latest_ts).total_seconds() / 3600.0, 2)

    return {
        "manifest_path": manifest_path,
        "exists": True,
        "total_entries": len(entries),
        "runs_count": len(runs_info),
        "expected_files_per_run": expected_files_per_run,
        "runs": runs_info,
        "runs_per_day": runs_per_day,
        "intervals": intervals,
        "age_hours": age_hours,
        "last_fetch_utc": last_fetch_utc,
        "file_count": len(file_paths),
        "total_size_mb": round(total_size_mb, 2),
        "log_status": log_status,
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
    if status.get("expected_files_per_run"):
        lines.append(f"Expected files per run: {status['expected_files_per_run']}")
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
    lines.append("Clustered runs:")
    if status.get("runs"):
        for run in status["runs"]:
            r_idx = run["run_index"]
            s_utc = run["start_utc"]
            cnt = run["file_count"]
            exp = run["expected_count"]
            if run["is_incomplete"]:
                missing_str = (
                    ", ".join(run["missing"]) if run["missing"] else "unspecified"
                )
                prefix = f"  Run {r_idx} ({s_utc}): {cnt}/{exp} files [INCOMPLETE]"
                lines.append(f"{prefix} (missing: {missing_str})")
            else:
                lines.append(f"  Run {r_idx} ({s_utc}): {cnt}/{exp} files")
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

    if status.get("log_status"):
        log_info = status["log_status"]
        lines.append("")
        lines.append("Run log status:")
        lines.append(f"  Log file: {log_info['log_path']}")
        if not log_info["exists"]:
            lines.append("  File does not exist.")
        elif log_info["total_lines"] == 0:
            lines.append("  File is empty.")
        else:
            lines.append(f"  Total starts: {log_info['total_starts']}")
            if log_info["unmatched_starts"]:
                for item in log_info["unmatched_starts"]:
                    lines.append(
                        f'  Line {item["line_num"]}: "{item["line"]}" [{item["flag"]}]'
                    )
            else:
                lines.append("  All starts have matching exit= (clean).")

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
        "--areas",
        default="configs/areas.json",
        help="Path to areas.json (default: configs/areas.json).",
    )
    parser.add_argument(
        "--vars",
        default="configs/variables.json",
        help="Path to variables.json (default: configs/variables.json).",
    )
    parser.add_argument(
        "--log",
        default=None,
        help="Path to execution run.log to audit for unclosed starts.",
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
        areas_path=args.areas,
        vars_path=args.vars,
        now_utc=now_utc,
        gap_threshold_hours=args.gap_hours,
        log_path=args.log,
    )
    print(format_status_report(status))


if __name__ == "__main__":
    main()
