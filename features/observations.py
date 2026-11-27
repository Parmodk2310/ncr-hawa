"""Hourly observation parsing, deduplication, and quality control (QC).

Hour convention:
OpenAQ timestamps follow an exclusive time-ending convention:
an hour stamped 03:00 covers 02:00 to 02:59 (i.e. period_start_utc is 02:00
and period_end_utc is 03:00).
In the real OpenAQ v3 response payload:
- period_start_utc is read from `results[].period.datetimeFrom.utc`
- period_end_utc is read from `results[].period.datetimeTo.utc`
- value is read from `results[].value`
- parameter name is read from `results[].parameter.name`
- unit is read from `results[].parameter.units`
"""

from __future__ import annotations

import csv
import glob
import json
import os
from datetime import datetime, timedelta
from typing import Any

DEFAULT_QC_CONFIG = {
    "flatline_hours": 6,
    "very_high_threshold": 1000.0,
    "min_hours_per_day": 18,
}


def load_qc_config(config_path: str = "configs/qc.json") -> dict[str, Any]:
    """Load QC thresholds from JSON config file or return defaults."""
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_QC_CONFIG, **data}
        except Exception:
            return DEFAULT_QC_CONFIG.copy()
    return DEFAULT_QC_CONFIG.copy()


def parse_raw_observation_file(
    file_path: str,
    fetch_time_utc: str | None = None,
    station_id: int | None = None,
    sensor_id: int | None = None,
) -> list[dict[str, Any]]:
    """Parse a single raw OpenAQ v3 JSON file into raw observation dicts."""
    normalized_path = file_path.replace("\\", "/")
    parts = normalized_path.split("/")

    # Infer station_id and sensor_id from path if not provided
    # Standard path: data/raw/openaq/<station_id>/<sensor_id>/<filename>.json
    if station_id is None or sensor_id is None or fetch_time_utc is None:
        try:
            if len(parts) >= 3:
                filename = parts[-1]
                inferred_sensor = int(parts[-2])
                inferred_station = int(parts[-3])
                if station_id is None:
                    station_id = inferred_station
                if sensor_id is None:
                    sensor_id = inferred_sensor
                if fetch_time_utc is None:
                    # filename: YYYYMMDDTHHMMSSZ_p1.json
                    raw_ts = filename.split("_")[0]
                    if len(raw_ts) >= 16 and "T" in raw_ts and raw_ts.endswith("Z"):
                        fetch_time_utc = (
                            f"{raw_ts[:4]}-{raw_ts[4:6]}-{raw_ts[6:11]}:"
                            f"{raw_ts[11:13]}:{raw_ts[13:]}"
                        )
                    else:
                        fetch_time_utc = "unknown"
        except (ValueError, IndexError):
            pass

    if station_id is None:
        station_id = 0
    if sensor_id is None:
        sensor_id = 0
    if fetch_time_utc is None:
        fetch_time_utc = "unknown"

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    results = data.get("results", [])
    records: list[dict[str, Any]] = []

    for item in results:
        param_obj = item.get("parameter") or {}
        parameter = param_obj.get("name", "unknown")
        unit = param_obj.get("units", "µg/m³")

        period = item.get("period") or {}
        dt_to = period.get("datetimeTo") or {}
        dt_from = period.get("datetimeFrom") or {}

        period_end_utc = dt_to.get("utc")
        period_start_utc = dt_from.get("utc")
        val = item.get("value")

        records.append(
            {
                "station_id": station_id,
                "sensor_id": sensor_id,
                "parameter": parameter,
                "unit": unit,
                "period_end_utc": period_end_utc,
                "period_start_utc": period_start_utc,
                "value": val,
                "source_file": normalized_path,
                "fetch_time_utc": fetch_time_utc,
            }
        )

    return records


def deduplicate_observations(
    raw_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int, list[dict[str, Any]]]:
    """Deduplicate records by (sensor_id, period_end_utc).

    Keeps the record with the latest fetch_time_utc.
    Counts and records all cases where two fetches disagreed on the value.
    Returns (deduped_records, disagreement_count, disagreement_details).
    """
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for r in raw_records:
        key = (r["sensor_id"], r["period_end_utc"])
        grouped.setdefault(key, []).append(r)

    deduped: list[dict[str, Any]] = []
    disagreements = 0
    disagreement_details: list[dict[str, Any]] = []

    for key, group in grouped.items():
        # Check if any values disagree
        first_val = group[0]["value"]
        has_disagreement = False
        for other in group[1:]:
            val = other["value"]
            if val != first_val:
                has_disagreement = True
                break

        if has_disagreement:
            disagreements += 1
            disagreement_details.append(
                {
                    "sensor_id": key[0],
                    "period_end_utc": key[1],
                    "conflicting_records": [
                        {
                            "fetch_time_utc": rec["fetch_time_utc"],
                            "value": rec["value"],
                            "source_file": rec["source_file"],
                        }
                        for rec in group
                    ],
                }
            )

        # Keep record from the latest fetch
        # Sort by fetch_time_utc ascending; last element is latest
        latest_record = max(group, key=lambda x: str(x.get("fetch_time_utc", "")))
        deduped.append(latest_record)

    return deduped, disagreements, disagreement_details


def apply_qc_flags(
    records: list[dict[str, Any]],
    flatline_hours: int = 6,
    very_high_threshold: float = 1000.0,
) -> list[dict[str, Any]]:
    """Apply QC flags to deduplicated observation records without deleting any.

    QC flags:
    - null: value is None
    - negative: value is not None and value < 0
    - very_high: value is not None and value > very_high_threshold
    - flatline: identical value across flatline_hours or more consecutive hours
    """
    # Group by sensor_id to evaluate temporal streaks
    by_sensor: dict[int, list[dict[str, Any]]] = {}
    for r in records:
        by_sensor.setdefault(r["sensor_id"], []).append(r)

    flagged_records: list[dict[str, Any]] = []

    for _sensor_id, sensor_rows in by_sensor.items():
        # Sort chronologically by period_end_utc
        sensor_rows.sort(key=lambda x: str(x.get("period_end_utc", "")))

        # Find flatline streaks
        # Consecutive hours: (dt_curr - dt_prev) == 1 hour and
        # v_curr == v_prev (not None)
        flatline_indices: set[int] = set()
        current_streak: list[int] = []

        for i, row in enumerate(sensor_rows):
            val = row.get("value")
            t_str = row.get("period_end_utc")

            if val is None or not t_str:
                if len(current_streak) >= flatline_hours:
                    flatline_indices.update(current_streak)
                current_streak = []
                continue

            try:
                dt_curr = datetime.fromisoformat(t_str.replace("Z", "+00:00"))
            except ValueError:
                if len(current_streak) >= flatline_hours:
                    flatline_indices.update(current_streak)
                current_streak = []
                continue

            if not current_streak:
                current_streak = [i]
            else:
                prev_i = current_streak[-1]
                prev_val = sensor_rows[prev_i].get("value")
                prev_t_str = sensor_rows[prev_i].get("period_end_utc", "")
                try:
                    dt_prev = datetime.fromisoformat(prev_t_str.replace("Z", "+00:00"))
                except ValueError:
                    dt_prev = None

                is_consecutive = dt_prev is not None and (
                    dt_curr - dt_prev
                ) == timedelta(hours=1)

                if is_consecutive and val == prev_val:
                    current_streak.append(i)
                else:
                    if len(current_streak) >= flatline_hours:
                        flatline_indices.update(current_streak)
                    current_streak = [i]

        if len(current_streak) >= flatline_hours:
            flatline_indices.update(current_streak)

        # Assign flags to each row
        for i, row in enumerate(sensor_rows):
            flags: list[str] = []
            val = row.get("value")

            if val is None:
                flags.append("null")
            else:
                if val < 0:
                    flags.append("negative")
                if val > very_high_threshold:
                    flags.append("very_high")
                if i in flatline_indices:
                    flags.append("flatline")

            row_copy = row.copy()
            row_copy["qc_flags"] = ";".join(sorted(flags))
            flagged_records.append(row_copy)

    # Sort output chronologically by station_id, parameter, period_end_utc
    flagged_records.sort(
        key=lambda x: (
            x.get("station_id", 0),
            str(x.get("parameter", "")),
            str(x.get("period_end_utc", "")),
        )
    )
    return flagged_records


def parse_and_write_hourly_observations(
    raw_dir: str = "data/raw/openaq",
    manifest_path: str | None = None,
    output_csv: str = "data/interim/openaq_hourly.csv",
    qc_config_path: str = "configs/qc.json",
) -> dict[str, Any]:
    """Parse all raw observation files, apply deduplication and QC, and write CSV."""
    if manifest_path is None:
        manifest_path = os.path.join(raw_dir, "manifest.jsonl")

    qc_config = load_qc_config(qc_config_path)
    flatline_hours = qc_config.get("flatline_hours", 6)
    very_high_threshold = qc_config.get("very_high_threshold", 1000.0)

    raw_records: list[dict[str, Any]] = []

    # Read using manifest if available
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    entry = json.loads(line_str)
                except json.JSONDecodeError:
                    continue
                fpath = entry.get("file_path", "")
                if fpath and os.path.exists(fpath):
                    records = parse_raw_observation_file(
                        file_path=fpath,
                        fetch_time_utc=entry.get("fetch_time_utc"),
                        station_id=entry.get("station_id"),
                        sensor_id=entry.get("sensor_id"),
                    )
                    raw_records.extend(records)
    else:
        # Fallback to scanning raw_dir
        pattern = os.path.join(raw_dir, "*", "*", "*.json")
        for fpath in glob.glob(pattern):
            records = parse_raw_observation_file(file_path=fpath)
            raw_records.extend(records)

    # Deduplicate
    deduped, disagreement_count, disagreement_details = deduplicate_observations(
        raw_records
    )

    # Apply QC flags
    flagged = apply_qc_flags(
        records=deduped,
        flatline_hours=flatline_hours,
        very_high_threshold=very_high_threshold,
    )

    # Write output CSV
    parent_dir = os.path.dirname(output_csv)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    fieldnames = [
        "station_id",
        "sensor_id",
        "parameter",
        "unit",
        "period_end_utc",
        "period_start_utc",
        "value",
        "source_file",
        "fetch_time_utc",
        "qc_flags",
    ]

    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in flagged:
            writer.writerow(
                {
                    "station_id": r.get("station_id"),
                    "sensor_id": r.get("sensor_id"),
                    "parameter": r.get("parameter"),
                    "unit": r.get("unit"),
                    "period_end_utc": r.get("period_end_utc"),
                    "period_start_utc": r.get("period_start_utc"),
                    "value": ("" if r.get("value") is None else r.get("value")),
                    "source_file": r.get("source_file"),
                    "fetch_time_utc": r.get("fetch_time_utc"),
                    "qc_flags": r.get("qc_flags", ""),
                }
            )

    qc_counts: dict[str, int] = {
        "negative": 0,
        "null": 0,
        "very_high": 0,
        "flatline": 0,
    }
    for r in flagged:
        flags = (r.get("qc_flags") or "").split(";")
        for flg in flags:
            if flg in qc_counts:
                qc_counts[flg] += 1

    summary = {
        "raw_records": len(raw_records),
        "total_raw_records": len(raw_records),
        "deduped_records": len(deduped),
        "disagreements": disagreement_count,
        "disagreement_count": disagreement_count,
        "disagreement_details": disagreement_details,
        "qc_counts": qc_counts,
        "output_csv": output_csv,
    }
    return summary


if __name__ == "__main__":
    summary = parse_and_write_hourly_observations()
    print("Hourly observations processed:")
    print(f"  Raw records parsed: {summary['total_raw_records']}")
    print(f"  Deduplicated records: {summary['deduped_records']}")
    print(f"  Disagreements across fetches: {summary['disagreement_count']}")
    print(f"  QC flag counts: {summary['qc_counts']}")
    print(f"  Saved to: {summary['output_csv']}")
