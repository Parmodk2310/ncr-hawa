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
    propose_decisions,
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


def test_rule_1_no_pm25_or_unknown() -> None:
    """Rule 1: has_pm25 is 'no' or unknown -> 'exclude', 'no PM2.5'."""
    stations = [
        {
            "station_id": "1",
            "name": "A",
            "lat": "28.6",
            "lon": "77.2",
            "has_pm25": "False",
            "datetime_last": "2026-11-18",
        },
        {
            "station_id": "2",
            "name": "B",
            "lat": "28.6",
            "lon": "77.2",
            "has_pm25": "",
            "datetime_last": "2026-11-18",
        },
    ]
    dup_map, dup_groups, _ = detect_duplicates(stations)
    ref_d = date(2026, 11, 19)
    cutoff = date(2026, 10, 20)
    decs = propose_decisions(stations, dup_map, dup_groups, ref_d, cutoff)
    assert decs["1"]["proposed_decision"] == "exclude"
    assert decs["1"]["proposed_reason"] == "no PM2.5"
    assert decs["2"]["proposed_decision"] == "exclude"
    assert decs["2"]["proposed_reason"] == "no PM2.5"


def test_rule_2_missing_datetime_last() -> None:
    """Rule 2: datetime_last missing -> 'review', 'last date unknown'."""
    stations = [
        {
            "station_id": "1",
            "name": "A",
            "lat": "28.6",
            "lon": "77.2",
            "has_pm25": "True",
            "datetime_last": "",
        },
        {
            "station_id": "2",
            "name": "B",
            "lat": "28.6",
            "lon": "77.2",
            "has_pm25": "True",
            "datetime_last": "   ",
        },
    ]
    dup_map, dup_groups, _ = detect_duplicates(stations)
    ref_d = date(2026, 11, 19)
    cutoff = date(2026, 10, 20)
    decs = propose_decisions(stations, dup_map, dup_groups, ref_d, cutoff)
    assert decs["1"]["proposed_decision"] == "review"
    assert decs["1"]["proposed_reason"] == "last date unknown"
    assert decs["2"]["proposed_decision"] == "review"
    assert decs["2"]["proposed_reason"] == "last date unknown"


def test_rule_3_duplicate_group_active_and_all_inactive() -> None:
    """Rule 3: Duplicate group resolution for active vs all-inactive groups."""
    # Active group (Stn 1 active, Stn 2 older)
    stns_active = [
        {
            "station_id": "1",
            "name": "A",
            "lat": "28.6",
            "lon": "77.2",
            "has_pm25": "True",
            "datetime_last": "2026-11-18",
        },
        {
            "station_id": "2",
            "name": "a",
            "lat": "28.6",
            "lon": "77.2",
            "has_pm25": "True",
            "datetime_last": "2022-01-01",
        },
    ]
    dup_map, dup_groups, _ = detect_duplicates(stns_active, dup_m=500.0)
    ref_d = date(2026, 11, 19)
    cutoff = date(2026, 10, 20)
    decs = propose_decisions(stns_active, dup_map, dup_groups, ref_d, cutoff)
    assert decs["1"]["proposed_decision"] == "use"
    assert decs["1"]["proposed_reason"] == "active monitor"
    assert decs["2"]["proposed_decision"] == "history_only"
    assert decs["2"]["proposed_reason"] == "older duplicate of 1"

    # All inactive group (Stn 3 from 2024, Stn 4 from 2022)
    stns_inactive = [
        {
            "station_id": "3",
            "name": "B",
            "lat": "28.6",
            "lon": "77.2",
            "has_pm25": "True",
            "datetime_last": "2024-01-01",
        },
        {
            "station_id": "4",
            "name": "b",
            "lat": "28.6",
            "lon": "77.2",
            "has_pm25": "True",
            "datetime_last": "2022-01-01",
        },
    ]
    dup_map2, dup_groups2, _ = detect_duplicates(stns_inactive, dup_m=500.0)
    decs2 = propose_decisions(stns_inactive, dup_map2, dup_groups2, ref_d, cutoff)
    assert decs2["3"]["proposed_decision"] == "history_only"
    assert decs2["3"]["proposed_reason"] == "no data in 30 days"
    assert decs2["4"]["proposed_decision"] == "history_only"
    assert decs2["4"]["proposed_reason"] == "older duplicate of 3"


def test_rule_4_datetime_last_older_than_30_days() -> None:
    """Rule 4: datetime_last > 30 days -> 'history_only', 'no data in 30 days'."""
    stations = [
        {
            "station_id": "1",
            "name": "Unique Stn",
            "lat": "28.6",
            "lon": "77.2",
            "has_pm25": "True",
            "datetime_last": "2025-01-01",
        },
    ]
    dup_map, dup_groups, _ = detect_duplicates(stations)
    ref_d = date(2026, 11, 19)
    cutoff = date(2026, 10, 20)
    decs = propose_decisions(stations, dup_map, dup_groups, ref_d, cutoff)
    assert decs["1"]["proposed_decision"] == "history_only"
    assert decs["1"]["proposed_reason"] == "no data in 30 days"


def test_rule_5_same_name_over_5km_override_rules_3_and_4() -> None:
    """Rule 5: Same name > 5 km apart overrides rules 3 and 4 with 'review'."""
    # Stn 1 active, Stn 2 stopped in 2018; ~7 km apart
    stations = [
        {
            "station_id": "1",
            "name": "Narela",
            "lat": "28.67",
            "lon": "77.21",
            "has_pm25": "True",
            "datetime_last": "2026-11-18",
        },
        {
            "station_id": "2",
            "name": "narela",
            "lat": "28.74",
            "lon": "77.21",
            "has_pm25": "True",
            "datetime_last": "2018-05-12",
        },
    ]
    dup_map, dup_groups, _ = detect_duplicates(stations, dup_m=500.0)
    ref_d = date(2026, 11, 19)
    cutoff = date(2026, 10, 20)
    decs = propose_decisions(stations, dup_map, dup_groups, ref_d, cutoff)

    # Both must get review, even though Stn 1 is active and Stn 2 is > 30 days old
    assert decs["1"]["proposed_decision"] == "review"
    assert decs["1"]["proposed_reason"] == "same name far apart, check coordinates"
    assert decs["2"]["proposed_decision"] == "review"
    assert decs["2"]["proposed_reason"] == "same name far apart, check coordinates"


def test_rule_6_everything_else() -> None:
    """Rule 6: Everything else -> 'use', 'active monitor'."""
    stations = [
        {
            "station_id": "1",
            "name": "Active Unique",
            "lat": "28.6",
            "lon": "77.2",
            "has_pm25": "True",
            "datetime_last": "2026-11-18",
        },
    ]
    dup_map, dup_groups, _ = detect_duplicates(stations)
    ref_d = date(2026, 11, 19)
    cutoff = date(2026, 10, 20)
    decs = propose_decisions(stations, dup_map, dup_groups, ref_d, cutoff)
    assert decs["1"]["proposed_decision"] == "use"
    assert decs["1"]["proposed_reason"] == "active monitor"


def test_publish_candidate_logic() -> None:
    """Verify publish_candidate=yes when redist=True, lic non-blank, dec='use'."""
    stations = [
        # Yes: redist True, licence non-blank, decision use
        {
            "station_id": "1",
            "name": "A",
            "lat": "28.6",
            "lon": "77.2",
            "has_pm25": "True",
            "datetime_last": "2026-11-18",
            "redistributionAllowed": "True",
            "licence_name": "CC BY 4.0",
        },
        # No: licence blank
        {
            "station_id": "2",
            "name": "B",
            "lat": "28.6",
            "lon": "77.2",
            "has_pm25": "True",
            "datetime_last": "2026-11-18",
            "redistributionAllowed": "True",
            "licence_name": "",
        },
        # No: redist False
        {
            "station_id": "3",
            "name": "C",
            "lat": "28.6",
            "lon": "77.2",
            "has_pm25": "True",
            "datetime_last": "2026-11-18",
            "redistributionAllowed": "False",
            "licence_name": "CC BY 4.0",
        },
        # No: decision history_only (> 30 days)
        {
            "station_id": "4",
            "name": "D",
            "lat": "28.6",
            "lon": "77.2",
            "has_pm25": "True",
            "datetime_last": "2020-01-01",
            "redistributionAllowed": "True",
            "licence_name": "CC BY 4.0",
        },
    ]
    dup_map, dup_groups, _ = detect_duplicates(stations)
    ref_d = date(2026, 11, 19)
    cutoff = date(2026, 10, 20)
    decs = propose_decisions(stations, dup_map, dup_groups, ref_d, cutoff)
    assert decs["1"]["publish_candidate"] == "yes"
    assert decs["2"]["publish_candidate"] == "no"
    assert decs["3"]["publish_candidate"] == "no"
    assert decs["4"]["publish_candidate"] == "no"


def test_end_to_end_tiny_csv_full_pipeline(tmp_path: Path) -> None:
    """Full pipeline run: duplicates, proposed decisions, empty decision."""
    areas_path = tmp_path / "areas.json"
    areas_path.write_text(json.dumps({"areas": SAMPLE_AREAS}), encoding="utf-8")

    licences_path = tmp_path / "licences.csv"
    licences_content = (
        "station_id,name,provider,lat,lon,licence_name,commercialUseAllowed,"
        "attributionRequired,redistributionAllowed,source_url,checked_on,"
        "decision,is_monitor,is_mobile,has_pm25,datetime_first,datetime_last\n"
        # 1 & 2: DUP at 500m (dist 0m)
        "1,RK Puram,CPCB,28.615,77.215,CC BY 4.0,True,True,True,http://a,2026-11-18,"
        ",True,False,True,2020-01-01,2026-11-18T18:00:00Z\n"
        "2,rk puram,caaqm,28.615,77.215,,,,,http://b,2026-11-18,"
        ",True,False,True,2020-01-01,2022-10-31T00:45:00Z\n"
        # 3 & 4: Same name 7 km apart (override to review)
        "3,Narela,caaqm,28.670,77.210,,,,,http://c,2026-11-18,"
        ",True,False,True,2020-01-01,2018-05-12T06:00:00Z\n"
        "4,narela,CPCB,28.730,77.210,,,,,http://d,2026-11-18,"
        ",True,False,True,2020-01-01,2026-11-18T18:00:00Z\n"
        # 5: No PM2.5 (Rule 1 -> exclude)
        "5,No PM,CPCB,28.615,77.215,,,,,http://e,2026-11-18,"
        ",True,False,False,2020-01-01,2026-11-18T18:00:00Z\n"
        # 6: Missing datetime_last (Rule 2 -> review)
        "6,No Date,CPCB,28.615,77.215,,,,,http://f,2026-11-18,"
        ",True,False,True,2020-01-01,\n"
        # 7 & 8: 700m apart (Not dup at 500m, but Dup at 1000m)
        "7,Patparganj,caaqm,28.625,77.285,,,,,http://g,2026-11-18,"
        ",True,False,True,2020-01-01,2018-05-13T11:30:00Z\n"
        "8,patparganj,CPCB,28.631,77.285,,,,,http://h,2026-11-18,"
        ",True,False,True,2020-01-01,2026-11-18T18:00:00Z\n"
    )
    licences_path.write_text(licences_content, encoding="utf-8")

    summary_md = tmp_path / "station_summary.md"
    dup_500_md = tmp_path / "station_duplicates.md"
    dup_1000_md = tmp_path / "station_duplicates_1000m.md"
    prop_dec_md = tmp_path / "proposed_decisions.md"
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
            str(dup_500_md),
            "--duplicates-1000-md",
            str(dup_1000_md),
            "--proposed-decisions-md",
            str(prop_dec_md),
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

    # Decision column must be strictly empty
    for r in reader:
        assert r["decision"] == ""

    # Check Stn 1: use, publish_candidate=yes
    assert rows_by_id["1"]["proposed_decision"] == "use"
    assert rows_by_id["1"]["publish_candidate"] == "yes"

    # Check Stn 2: history_only, older duplicate of 1
    assert rows_by_id["2"]["proposed_decision"] == "history_only"
    assert "older duplicate of 1" in rows_by_id["2"]["proposed_reason"]
    assert rows_by_id["2"]["publish_candidate"] == "no"

    # Check Stn 3 & 4: review due to Rule 5 override
    assert rows_by_id["3"]["proposed_decision"] == "review"
    assert rows_by_id["4"]["proposed_decision"] == "review"

    # Check Stn 5: exclude due to Rule 1
    assert rows_by_id["5"]["proposed_decision"] == "exclude"

    # Check Stn 6: review due to Rule 2
    assert rows_by_id["6"]["proposed_decision"] == "review"

    # 2. Verify reports exist and contain expected sections
    assert dup_500_md.exists()
    assert dup_1000_md.exists()
    assert prop_dec_md.exists()

    prop_content = prop_dec_md.read_text(encoding="utf-8")
    assert "| **1** | `has_pm25` is `no` or unknown" in prop_content
    assert "| **5** | Same name as another station > 5 km apart" in prop_content
    assert "Publishing Policy Note" in prop_content
    assert "Proposed Decisions by Forecast Area" in prop_content

    # 3. Verify that Patparganj (7 & 8) is far apart at 500m, but duplicate at 1000m
    d500_text = dup_500_md.read_text(encoding="utf-8")
    d1000_text = dup_1000_md.read_text(encoding="utf-8")
    assert "patparganj" in d500_text.lower()
    assert "Group `DUP-02`: patparganj" in d1000_text


def test_main_cli_invalid_date() -> None:
    """Invalid date format must return non-zero exit code."""
    exit_code = main(["--as-of-date", "invalid-date"])
    assert exit_code == 1
