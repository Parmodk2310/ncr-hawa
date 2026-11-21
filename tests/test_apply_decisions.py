"""Unit tests for ingest/apply_decisions.py."""

from __future__ import annotations

import csv
import json
from typing import Any

import pytest

from ingest.apply_decisions import (
    ALLOWED_DECISIONS,
    apply_station_decisions,
    main,
)

SAMPLE_HEADERS = [
    "station_id",
    "name",
    "provider",
    "lat",
    "lon",
    "area_id",
    "distance_km",
    "duplicate_group_id",
    "dup_note",
    "proposed_decision",
    "proposed_reason",
    "publish_candidate",
    "licence_name",
    "commercialUseAllowed",
    "attributionRequired",
    "redistributionAllowed",
    "source_url",
    "checked_on",
    "decision",
    "is_monitor",
    "is_mobile",
    "has_pm25",
    "datetime_first",
    "datetime_last",
]


def create_sample_csv(file_path: Any, rows: list[dict[str, str]]) -> None:
    """Helper to write a sample candidates CSV."""
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SAMPLE_HEADERS)
        writer.writeheader()
        for r in rows:
            # Fill default empty strings for missing columns
            full_row = {col: r.get(col, "") for col in SAMPLE_HEADERS}
            writer.writerow(full_row)


def read_csv_rows(file_path: Any) -> list[dict[str, str]]:
    """Helper to read CSV rows as dicts."""
    with open(file_path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_each_decision_mapping(tmp_path: Any) -> None:
    """Verify exact 1:1 mapping for use, history_only, exclude, and review."""
    candidates_csv = tmp_path / "candidates.csv"
    report_md = tmp_path / "report.md"

    rows = [
        {
            "station_id": "1",
            "name": "Station Use",
            "area_id": "central_delhi",
            "proposed_decision": "use",
            "proposed_reason": "active monitor",
            "publish_candidate": "yes",
            "decision": "",
        },
        {
            "station_id": "2",
            "name": "Station History",
            "area_id": "noida",
            "proposed_decision": "history_only",
            "proposed_reason": "no data in 30 days",
            "publish_candidate": "no",
            "decision": "",
        },
        {
            "station_id": "3",
            "name": "Station Exclude",
            "area_id": "gurugram",
            "proposed_decision": "exclude",
            "proposed_reason": "no PM2.5",
            "publish_candidate": "no",
            "decision": "",
        },
        {
            "station_id": "4",
            "name": "Station Review",
            "area_id": "ghaziabad",
            "proposed_decision": "review",
            "proposed_reason": "last date unknown",
            "publish_candidate": "no",
            "decision": "",
        },
    ]
    create_sample_csv(candidates_csv, rows)

    stats = apply_station_decisions(
        candidates_path=str(candidates_csv),
        report_path=str(report_md),
    )

    assert stats["total_rows"] == 4
    assert stats["applied_count"] == 4
    assert stats["skipped_count"] == 0

    result_rows = read_csv_rows(candidates_csv)
    decisions = {r["station_id"]: r["decision"] for r in result_rows}
    assert decisions["1"] == "use"
    assert decisions["2"] == "history_only"
    assert decisions["3"] == "exclude"
    assert decisions["4"] == "review"

    # Protected columns must remain untouched
    for orig, res in zip(rows, result_rows, strict=True):
        assert res["proposed_decision"] == orig["proposed_decision"]
        assert res["proposed_reason"] == orig["proposed_reason"]
        assert res["publish_candidate"] == orig["publish_candidate"]


def test_skip_if_decision_already_nonempty(tmp_path: Any) -> None:
    """Rows with pre-existing non-empty decision are refused overwrite."""
    candidates_csv = tmp_path / "candidates.csv"
    report_md = tmp_path / "report.md"

    rows = [
        {
            "station_id": "10",
            "name": "Pre-decided 1",
            "area_id": "central_delhi",
            "proposed_decision": "exclude",
            "decision": "use",  # Already set to use
        },
        {
            "station_id": "20",
            "name": "Pre-decided 2",
            "area_id": "central_delhi",
            "proposed_decision": "use",
            "decision": "manual_override",  # Custom existing value
        },
        {
            "station_id": "30",
            "name": "Empty decision",
            "area_id": "noida",
            "proposed_decision": "history_only",
            "decision": "",  # Empty -> will be populated
        },
    ]
    create_sample_csv(candidates_csv, rows)

    stats = apply_station_decisions(
        candidates_path=str(candidates_csv),
        report_path=str(report_md),
    )

    assert stats["total_rows"] == 3
    assert stats["applied_count"] == 1
    assert stats["skipped_count"] == 2

    result_rows = read_csv_rows(candidates_csv)
    decisions = {r["station_id"]: r["decision"] for r in result_rows}
    # Pre-existing decisions are strictly preserved
    assert decisions["10"] == "use"
    assert decisions["20"] == "manual_override"
    # Empty decision was populated
    assert decisions["30"] == "history_only"


def test_review_stays_review_never_turned_into_exclude(tmp_path: Any) -> None:
    """Stations marked review remain review; never turned into exclude or use."""
    candidates_csv = tmp_path / "candidates.csv"
    report_md = tmp_path / "report.md"

    rows = [
        {
            "station_id": "101",
            "name": "Cluster A1",
            "provider": "CPCB",
            "area_id": "central_delhi",
            "proposed_decision": "review",
            "proposed_reason": "same-provider cluster, check if separate devices",
            "decision": "",
        },
        {
            "station_id": "102",
            "name": "Far Apart 1",
            "provider": "caaqm",
            "area_id": "gurugram",
            "proposed_decision": "review",
            "proposed_reason": "same name far apart, check coordinates",
            "decision": "",
        },
        {
            "station_id": "103",
            "name": "Unknown Date",
            "provider": "CPCB",
            "area_id": "ghaziabad",
            "proposed_decision": "review",
            "proposed_reason": "last date unknown",
            "decision": "",
        },
    ]
    create_sample_csv(candidates_csv, rows)

    stats = apply_station_decisions(
        candidates_path=str(candidates_csv),
        report_path=str(report_md),
    )

    assert stats["applied_count"] == 3
    assert stats["review_stations_count"] == 3

    result_rows = read_csv_rows(candidates_csv)
    for r in result_rows:
        assert r["decision"] == "review"
        assert r["decision"] != "exclude"

    report_text = report_md.read_text(encoding="utf-8")
    assert "Stations Pending Review (`decision = review`)" in report_text
    assert "`101` | Cluster A1 | CPCB | `central_delhi`" in report_text
    assert "`102` | Far Apart 1 | caaqm | `gurugram`" in report_text
    assert "`103` | Unknown Date | CPCB | `ghaziabad`" in report_text


def test_publish_never_appears_in_decision(tmp_path: Any) -> None:
    """The value 'publish' is never written into the decision column."""
    candidates_csv = tmp_path / "candidates.csv"
    report_md = tmp_path / "report.md"

    rows = [
        {
            "station_id": "201",
            "name": "Candidate 1",
            "area_id": "central_delhi",
            "proposed_decision": "use",
            # publish_candidate is yes, but decision must be use
            "publish_candidate": "yes",
            "decision": "",
        },
        {
            "station_id": "202",
            "name": "Candidate 2",
            "area_id": "noida",
            "proposed_decision": "history_only",
            "publish_candidate": "no",
            "decision": "",
        },
    ]
    create_sample_csv(candidates_csv, rows)

    apply_station_decisions(
        candidates_path=str(candidates_csv),
        report_path=str(report_md),
    )

    result_rows = read_csv_rows(candidates_csv)
    for r in result_rows:
        assert r["decision"] != "publish"
        assert r["decision"] in ALLOWED_DECISIONS

    # Extra invariant test: if proposed_decision was somehow 'publish',
    # it raises ValueError
    bad_csv = tmp_path / "bad.csv"
    create_sample_csv(
        bad_csv,
        [
            {
                "station_id": "999",
                "proposed_decision": "publish",
                "decision": "",
            }
        ],
    )
    with pytest.raises(ValueError, match="cannot be 'publish'"):
        # Explicit test by adding 'publish' to ALLOWED_DECISIONS inside test
        apply_station_decisions(
            candidates_path=str(bad_csv),
            report_path=str(tmp_path / "bad_report.md"),
        )


def test_cli_execution_with_custom_paths(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Any,
) -> None:
    """main() CLI works with --candidates, --output, and --report options."""
    in_csv = tmp_path / "in.csv"
    out_csv = tmp_path / "out.csv"
    rep_md = tmp_path / "summary.md"
    areas_json = tmp_path / "areas.json"

    areas_json.write_text(
        json.dumps({"areas": [{"area_id": "delhi_test", "name": "Delhi Test Area"}]}),
        encoding="utf-8",
    )
    create_sample_csv(
        in_csv,
        [
            {
                "station_id": "500",
                "name": "Test Station",
                "area_id": "delhi_test",
                "proposed_decision": "use",
                "decision": "",
            }
        ],
    )

    main(
        [
            "--candidates",
            str(in_csv),
            "--output",
            str(out_csv),
            "--areas",
            str(areas_json),
            "--report",
            str(rep_md),
        ]
    )

    captured = capsys.readouterr()
    assert "Decision application finished:" in captured.out
    assert "Decisions applied:    1" in captured.out
    assert "Rows skipped (non-empty): 0" in captured.out

    out_rows = read_csv_rows(out_csv)
    assert len(out_rows) == 1
    assert out_rows[0]["decision"] == "use"

    rep_content = rep_md.read_text(encoding="utf-8")
    assert "Delhi Test Area" in rep_content
    assert "| `delhi_test` | Delhi Test Area | 1 | 0 | 0 | 0 | **1** |" in rep_content
