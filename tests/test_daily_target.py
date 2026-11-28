"""Tests for features/daily_target.py."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from features.daily_target import (
    TZ_IST,
    aggregate_and_write_daily_pm25,
    assign_ist_date,
    compute_daily_pm25_records,
)


def test_ist_day_assignment_boundaries() -> None:
    """Test boundary conditions for assigning observation hours to IST calendar days.

    An IST calendar day (Asia/Kolkata, UTC+05:30) contains hourly intervals
    whose START falls within 00:00 to 23:59 IST.

    - Hour ending 18:30 UTC:
      Started at 17:30 UTC. In IST (UTC+05:30), 17:30 UTC is 23:00 IST of the
      same UTC date.
      Therefore, 2026-11-01 18:30 UTC started at 2026-11-01 23:00 IST ->
      IST day 2026-11-01.
      Relative to the following IST day (2026-11-02), hour ending 18:30 UTC
      belongs to the PREVIOUS day.

    - Hour ending 19:30 UTC:
      Started at 18:30 UTC. In IST (UTC+05:30), 18:30 UTC is 00:00 IST of the
      next day (2026-11-02).
      Therefore, 2026-11-01 19:30 UTC belongs to the NEXT IST day (2026-11-02).
    """
    # 2026-11-01 18:30 UTC ended interval [17:30, 18:30] UTC -> [23:00, 00:00] IST
    # Interval start is 2026-11-01 23:00 IST -> belongs to 2026-11-01
    date_1830 = assign_ist_date(
        period_start_utc="2026-11-01T17:30:00Z",
        period_end_utc="2026-11-01T18:30:00Z",
    )
    assert date_1830 == "2026-11-01"

    # 2026-11-01 19:30 UTC ended interval [18:30, 19:30] UTC ->
    # [00:00, 01:00] IST on 2026-11-02
    # Interval start is 2026-11-02 00:00 IST -> belongs to 2026-11-02
    date_1930 = assign_ist_date(
        period_start_utc="2026-11-01T18:30:00Z",
        period_end_utc="2026-11-01T19:30:00Z",
    )
    assert date_1930 == "2026-11-02"

    # Testing start inferred when period_start_utc is None
    date_inferred_prev = assign_ist_date(
        period_start_utc=None,
        period_end_utc="2026-11-01T18:30:00Z",
    )
    assert date_inferred_prev == "2026-11-01"

    date_inferred_curr = assign_ist_date(
        period_start_utc=None,
        period_end_utc="2026-11-01T19:30:00Z",
    )
    assert date_inferred_curr == "2026-11-02"


def test_valid_day_logic_thresholds() -> None:
    """Verify that 17 valid hours is invalid and 18 valid hours is valid."""
    # 17 valid hours for station 10 on 2026-11-02
    records_17: list[dict[str, Any]] = [
        {
            "station_id": 10,
            "parameter": "pm25",
            "period_start_utc": f"2026-11-02T{i:02d}:00:00Z",
            "period_end_utc": f"2026-11-02T{i + 1:02d}:00:00Z",
            "value": 50.0,
            "qc_flags": "",
        }
        for i in range(17)
    ]
    daily_rows_17, _ = compute_daily_pm25_records(records_17, min_hours=18)
    assert len(daily_rows_17) == 1
    assert daily_rows_17[0]["n_hours_valid"] == 17
    assert daily_rows_17[0]["valid"] is False

    # 18 valid hours for station 10 on 2026-11-02
    records_18: list[dict[str, Any]] = [
        {
            "station_id": 10,
            "parameter": "pm25",
            "period_start_utc": f"2026-11-02T{i:02d}:00:00Z",
            "period_end_utc": f"2026-11-02T{i + 1:02d}:00:00Z",
            "value": 50.0,
            "qc_flags": "",
        }
        for i in range(18)
    ]
    daily_rows_18, _ = compute_daily_pm25_records(records_18, min_hours=18)
    assert len(daily_rows_18) == 1
    assert daily_rows_18[0]["n_hours_valid"] == 18
    assert daily_rows_18[0]["valid"] is True


def test_negative_and_null_hours_excluded() -> None:
    """Verify that negative and null hours are excluded from mean and valid count."""
    records: list[dict[str, Any]] = [
        # 10 valid hours of 40.0
        *(
            {
                "station_id": 10,
                "parameter": "pm25",
                "period_start_utc": f"2026-11-02T{i:02d}:00:00Z",
                "period_end_utc": f"2026-11-02T{i + 1:02d}:00:00Z",
                "value": 40.0,
                "qc_flags": "",
            }
            for i in range(10)
        ),
        # 2 negative hours (flagged and raw)
        {
            "station_id": 10,
            "parameter": "pm25",
            "period_start_utc": "2026-11-02T10:00:00Z",
            "period_end_utc": "2026-11-02T11:00:00Z",
            "value": -15.0,
            "qc_flags": "negative",
        },
        # 2 null hours
        {
            "station_id": 10,
            "parameter": "pm25",
            "period_start_utc": "2026-11-02T11:00:00Z",
            "period_end_utc": "2026-11-02T12:00:00Z",
            "value": None,
            "qc_flags": "null",
        },
    ]

    daily_rows, rep = compute_daily_pm25_records(records, min_hours=18)
    assert len(daily_rows) == 1
    # Only the 10 valid hours counted
    assert daily_rows[0]["n_hours_valid"] == 10
    assert daily_rows[0]["mean_pm25"] == 40.0
    assert rep["negative_hours_excluded"] == 1
    assert rep["null_hours_excluded"] == 1


def test_very_high_and_flatline_included() -> None:
    """Verify that very_high and flatline hours are INCLUDED in mean and valid count."""
    records: list[dict[str, Any]] = [
        # 10 normal hours of 50.0
        *(
            {
                "station_id": 10,
                "parameter": "pm25",
                "period_start_utc": f"2026-11-02T{i:02d}:00:00Z",
                "period_end_utc": f"2026-11-02T{i + 1:02d}:00:00Z",
                "value": 50.0,
                "qc_flags": "",
            }
            for i in range(10)
        ),
        # 6 flatline hours of 50.0
        *(
            {
                "station_id": 10,
                "parameter": "pm25",
                "period_start_utc": f"2026-11-02T{i:02d}:00:00Z",
                "period_end_utc": f"2026-11-02T{i + 1:02d}:00:00Z",
                "value": 50.0,
                "qc_flags": "flatline",
            }
            for i in range(10, 16)
        ),
        # 2 very_high hours of 1100.0
        *(
            {
                "station_id": 10,
                "parameter": "pm25",
                "period_start_utc": f"2026-11-02T{i:02d}:00:00Z",
                "period_end_utc": f"2026-11-02T{i + 1:02d}:00:00Z",
                "value": 1100.0,
                "qc_flags": "very_high",
            }
            for i in range(16, 18)
        ),
    ]

    daily_rows, rep = compute_daily_pm25_records(records, min_hours=18)
    assert len(daily_rows) == 1
    # All 18 hours (10 normal + 6 flatline + 2 very_high) must be included
    assert daily_rows[0]["n_hours_valid"] == 18
    assert daily_rows[0]["valid"] is True

    # Mean: (10*50 + 6*50 + 2*1100) / 18 = (500 + 300 + 2200) / 18 = 3000 / 18 = 166.67
    assert daily_rows[0]["mean_pm25"] == 166.67
    assert rep["flatline_hours_included"] == 6
    assert rep["very_high_hours_included"] == 2


def test_aggregate_and_write_daily_pm25_integration(tmp_path: Path) -> None:
    """Test full integration from hourly CSV to daily target CSV."""
    hourly_csv = tmp_path / "hourly.csv"
    with open(hourly_csv, "w", encoding="utf-8") as f:
        f.write(
            "station_id,sensor_id,parameter,unit,period_end_utc,"
            "period_start_utc,value,source_file,fetch_time_utc,qc_flags\n"
        )
        for i in range(18):
            f.write(
                f"101,201,pm25,µg/m³,2026-11-02T{i + 1:02d}:00:00Z,"
                f"2026-11-02T{i:02d}:00:00Z,60.0,dummy.json,fetch,\n"
            )

    daily_csv = tmp_path / "daily.csv"
    qc_cfg = tmp_path / "qc.json"
    with open(qc_cfg, "w", encoding="utf-8") as f:
        f.write('{"min_hours_per_day": 18}\n')

    summary = aggregate_and_write_daily_pm25(
        hourly_csv_path=str(hourly_csv),
        output_csv_path=str(daily_csv),
        qc_config_path=str(qc_cfg),
    )

    assert summary["station_days_total"] == 1
    assert summary["station_days_valid"] == 1
    assert daily_csv.exists()


def test_ist_timezone_offset() -> None:
    """Verify that TZ_IST provides a fixed UTC offset of +05:30."""
    dt = datetime(2026, 11, 1, 12, 0, 0, tzinfo=UTC)
    ist_dt = dt.astimezone(TZ_IST)
    assert ist_dt.utcoffset() == timedelta(hours=5, minutes=30)
