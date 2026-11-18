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
    detect_duplicates,
    haversine_distance_km,
    main,
    normalise_station_name,
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


def test_normalise_station_name() -> None:
    """Verify name normalisation: lowercase and collapsed whitespace."""
    assert (
        normalise_station_name("  R   K   Puram,   Delhi - DPCC  ")
        == "r k puram, delhi - dpcc"
    )
    assert normalise_station_name("DELHI TECH UNIV") == "delhi tech univ"
    assert normalise_station_name("") == ""
    assert normalise_station_name(None) == ""


def test_haversine_distance_known_pairs() -> None:
    """Verify haversine formula against known reference coordinate pairs."""
    d_zero = haversine_distance_km(28.61, 77.21, 28.61, 77.21)
    assert d_zero == pytest.approx(0.0, abs=1e-5)

    d_delhi_noida = haversine_distance_km(28.61, 77.21, 28.54, 77.39)
    assert 18.5 <= d_delhi_noida <= 20.0
    assert d_delhi_noida == pytest.approx(19.22, abs=0.1)

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
    area_id, dist = assign_station_to_area(28.615, 77.215, SAMPLE_AREAS, max_km=25.0)
    assert area_id == "central_delhi"
    assert dist is not None and dist < 2.0

    area_id_noida, dist_noida = assign_station_to_area(
        28.545, 77.385, SAMPLE_AREAS, max_km=25.0
    )
    assert area_id_noida == "noida"
    assert dist_noida is not None and dist_noida < 2.0

    area_id_far, dist_far = assign_station_to_area(
        28.876, 76.619, SAMPLE_AREAS, max_km=25.0
    )
    assert area_id_far == "outside"
    assert dist_far is not None and dist_far > 50.0

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


def test_duplicates_exact_duplicates() -> None:
    """Exact duplicates (same name, distance 0m) must form a duplicate group."""
    stations = [
        {"station_id": "1", "name": "R K Puram", "lat": "28.563", "lon": "77.186"},
        {"station_id": "2", "name": "r k puram", "lat": "28.563", "lon": "77.186"},
    ]
    dup_map, dup_groups, far_apart = detect_duplicates(stations, dup_m=500.0)
    assert len(dup_groups) == 1
    assert dup_groups[0]["group_id"] == "DUP-01"
    assert len(dup_groups[0]["stations"]) == 2
    assert dup_map["1"]["group_id"] == "DUP-01"
    assert dup_map["2"]["group_id"] == "DUP-01"
    assert "likely duplicate" in dup_map["1"]["dup_note"]
    assert len(far_apart) == 0


def test_duplicates_same_name_7km_apart() -> None:
    """Same name stations 7 km apart must be listed as 'same name, far apart'."""
    stations = [
        {
            "station_id": "5763",
            "name": "Narela, Delhi - DPCC",
            "lat": "28.8446874",
            "lon": "77.0332666",
        },
        {
            "station_id": "10485",
            "name": "Narela, Delhi - DPCC",
            "lat": "28.822836",
            "lon": "77.101981",
        },
    ]
    dup_map, dup_groups, far_apart = detect_duplicates(stations, dup_m=500.0)
    assert len(dup_groups) == 0
    assert dup_map["5763"]["group_id"] == ""
    assert dup_map["10485"]["group_id"] == ""
    assert "same name, far apart" in dup_map["5763"]["dup_note"]
    assert "same name, far apart" in dup_map["10485"]["dup_note"]
    assert len(far_apart) == 2


def test_duplicates_different_names_at_same_spot() -> None:
    """Different names at the exact same location must NOT be treated as duplicates."""
    stations = [
        {"station_id": "1", "name": "Station Alpha", "lat": "28.61", "lon": "77.21"},
        {"station_id": "2", "name": "Station Beta", "lat": "28.61", "lon": "77.21"},
    ]
    dup_map, dup_groups, far_apart = detect_duplicates(stations, dup_m=500.0)
    assert len(dup_groups) == 0
    assert dup_map["1"]["group_id"] == ""
    assert dup_map["1"]["dup_note"] == ""
    assert dup_map["2"]["group_id"] == ""
    assert dup_map["2"]["dup_note"] == ""
    assert len(far_apart) == 0


def test_duplicates_missing_coordinates() -> None:
    """Stations with same name but missing coordinates must not be duplicates."""
    stations = [
        {"station_id": "1", "name": "Station A", "lat": "", "lon": ""},
        {"station_id": "2", "name": "Station A", "lat": "28.61", "lon": "77.21"},
    ]
    dup_map, dup_groups, far_apart = detect_duplicates(stations, dup_m=500.0)
    assert len(dup_groups) == 0
    assert dup_map["1"]["group_id"] == ""
    assert "missing coordinates" in dup_map["1"]["dup_note"]
    assert dup_map["2"]["group_id"] == ""
    assert len(far_apart) == 0


def test_duplicates_configurable_dup_m_threshold() -> None:
    """Changing --dup-m changes whether stations ~300m apart are duplicates."""
    stations = [
        {"station_id": "1", "name": "Stadium", "lat": "28.5828", "lon": "77.2321"},
        {"station_id": "2", "name": "Stadium", "lat": "28.5802", "lon": "77.2338"},
    ]
    # At 500m threshold: ~328m apart -> DUPLICATE
    _, groups_500, _ = detect_duplicates(stations, dup_m=500.0)
    assert len(groups_500) == 1

    # At 200m threshold: ~328m apart -> NOT DUPLICATE
    _, groups_200, far_200 = detect_duplicates(stations, dup_m=200.0)
    assert len(groups_200) == 0
    assert len(far_200) == 2


def test_analyse_stations_tiny_hand_made_csv(tmp_path: Path) -> None:
    """Full analysis flow with exact duplicates, 7km apart, same spot diff names."""
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
        # 1 & 2: Exact duplicates (RK Puram CPCB vs caaqm, dist 0m)
        "17,R K Puram,CPCB,28.563,77.186,CC BY 4.0,True,True,True,http://a,2026-11-18,"
        ",True,False,True,2020-01-01,2026-11-18T18:00:00Z\n"
        "7044,r k puram,caaqm,28.563,77.186,,,,,http://b,2026-11-18,"
        ",True,False,True,2020-01-01,2022-10-31T00:45:00Z\n"
        # 3 & 4: Same name ~7 km apart (both within 25 km of Delhi)
        "5763,Narela,caaqm,28.670,77.210,,,,,http://c,2026-11-18,"
        ",True,False,True,2020-01-01,2018-05-12T06:00:00Z\n"
        "10485,narela,CPCB,28.730,77.210,,,,,http://d,2026-11-18,"
        ",True,False,True,2020-01-01,2026-11-18T18:00:00Z\n"
        # 5 & 6: Different names at same spot (Alpha vs Beta at dist 0m)
        "101,Station Alpha,CPCB,28.615,77.215,,,,,http://e,2026-11-18,"
        ",True,False,True,2020-01-01,2026-11-18T18:00:00Z\n"
        "102,Station Beta,CPCB,28.615,77.215,,,,,http://f,2026-11-18,"
        ",True,False,True,2020-01-01,2026-11-18T18:00:00Z\n"
        # 7: Missing coordinates
        "200,Station Missing,CPCB,,,,,,,http://g,2026-11-18,"
        ",True,False,True,2020-01-01,2026-11-18T18:00:00Z\n"
    )
    licences_path.write_text(licences_content, encoding="utf-8")

    summary_md = tmp_path / "station_summary.md"
    duplicates_md = tmp_path / "station_duplicates.md"
    candidates_csv = tmp_path / "candidates.csv"

    exit_code = main(
        [
            "--licences-csv",
            str(licences_path),
            "--areas-json",
            str(areas_path),
            "--max-km",
            "30.0",
            "--dup-m",
            "500.0",
            "--summary-md",
            str(summary_md),
            "--duplicates-md",
            str(duplicates_md),
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

    rows_by_id = {r["station_id"]: r for r in reader}

    # Verify duplicate pair 17 & 7044
    assert rows_by_id["17"]["duplicate_group_id"] == "DUP-01"
    assert rows_by_id["7044"]["duplicate_group_id"] == "DUP-01"
    assert "likely duplicate" in rows_by_id["17"]["dup_note"]
    assert "likely duplicate" in rows_by_id["7044"]["dup_note"]
    assert rows_by_id["17"]["decision"] == ""
    assert rows_by_id["7044"]["decision"] == ""

    # Verify same name 7 km apart (Narela 5763 & 10485)
    assert rows_by_id["5763"]["duplicate_group_id"] == ""
    assert rows_by_id["10485"]["duplicate_group_id"] == ""
    assert "same name, far apart" in rows_by_id["5763"]["dup_note"]
    assert "same name, far apart" in rows_by_id["10485"]["dup_note"]

    # Verify different names at same spot (Alpha 101 & Beta 102)
    assert rows_by_id["101"]["duplicate_group_id"] == ""
    assert rows_by_id["101"]["dup_note"] == ""
    assert rows_by_id["102"]["duplicate_group_id"] == ""
    assert rows_by_id["102"]["dup_note"] == ""

    # 2. Verify duplicates report (reports/station_duplicates.md)
    assert duplicates_md.exists()
    dup_content = duplicates_md.read_text(encoding="utf-8")
    assert "Group `DUP-01`: r k puram" in dup_content
    assert "| 17 | `CPCB` |" in dup_content
    assert "| 7044 | `caaqm` |" in dup_content
    assert "Same Name, Far Apart" in dup_content
    assert "narela" in dup_content

    # 3. Verify summary report (reports/station_summary.md)
    assert summary_md.exists()
    sum_content = summary_md.read_text(encoding="utf-8")
    assert "Duplicate Station Summary" in sum_content
    assert "Likely Duplicate Groups**: `1`" in sum_content


def test_main_cli_invalid_date() -> None:
    """Invalid date format must return non-zero exit code."""
    exit_code = main(["--as-of-date", "invalid-date"])
    assert exit_code == 1
