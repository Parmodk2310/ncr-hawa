"""Daily target aggregation for PM2.5 in Indian Standard Time (IST).

Day convention:
An IST calendar day (Asia/Kolkata, UTC+05:30) contains the hourly intervals
whose START falls within 00:00 to 23:59 IST.
Because OpenAQ timestamps are time-ending:
- An interval ending at 00:00 IST (18:30 UTC previous day) started at 23:00 IST,
  so it belongs to the previous day.
- An interval ending at 01:00 IST (19:30 UTC previous day) started at 00:00 IST,
  so it belongs to the new day.
"""

from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

TZ_IST = ZoneInfo("Asia/Kolkata")
DEFAULT_MIN_HOURS_PER_DAY = 18


def load_min_hours_config(config_path: str = "configs/qc.json") -> int:
    """Load min_hours_per_day threshold from QC config."""
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
                return int(data.get("min_hours_per_day", DEFAULT_MIN_HOURS_PER_DAY))
        except Exception:
            return DEFAULT_MIN_HOURS_PER_DAY
    return DEFAULT_MIN_HOURS_PER_DAY


def assign_ist_date(
    period_start_utc: str | None,
    period_end_utc: str | None,
) -> str | None:
    """Assign an observation interval to an IST calendar date (YYYY-MM-DD).

    A day contains the hourly intervals whose START falls within 00:00 to 23:59 IST.
    """
    dt_start_utc: datetime | None = None

    if period_start_utc:
        try:
            dt_start_utc = datetime.fromisoformat(
                period_start_utc.replace("Z", "+00:00")
            )
        except ValueError:
            dt_start_utc = None

    if dt_start_utc is None and period_end_utc:
        try:
            dt_end_utc = datetime.fromisoformat(period_end_utc.replace("Z", "+00:00"))
            dt_start_utc = dt_end_utc - timedelta(hours=1)
        except ValueError:
            dt_start_utc = None

    if dt_start_utc is None:
        return None

    dt_start_ist = dt_start_utc.astimezone(TZ_IST)
    return dt_start_ist.strftime("%Y-%m-%d")


def compute_daily_pm25_records(
    hourly_records: list[dict[str, Any]],
    min_hours: int = DEFAULT_MIN_HOURS_PER_DAY,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Compute mean daily PM2.5 per station-day for IST calendar days.

    Excludes flagged negative and null hours.
    Includes (and reports) very_high and flatline hours.
    A day is marked valid if n_hours_valid >= min_hours.
    """
    # Group records by (station_id, date_ist)
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)

    for r in hourly_records:
        param = str(r.get("parameter", "")).lower()
        if param != "pm25":
            continue

        st_id = int(r.get("station_id", 0))
        date_ist = assign_ist_date(
            period_start_utc=r.get("period_start_utc"),
            period_end_utc=r.get("period_end_utc"),
        )
        if not date_ist:
            continue

        grouped[(st_id, date_ist)].append(r)

    daily_rows: list[dict[str, Any]] = []
    reported_flags: dict[str, int] = {
        "flatline_hours_included": 0,
        "very_high_hours_included": 0,
        "negative_hours_excluded": 0,
        "null_hours_excluded": 0,
    }

    # Sort keys by station_id and date_ist
    for st_id, date_ist in sorted(grouped.keys()):
        rows = grouped[(st_id, date_ist)]

        valid_values: list[float] = []

        for row in rows:
            flags = set((row.get("qc_flags") or "").split(";"))
            val_raw = row.get("value")

            # Try to convert value to float
            val: float | None = None
            if val_raw is not None and val_raw != "":
                try:
                    val = float(val_raw)
                except (ValueError, TypeError):
                    val = None

            # Exclude negative and null hours
            if val is None or "null" in flags:
                reported_flags["null_hours_excluded"] += 1
                continue
            if val < 0 or "negative" in flags:
                reported_flags["negative_hours_excluded"] += 1
                continue

            # Report (do not exclude) flatline and very_high
            if "flatline" in flags:
                reported_flags["flatline_hours_included"] += 1
            if "very_high" in flags:
                reported_flags["very_high_hours_included"] += 1

            valid_values.append(val)

        n_hours_valid = len(valid_values)
        is_valid = n_hours_valid >= min_hours
        mean_pm25 = (
            round(sum(valid_values) / n_hours_valid, 2) if n_hours_valid > 0 else None
        )

        daily_rows.append(
            {
                "station_id": st_id,
                "date_ist": date_ist,
                "mean_pm25": mean_pm25,
                "n_hours_valid": n_hours_valid,
                "valid": is_valid,
            }
        )

    summary = {
        "total_days_computed": len(daily_rows),
        "station_days_total": len(daily_rows),
        "valid_days_count": sum(1 for d in daily_rows if d["valid"]),
        "station_days_valid": sum(1 for d in daily_rows if d["valid"]),
        "min_hours_threshold": min_hours,
        "reported_flags": reported_flags,
        **reported_flags,
    }
    return daily_rows, summary


def compute_and_write_daily_pm25(
    input_csv: str = "data/interim/openaq_hourly.csv",
    output_csv: str = "data/interim/daily_pm25.csv",
    qc_config_path: str = "configs/qc.json",
) -> dict[str, Any]:
    """Read openaq_hourly.csv, compute daily IST targets, and write daily_pm25.csv."""
    min_hours = load_min_hours_config(qc_config_path)

    hourly_records: list[dict[str, Any]] = []
    if os.path.exists(input_csv):
        with open(input_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                hourly_records.append(dict(row))

    daily_rows, summary = compute_daily_pm25_records(
        hourly_records=hourly_records,
        min_hours=min_hours,
    )

    parent_dir = os.path.dirname(output_csv)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    fieldnames = [
        "station_id",
        "date_ist",
        "mean_pm25",
        "n_hours_valid",
        "valid",
    ]

    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in daily_rows:
            writer.writerow(
                {
                    "station_id": r["station_id"],
                    "date_ist": r["date_ist"],
                    "mean_pm25": ("" if r["mean_pm25"] is None else r["mean_pm25"]),
                    "n_hours_valid": r["n_hours_valid"],
                    "valid": r["valid"],
                }
            )

    summary["output_csv"] = output_csv
    return summary


def aggregate_and_write_daily_pm25(
    hourly_csv_path: str = "data/interim/openaq_hourly.csv",
    output_csv_path: str = "data/interim/daily_pm25.csv",
    qc_config_path: str = "configs/qc.json",
) -> dict[str, Any]:
    """Alias for compute_and_write_daily_pm25."""
    return compute_and_write_daily_pm25(
        input_csv=hourly_csv_path,
        output_csv=output_csv_path,
        qc_config_path=qc_config_path,
    )


if __name__ == "__main__":
    summary = compute_and_write_daily_pm25()
    print("Daily PM2.5 targets computed:")
    print(f"  Station-days computed: {summary['total_days_computed']}")
    min_h = summary["min_hours_threshold"]
    valid_cnt = summary["valid_days_count"]
    print(f"  Valid station-days (>= {min_h}h): {valid_cnt}")
    print(f"  QC details: {summary['reported_flags']}")
    print(f"  Saved to: {summary['output_csv']}")
