"""Unit tests for ingest/analyse_stations.py."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from ingest.analyse_stations import (
    assign_station_to_area,
    clean_field,
    haversine_distance_km,
    main,
    parse_iso_date,
    parse_tri_state,
)

SAMPLE_AREAS: list[dict[str, Any]] = [
    {
        "area_id": "central_delhi",
        "name": "Central Delhi",
        "latitude": 28.61,
        "longitude": 77.21,
    },
    {
        "area_id": "noida",
        "name": "Noida",
        "latitude": 28.54,
        "longitude": 77.39,
    },
]


def test_haversine_distance_known_pairs() -> None:
    """Verify haversine formula against known reference coordinate pairs."""
    # 1. Zero distance for identical points
    d_zero = haversine_distance_km(28.61, 77.21, 28.61, 77.21)
    assert d_zero == pytest.approx(0.0, abs=1e-5)

    # 2. Central Delhi (28.61, 77.21) to Noida (28.54, 77.39) is ~19.2 km
    d_delhi_noida = haversine_distance_km(28.61, 77.21, 28.54, 77.39)
    assert 18.5 <= d_delhi_noida <= 20.0
    assert d_delhi_noida == pytest.approx(19.22, abs=0.1)

    # 3. London (51.5074, -0.1278) to Paris (48.8566, 2.3522) is ~343.5 km
    d_london_paris = haversine_distance_km(51.5074, -0.1278, 48.8566, 2.3522)
    assert 342.0 <= d_london_paris <= 345.0


def test_haversine_symmetry() -> None:
    """Verify haversine distance is symmetric."""
    p1 = (28.61, 77.21)
    p2 = (28.54, 77.39)
    assert haversine_distance_km(p1[0], p1[1], p2[0], p2[1]) == pytest.approx(
        haversine_distance_km(p2[0], p2[1], p1[0], p1[1]), abs=1e-6
    )


def test_assign_station_to_area_missing_or_invalid_coords() -> None:
    """Missing or non-numeric coordinates must return ('unknown', None)."""
    assert assign_station_to_area("", "", SAMPLE_AREAS, 25.0) == ("unknown", None)
    assert assign_station_to_area("invalid", "77.2", SAMPLE_AREAS, 25.0) == (
        "unknown",
        None,
    )
    assert assign_station_to_area(None, 77.2, SAMPLE_AREAS, 25.0) == ("unknown", None)
    assert assign_station_to_area(28.6, None, SAMPLE_AREAS, 25.0) == ("unknown", None)


def test_assign_station_to_area_nearest_and_outside() -> None:
    """Points in radius assign to nearest center; beyond assign to outside."""
    # Near Central Delhi
    area_id, dist = assign_station_to_area(28.615, 77.215, SAMPLE_AREAS, max_km=25.0)
    assert area_id == "central_delhi"
    assert dist is not None and dist < 2.0

    # Near Noida
    area_id_noida, dist_noida = assign_station_to_area(
        28.545, 77.385, SAMPLE_AREAS, max_km=25.0
    )
    assert area_id_noida == "noida"
    assert dist_noida is not None and dist_noida < 2.0

    # Rohtak (~60km away) with max_km=25.0 -> 'outside'
    area_id_far, dist_far = assign_station_to_area(
        28.876, 76.619, SAMPLE_AREAS, max_km=25.0
    )
    assert area_id_far == "outside"
    assert dist_far is not None and dist_far > 50.0

    # Empty areas list
    assert assign_station_to_area(28.6, 77.2, [], 25.0) == ("outside", None)


def test_parse_iso_date() -> None:
    """Test defensive ISO date parsing."""
    assert parse_iso_date("2026-11-18T18:00:00Z") == date(2026, 11, 18)
    assert parse_iso_date("2026-11-18") == date(2026, 11, 18)
    assert parse_iso_date("") is None
    assert parse_iso_date("   ") is None
    assert parse_iso_date("not-a-date") is None
    assert parse_iso_date(None) is None


def test_clean_field_and_parse_tri_state() -> None:
    """Empty or unverified fields must map to 'unknown' without guessing."""
    assert clean_field("") == "unknown"
    assert clean_field("   ") == "unknown"
    assert clean_field(None) == "unknown"
    assert clean_field("CPCB") == "CPCB"

    assert parse_tri_state("True") == "yes"
    assert parse_tri_state("true") == "yes"
    assert parse_tri_state("False") == "no"
    assert parse_tri_state("false") == "no"
    assert parse_tri_state("") == "unknown"
    assert parse_tri_state(None) == "unknown"
    assert parse_tri_state("maybe") == "unknown"


def test_analyse_stations_tiny_hand_made_csv(tmp_path: Path) -> None:
    """Test full analysis flow on a hand-crafted CSV with known edge cases."""
    areas_path = tmp_path / "areas.json"
    areas_path.write_text(
        json.dumps({"areas": SAMPLE_AREAS}),
        encoding="utf-8",
    )

    licences_path = tmp_path / "licences.csv"
    licences_content = (
        "station_id,name,provider,lat,lon,licence_name,commercialUseAllowed,"
        "attributionRequired,redistributionAllowed,source_url,checked_on,"
        "decision,is_monitor,is_mobile,has_pm25,datetime_first,datetime_last\n"
        # 1: Central Delhi, within radius, active, CC BY 4.0
        "1,Station A,CPCB,28.615,77.215,CC BY 4.0,True,True,True,http://a,2026-11-18,"
        ",True,False,True,2020-01-01,2026-11-15T10:00:00Z\n"
        # 2: Noida, within radius, inactive (2024), no licence (empty)
        "2,Station B,AirGradient,28.545,77.385,,,,,http://b,2026-11-18,"
        ",False,False,True,2020-01-01,2024-01-01T00:00:00Z\n"
        # 3: Far away (Rohtak), outside radius (> 25 km), active
        "3,Station C,CPCB,28.876,76.619,,,,,http://c,2026-11-18,"
        ",True,False,True,2020-01-01,2026-11-16T00:00:00Z\n"
        # 4: Missing coords, missing date
        "4,Station D,,,,, ,,,http://d,2026-11-18,"
        ",,,False,,\n"
    )
    licences_path.write_text(licences_content, encoding="utf-8")

    summary_md = tmp_path / "station_summary.md"
    candidates_csv = tmp_path / "candidates.csv"

    exit_code = main(
        [
            "--licences-csv",
            str(licences_path),
            "--areas-json",
            str(areas_path),
            "--max-km",
            "25.0",
            "--summary-md",
            str(summary_md),
            "--candidates-csv",
            str(candidates_csv),
            "--as-of-date",
            "2026-11-18",
        ]
    )
    assert exit_code == 0

    # 1. Verify candidate CSV
    assert candidates_csv.exists()
    with open(candidates_csv, encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    # Exactly 2 candidates within 25 km (Station A and Station B)
    assert len(reader) == 2
    row1, row2 = reader[0], reader[1]

    assert row1["station_id"] == "1"
    assert row1["area_id"] == "central_delhi"
    assert float(row1["distance_km"]) < 2.0
    assert row1["decision"] == ""  # Strictly empty string
    assert row1["licence_name"] == "CC BY 4.0"

    assert row2["station_id"] == "2"
    assert row2["area_id"] == "noida"
    assert float(row2["distance_km"]) < 2.0
    assert row2["decision"] == ""  # Strictly empty string
    assert row2["licence_name"] == "unknown"  # Empty mapped to 'unknown'
    assert row2["commercialUseAllowed"] == "unknown"

    # 2. Verify Summary Markdown
    assert summary_md.exists()
    content = summary_md.read_text(encoding="utf-8")

    assert "Reference UTC Date**: `2026-11-18`" in content
    assert "Total Locations Evaluated**: `4`" in content
    assert "Candidate Locations Kept**: `2` (`stations_candidates.csv`)" in content
    assert "Locations Outside Threshold**: `1`" in content

    # Check area breakdown in markdown
    assert "`central_delhi`" in content
    assert "`noida`" in content
    assert "`outside`" in content
    assert "`unknown`" in content

    # Check provider breakdown
    assert "`CPCB`" in content
    assert "`AirGradient`" in content

    # Check recency counts: Station 1 active within 30 days, Station 3 active
    assert "Active within last 30 days" in content
    assert "**2**" in content


def test_analyse_stations_include_outside_flag(tmp_path: Path) -> None:
    """When --include-outside is passed, outside stations are included in CSV."""
    areas_path = tmp_path / "areas.json"
    areas_path.write_text(
        json.dumps({"areas": SAMPLE_AREAS}),
        encoding="utf-8",
    )

    licences_path = tmp_path / "licences.csv"
    licences_content = (
        "station_id,name,provider,lat,lon,licence_name,commercialUseAllowed,"
        "attributionRequired,redistributionAllowed,source_url,checked_on,"
        "decision,is_monitor,is_mobile,has_pm25,datetime_first,datetime_last\n"
        "1,Station In,CPCB,28.615,77.215,,,,,,2026-11-18,,,,,\n"
        "2,Station Out,CPCB,28.876,76.619,,,,,,2026-11-18,,,,,\n"
    )
    licences_path.write_text(licences_content, encoding="utf-8")

    candidates_csv = tmp_path / "candidates.csv"

    exit_code = main(
        [
            "--licences-csv",
            str(licences_path),
            "--areas-json",
            str(areas_path),
            "--candidates-csv",
            str(candidates_csv),
            "--include-outside",
        ]
    )
    assert exit_code == 0

    with open(candidates_csv, encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    assert len(reader) == 2
    assert reader[0]["area_id"] == "central_delhi"
    assert reader[1]["area_id"] == "outside"
    assert reader[0]["decision"] == ""
    assert reader[1]["decision"] == ""


def test_main_cli_invalid_date(tmp_path: Path) -> None:
    """Invalid date format must return non-zero exit code."""
    exit_code = main(["--as-of-date", "invalid-date"])
    assert exit_code == 1
