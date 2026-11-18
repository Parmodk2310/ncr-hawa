"""Analyse OpenAQ station metadata and licence records for Delhi-NCR shortlist."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

CANDIDATE_COLUMNS = [
    "station_id",
    "name",
    "provider",
    "lat",
    "lon",
    "area_id",
    "distance_km",
    "duplicate_group_id",
    "dup_note",
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


def normalise_station_name(name: Any) -> str:
    """Normalise station name: lowercase, collapsed whitespace sequences."""
    if not name:
        return ""
    return " ".join(str(name).lower().split())


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance between two WGS-84 points in kilometers."""
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (
        math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return radius_km * c


def assign_station_to_area(
    lat_val: Any,
    lon_val: Any,
    areas: list[dict[str, Any]],
    max_km: float,
) -> tuple[str, float | None]:
    """Assign station coordinates to nearest area center within max_km.

    Returns (area_id, distance_km).
    - If coordinates are missing or invalid, returns ("unknown", None).
    - If minimum distance exceeds max_km, returns ("outside", round(min_dist, 2)).
    - Otherwise returns (nearest_area_id, round(min_dist, 2)).
    """
    if lat_val is None or lon_val is None:
        return ("unknown", None)

    try:
        lat = float(str(lat_val).strip())
        lon = float(str(lon_val).strip())
    except (ValueError, TypeError, AttributeError):
        return ("unknown", None)

    if not areas:
        return ("outside", None)

    best_area_id: str | None = None
    min_dist = float("inf")

    for area in areas:
        area_lat = float(area["latitude"])
        area_lon = float(area["longitude"])
        dist = haversine_distance_km(lat, lon, area_lat, area_lon)
        if dist < min_dist:
            min_dist = dist
            best_area_id = str(area["area_id"])

    if best_area_id is None:
        return ("outside", None)

    rounded_dist = round(min_dist, 2)
    if min_dist <= max_km:
        return (best_area_id, rounded_dist)
    return ("outside", rounded_dist)


def parse_iso_date(date_str: Any) -> date | None:
    """Parse ISO 8601 datetime string to date object defensively."""
    if not date_str:
        return None
    val = str(date_str).strip()
    if not val:
        return None
    cleaned = val.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(cleaned).date()
    except (ValueError, TypeError):
        return None


def clean_field(val: Any) -> str:
    """Return stripped string or 'unknown' if empty or None."""
    if val is None:
        return "unknown"
    s = str(val).strip()
    return s if s else "unknown"


def parse_tri_state(val: Any) -> str:
    """Convert boolean-like field into 'yes', 'no', or 'unknown'."""
    if val is None:
        return "unknown"
    s = str(val).strip().lower()
    if s in ("true", "t", "1", "yes"):
        return "yes"
    if s in ("false", "f", "0", "no"):
        return "no"
    return "unknown"


def _fmt_pct(count: int, total: int) -> str:
    """Format count as percentage string."""
    if total <= 0:
        return "0.0%"
    return f"{count / total * 100.0:.1f}%"


def detect_duplicates(
    stations: list[dict[str, Any]],
    dup_m: float = 500.0,
) -> tuple[dict[str, dict[str, str]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Detect likely duplicate stations by normalised name and distance <= dup_m.

    Returns:
    - dup_map: dict of station_id -> {"group_id": str, "dup_note": str}
    - dup_groups: list of duplicate group dicts
    - far_apart_cases: list of same-name stations farther than dup_m
    """
    dup_map: dict[str, dict[str, str]] = {}
    dup_groups: list[dict[str, Any]] = []
    far_apart_cases: list[dict[str, Any]] = []

    # Group stations by normalised name
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in stations:
        norm = normalise_station_name(s.get("name"))
        by_name[norm].append(s)

    group_counter = 1

    for norm_name, group_stations in by_name.items():
        if len(group_stations) < 2:
            for s in group_stations:
                sid = clean_field(s.get("station_id"))
                dup_map[sid] = {"group_id": "", "dup_note": ""}
            continue

        # Separate stations with valid coordinates and missing coordinates
        valid_list: list[tuple[dict[str, Any], float, float]] = []
        for s in group_stations:
            sid = clean_field(s.get("station_id"))
            try:
                lat = float(str(s.get("lat")).strip())
                lon = float(str(s.get("lon")).strip())
                valid_list.append((s, lat, lon))
            except (ValueError, TypeError, AttributeError):
                dup_map[sid] = {
                    "group_id": "",
                    "dup_note": "same name, missing coordinates",
                }

        n_valid = len(valid_list)
        if n_valid < 2:
            for s, _, _ in valid_list:
                sid = clean_field(s.get("station_id"))
                dup_map[sid] = {
                    "group_id": "",
                    "dup_note": "same name, other station(s) missing coordinates",
                }
            continue

        # Compute pairwise distance in metres
        dist_matrix: dict[tuple[int, int], float] = {}
        adj: dict[int, list[int]] = {i: [] for i in range(n_valid)}

        for i in range(n_valid):
            for j in range(i + 1, n_valid):
                d_m = (
                    haversine_distance_km(
                        valid_list[i][1],
                        valid_list[i][2],
                        valid_list[j][1],
                        valid_list[j][2],
                    )
                    * 1000.0
                )
                dist_matrix[(i, j)] = d_m
                dist_matrix[(j, i)] = d_m
                if d_m <= dup_m:
                    adj[i].append(j)
                    adj[j].append(i)

        # Find connected components where edge is d_m <= dup_m
        visited: set[int] = set()
        components: list[list[int]] = []

        for i in range(n_valid):
            if i not in visited:
                comp: list[int] = []
                queue = [i]
                visited.add(i)
                while queue:
                    curr = queue.pop(0)
                    comp.append(curr)
                    for nbr in adj[curr]:
                        if nbr not in visited:
                            visited.add(nbr)
                            queue.append(nbr)
                components.append(comp)

        for comp in components:
            if len(comp) >= 2:
                group_id = f"DUP-{group_counter:02d}"
                group_counter += 1
                group_stns = [valid_list[idx][0] for idx in comp]

                # Pairwise distances within this duplicate group
                pairwise_dists: list[dict[str, Any]] = []
                for idx1 in comp:
                    for idx2 in comp:
                        if idx1 < idx2:
                            s1 = valid_list[idx1][0]
                            s2 = valid_list[idx2][0]
                            d = dist_matrix.get((idx1, idx2), 0.0)
                            pairwise_dists.append(
                                {
                                    "s1_id": clean_field(s1.get("station_id")),
                                    "s2_id": clean_field(s2.get("station_id")),
                                    "dist_m": d,
                                }
                            )

                max_dist_in_group = max(
                    (p["dist_m"] for p in pairwise_dists), default=0.0
                )

                dup_groups.append(
                    {
                        "group_id": group_id,
                        "name": norm_name,
                        "stations": group_stns,
                        "pairwise": pairwise_dists,
                        "max_dist_m": max_dist_in_group,
                    }
                )

                for idx in comp:
                    stn = valid_list[idx][0]
                    sid = clean_field(stn.get("station_id"))
                    other_dists = [
                        (valid_list[other_idx][0], dist_matrix[(idx, other_idx)])
                        for other_idx in comp
                        if other_idx != idx
                    ]
                    closest_other, closest_dist = min(other_dists, key=lambda x: x[1])
                    closest_id = clean_field(closest_other.get("station_id"))
                    dup_map[sid] = {
                        "group_id": group_id,
                        "dup_note": (
                            f"likely duplicate ({closest_dist:.1f} m to "
                            f"station {closest_id})"
                        ),
                    }
            else:
                # Isolated station with same name but separated by > dup_m
                idx = comp[0]
                stn = valid_list[idx][0]
                sid = clean_field(stn.get("station_id"))
                all_other_dists = [
                    (
                        valid_list[other_idx][0],
                        dist_matrix[(idx, other_idx)],
                    )
                    for other_idx in range(n_valid)
                    if other_idx != idx
                ]
                closest_other, closest_dist = min(all_other_dists, key=lambda x: x[1])
                closest_id = clean_field(closest_other.get("station_id"))

                if closest_dist >= 1000.0:
                    dist_disp = f"{closest_dist / 1000.0:.2f} km"
                else:
                    dist_disp = f"{closest_dist:.1f} m"

                dup_note_str = (
                    f"same name, far apart ({dist_disp} to station {closest_id})"
                )
                dup_map[sid] = {
                    "group_id": "",
                    "dup_note": dup_note_str,
                }
                far_apart_cases.append(
                    {
                        "station": stn,
                        "closest_other": closest_other,
                        "distance_m": closest_dist,
                        "norm_name": norm_name,
                    }
                )

    return dup_map, dup_groups, far_apart_cases


def analyse_stations(
    licences_csv_path: str,
    areas_json_path: str,
    max_km: float = 25.0,
    dup_m: float = 500.0,
    summary_md_path: str | None = None,
    duplicates_md_path: str | None = None,
    candidates_csv_path: str | None = None,
    as_of_date: date | None = None,
    include_outside: bool = False,
) -> dict[str, Any]:
    """Analyse station licences CSV, detect duplicates, write reports and CSV."""
    if as_of_date is None:
        ref_date = datetime.now(UTC).date()
    else:
        ref_date = as_of_date

    # Load areas
    with open(areas_json_path, encoding="utf-8") as f:
        areas_data = json.load(f)
    areas: list[dict[str, Any]] = areas_data.get("areas", [])

    # Load stations
    with open(licences_csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        raw_rows = list(reader)

    # 1. Run duplicate detection across all stations
    dup_map, dup_groups, far_apart_cases = detect_duplicates(raw_rows, dup_m=dup_m)

    # Tracking metrics
    area_counts: Counter[str] = Counter()
    provider_counts: Counter[str] = Counter()
    licence_status_counts: Counter[str] = Counter()
    licence_name_counts: Counter[str] = Counter()
    has_pm25_counts: Counter[str] = Counter()
    is_mobile_counts: Counter[str] = Counter()
    is_monitor_counts: Counter[str] = Counter()

    recency_counts = {
        "within_30_days": 0,
        "older_than_30_days": 0,
        "unknown_or_missing": 0,
    }

    processed_rows: list[dict[str, Any]] = []
    candidates_rows: list[dict[str, Any]] = []
    outside_rows: list[dict[str, Any]] = []

    cutoff_date = ref_date - timedelta(days=30)

    for row in raw_rows:
        lat_val = row.get("lat")
        lon_val = row.get("lon")
        area_id, dist_km = assign_station_to_area(lat_val, lon_val, areas, max_km)
        area_counts[area_id] += 1

        provider_str = clean_field(row.get("provider"))
        provider_counts[provider_str] += 1

        lic_name_raw = row.get("licence_name", "")
        lic_name_clean = lic_name_raw.strip() if lic_name_raw else ""
        if lic_name_clean:
            licence_status_counts["listed"] += 1
            licence_name_counts[lic_name_clean] += 1
        else:
            licence_status_counts["no licence"] += 1

        pm25_state = parse_tri_state(row.get("has_pm25"))
        has_pm25_counts[pm25_state] += 1

        mobile_state = parse_tri_state(row.get("is_mobile"))
        is_mobile_counts[mobile_state] += 1

        monitor_state = parse_tri_state(row.get("is_monitor"))
        is_monitor_counts[monitor_state] += 1

        last_dt = parse_iso_date(row.get("datetime_last"))
        if last_dt is None:
            recency_counts["unknown_or_missing"] += 1
        elif cutoff_date <= last_dt <= ref_date:
            recency_counts["within_30_days"] += 1
        else:
            recency_counts["older_than_30_days"] += 1

        sid = clean_field(row.get("station_id"))
        dup_info = dup_map.get(sid, {"group_id": "", "dup_note": ""})

        row_item = {
            "station_id": sid,
            "name": clean_field(row.get("name")),
            "provider": provider_str,
            "lat": clean_field(lat_val),
            "lon": clean_field(lon_val),
            "area_id": area_id,
            "distance_km": f"{dist_km:.2f}" if dist_km is not None else "unknown",
            "duplicate_group_id": dup_info["group_id"],
            "dup_note": dup_info["dup_note"],
            "licence_name": clean_field(lic_name_raw),
            "commercialUseAllowed": clean_field(row.get("commercialUseAllowed")),
            "attributionRequired": clean_field(row.get("attributionRequired")),
            "redistributionAllowed": clean_field(row.get("redistributionAllowed")),
            "source_url": clean_field(row.get("source_url")),
            "checked_on": clean_field(row.get("checked_on")),
            "decision": "",  # Strictly empty string for maintainer decision
            "is_monitor": clean_field(row.get("is_monitor")),
            "is_mobile": clean_field(row.get("is_mobile")),
            "has_pm25": clean_field(row.get("has_pm25")),
            "datetime_first": clean_field(row.get("datetime_first")),
            "datetime_last": clean_field(row.get("datetime_last")),
            "_dist_num": dist_km,
        }
        processed_rows.append(row_item)

        if area_id == "outside":
            outside_rows.append(row_item)

        # Candidate selection: stations within max_km (or all if include_outside)
        is_candidate = area_id not in ("outside", "unknown")
        if is_candidate or include_outside:
            candidates_rows.append(row_item)

    # Write candidates CSV if requested
    if candidates_csv_path:
        csv_dir = os.path.dirname(os.path.abspath(candidates_csv_path))
        os.makedirs(csv_dir, exist_ok=True)
        with open(candidates_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=CANDIDATE_COLUMNS, extrasaction="ignore"
            )
            writer.writeheader()
            for r in candidates_rows:
                writer.writerow(r)

    total_stations = len(raw_rows)
    kept_count = len(candidates_rows)

    # Generate Reports: reports/station_duplicates.md
    if duplicates_md_path:
        dup_md_dir = os.path.dirname(os.path.abspath(duplicates_md_path))
        os.makedirs(dup_md_dir, exist_ok=True)

        dup_lines: list[str] = [
            "# Station Duplicate Detection Report (Task A-003b)",
            "",
            "## Overview",
            f"- **Input Licences File**: `{licences_csv_path}`",
            f"- **Distance Threshold (`--dup-m`)**: `{dup_m} m` (maintainer guess)",
            f"- **Total Locations Evaluated**: `{total_stations}`",
            f"- **Likely Duplicate Groups Found**: `{len(dup_groups)}`",
            f"- **Total Duplicate Stations**: "
            f"`{sum(len(g['stations']) for g in dup_groups)}`",
            f"- **Same-Name Stations Separated Beyond Threshold**: "
            f"`{len(far_apart_cases)}`",
            "",
            "## 1. Likely Duplicate Groups (Distance <= "
            f"{dup_m:.0f} m, Same Normalised Name)",
            "",
        ]

        if not dup_groups:
            dup_lines.append("No duplicate groups found within the threshold.\n")
        else:
            for g in dup_groups:
                gid = g["group_id"]
                gname = g["name"]
                stns = g["stations"]
                max_d = g["max_dist_m"]
                dup_lines.extend(
                    [
                        f"### Group `{gid}`: {gname}",
                        f"- **Stations in Group**: `{len(stns)}`",
                        f"- **Maximum Distance Apart**: `{max_d:.1f} m`",
                        "",
                        "| Station ID | Provider | Distance Apart | datetime_first | "
                        "datetime_last | Licence Name | has_pm25 |",
                        "|---|---|---|---|---|---|---|",
                    ]
                )
                for s in stns:
                    sid = clean_field(s.get("station_id"))
                    prov = clean_field(s.get("provider"))
                    dt_first = clean_field(s.get("datetime_first"))
                    dt_last = clean_field(s.get("datetime_last"))
                    lic = clean_field(s.get("licence_name"))
                    pm25 = clean_field(s.get("has_pm25"))

                    # Distances to other members in group
                    dist_notes = []
                    for pw in g["pairwise"]:
                        if pw["s1_id"] == sid:
                            dist_notes.append(
                                f"{pw['dist_m']:.1f} m (to {pw['s2_id']})"
                            )
                        elif pw["s2_id"] == sid:
                            dist_notes.append(
                                f"{pw['dist_m']:.1f} m (to {pw['s1_id']})"
                            )
                    dist_disp = "; ".join(dist_notes) if dist_notes else "0.0 m"

                    dup_lines.append(
                        f"| {sid} | `{prov}` | {dist_disp} | `{dt_first}` | "
                        f"`{dt_last}` | `{lic}` | `{pm25}` |"
                    )
                dup_lines.append("")

        dup_lines.extend(
            [
                f"## 2. Same Name, Far Apart (> {dup_m:.0f} m)",
                "",
                "These stations share identical normalised names but are located "
                f"farther apart than `{dup_m} m`. "
                "Per project rules, they are **not** treated as duplicates.",
                "",
                "| Station ID | Normalised Name | Provider | Closest Counterpart | "
                "Distance Apart | datetime_last |",
                "|---|---|---|---|---|---|",
            ]
        )

        if not far_apart_cases:
            dup_lines.append("No same-name far-apart stations found.\n")
        else:
            for fa in far_apart_cases:
                s = fa["station"]
                sid = clean_field(s.get("station_id"))
                prov = clean_field(s.get("provider"))
                name_disp = fa["norm_name"]
                c_stn = fa["closest_other"]
                c_id = clean_field(c_stn.get("station_id"))
                d_m = fa["distance_m"]
                d_disp = f"{d_m / 1000.0:.2f} km" if d_m >= 1000.0 else f"{d_m:.1f} m"
                dt_l = clean_field(s.get("datetime_last"))
                dup_lines.append(
                    f"| {sid} | `{name_disp}` | `{prov}` | Station {c_id} | "
                    f"**{d_disp}** | `{dt_l}` |"
                )

        dup_lines.extend(
            [
                "",
                "## 3. Decision Guidance for Candidates CSV",
                "1. In candidates CSV, duplicates are tagged with `duplicate_group_id` "
                "and `dup_note`.",
                "2. When deciding which station to keep in each duplicate group:",
                "   - Prefer stations with active reporting (`datetime_last` in 2026).",
                "   - Prefer reference-grade monitors (`is_monitor = True`).",
                "   - Mark one as `use` and duplicates as `exclude` in `decision`.",
                "3. The `decision` column remains empty for maintainer review.",
                "",
            ]
        )

        with open(duplicates_md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(dup_lines))

    # Generate Markdown Summary Report (reports/station_summary.md)
    if summary_md_path:
        md_dir = os.path.dirname(os.path.abspath(summary_md_path))
        os.makedirs(md_dir, exist_ok=True)

        md_lines: list[str] = [
            "# Station & Licence Shortlist Summary (Task A-003)",
            "",
            "## Overview",
            f"- **Input Licences File**: `{licences_csv_path}`",
            f"- **Input Areas File**: `{areas_json_path}`",
            f"- **Reference UTC Date**: `{ref_date.isoformat()}`",
            f"- **Distance Threshold (`--max-km`)**: `{max_km} km` (maintainer guess)",
            f"- **Duplicate Threshold (`--dup-m`)**: `{dup_m} m` (maintainer guess)",
            f"- **Total Locations Evaluated**: `{total_stations}`",
            f"- **Candidate Locations Kept**: `{kept_count}`",
            f"- **Locations Outside Threshold**: `{len(outside_rows)}`",
            f"- **Duplicate Groups Detected**: `{len(dup_groups)}`",
            "",
            "## 1. Station Distribution by Forecast Area",
            "| Area ID | Description / Center | Radius Limit | Station Count | Share |",
            "|---|---|---|---|---|",
        ]

        for area in areas:
            aid = str(area["area_id"])
            aname = str(area.get("name", aid))
            cnt = area_counts.get(aid, 0)
            pct_str = _fmt_pct(cnt, total_stations)
            md_lines.append(
                f"| `{aid}` | {aname} | <= {max_km} km | {cnt} | {pct_str} |"
            )

        outside_cnt = area_counts.get("outside", 0)
        outside_pct_str = _fmt_pct(outside_cnt, total_stations)
        md_lines.append(
            f"| `outside` | Beyond {max_km} km radius | > {max_km} km | "
            f"{outside_cnt} | {outside_pct_str} |"
        )

        unknown_area_cnt = area_counts.get("unknown", 0)
        if unknown_area_cnt > 0:
            unknown_pct_str = _fmt_pct(unknown_area_cnt, total_stations)
            md_lines.append(
                f"| `unknown` | Missing / Invalid Coordinates | N/A | "
                f"{unknown_area_cnt} | {unknown_pct_str} |"
            )

        md_lines.extend(
            [
                f"| **Total** | All Locations | - | {total_stations} | 100.0% |",
                "",
                "## 2. Provider Breakdown",
                "| Provider | Total Count | Kept Candidates | Licence Status |",
                "|---|---|---|---|",
            ]
        )

        for prov, total_prov_cnt in provider_counts.most_common():
            cand_prov_cnt = sum(1 for c in candidates_rows if c["provider"] == prov)
            md_lines.append(f"| `{prov}` | {total_prov_cnt} | {cand_prov_cnt} | - |")

        md_lines.extend(
            [
                "",
                "## 3. Licence Status",
                f"- **Listed Licence**: {licence_status_counts.get('listed', 0)}",
            ]
        )
        for lic_name, cnt in licence_name_counts.most_common():
            md_lines.append(f"  - `{lic_name}`: {cnt}")
        md_lines.extend(
            [
                f"- **No Licence**: {licence_status_counts.get('no licence', 0)}",
                "",
                "> [!IMPORTANT]",
                "> Per data policy (`AQ_11`), missing licence data is reported as "
                "`unknown`.",
                "> If redistribution is unconfirmed, only derived forecasts may "
                "be published, never raw station observations.",
                "",
                "## 4. Sensor & Parameter Characteristics",
                "| Parameter | Value | Count | Share |",
                "|---|---|---|---|",
                f"| `has_pm25` | `yes` | {has_pm25_counts.get('yes', 0)} | "
                f"{_fmt_pct(has_pm25_counts.get('yes', 0), total_stations)} |",
                f"| `has_pm25` | `no` | {has_pm25_counts.get('no', 0)} | "
                f"{_fmt_pct(has_pm25_counts.get('no', 0), total_stations)} |",
                f"| `has_pm25` | `unknown` | {has_pm25_counts.get('unknown', 0)} | "
                f"{_fmt_pct(has_pm25_counts.get('unknown', 0), total_stations)} |",
                f"| `is_mobile` | `yes` | {is_mobile_counts.get('yes', 0)} | "
                f"{_fmt_pct(is_mobile_counts.get('yes', 0), total_stations)} |",
                f"| `is_mobile` | `no` | {is_mobile_counts.get('no', 0)} | "
                f"{_fmt_pct(is_mobile_counts.get('no', 0), total_stations)} |",
                f"| `is_mobile` | `unknown` | {is_mobile_counts.get('unknown', 0)} | "
                f"{_fmt_pct(is_mobile_counts.get('unknown', 0), total_stations)} |",
                f"| `is_monitor` | `yes` | {is_monitor_counts.get('yes', 0)} | "
                f"{_fmt_pct(is_monitor_counts.get('yes', 0), total_stations)} |",
                f"| `is_monitor` | `no` | {is_monitor_counts.get('no', 0)} | "
                f"{_fmt_pct(is_monitor_counts.get('no', 0), total_stations)} |",
                f"| `is_monitor` | `unknown` | {is_monitor_counts.get('unknown', 0)} | "
                f"{_fmt_pct(is_monitor_counts.get('unknown', 0), total_stations)} |",
                "",
                "## 5. Data Recency (`datetime_last`)",
                f"- **Reference Date**: `{ref_date.isoformat()}` (UTC)",
                f"- **Active within last 30 days** (>= `{cutoff_date.isoformat()}`): "
                f"**{recency_counts['within_30_days']}**",
                f"- **Historical only** (> 30 days old): "
                f"**{recency_counts['older_than_30_days']}**",
                f"- **Unknown / Missing date**: "
                f"**{recency_counts['unknown_or_missing']}**",
                "",
                "## 6. Duplicate Station Summary",
                f"- **Duplicate Distance Threshold (`--dup-m`)**: `{dup_m} m`",
                f"- **Likely Duplicate Groups**: `{len(dup_groups)}`",
                f"- **Same-Name Far Apart**: `{len(far_apart_cases)}`",
                "- Detailed audit available in `reports/station_duplicates.md`.",
                "",
                "## 7. Outside Locations (> 25 km threshold)",
                f"Total outside locations: **{len(outside_rows)}**",
                "| Station ID | Name | Provider | Lat | Lon | Nearest Distance (km) |",
                "|---|---|---|---|---|---|",
            ]
        )

        for out_row in sorted(
            outside_rows,
            key=lambda x: (
                float(x["_dist_num"]) if x["_dist_num"] is not None else float("inf")
            ),
        ):
            dist_disp = (
                f"{out_row['_dist_num']:.2f}"
                if out_row["_dist_num"] is not None
                else "unknown"
            )
            md_lines.append(
                f"| {out_row['station_id']} | {out_row['name']} | "
                f"{out_row['provider']} | {out_row['lat']} | {out_row['lon']} | "
                f"{dist_disp} |"
            )

        md_lines.extend(
            [
                "",
                "## 8. Next Steps & Decision Guide",
                "1. Inspect `data/stations_candidates.csv`.",
                "2. Check duplicate tags (`duplicate_group_id`, `dup_note`).",
                "3. Fill `decision` column (`use`, `publish`, `exclude`) per `AQ_11`.",
                "4. Do not invent licences; unverified flags stay `unknown`.",
                "",
            ]
        )

        with open(summary_md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

    return {
        "total_stations": total_stations,
        "kept_candidates": kept_count,
        "outside_count": len(outside_rows),
        "duplicate_groups_count": len(dup_groups),
        "duplicate_stations_count": sum(len(g["stations"]) for g in dup_groups),
        "far_apart_count": len(far_apart_cases),
        "ref_date": ref_date.isoformat(),
        "area_counts": dict(area_counts),
        "provider_counts": dict(provider_counts),
        "licence_status_counts": dict(licence_status_counts),
        "recency_counts": recency_counts,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for station analysis."""
    parser = argparse.ArgumentParser(
        description="Analyse OpenAQ station metadata and licence records for Delhi-NCR."
    )
    parser.add_argument(
        "--licences-csv",
        default="data/licences.csv",
        help="Path to input licences CSV (default: data/licences.csv).",
    )
    parser.add_argument(
        "--areas-json",
        default="configs/areas.json",
        help="Path to areas config JSON (default: configs/areas.json).",
    )
    parser.add_argument(
        "--max-km",
        type=float,
        default=25.0,
        help="Maximum distance in km from area center (default: 25.0 km).",
    )
    parser.add_argument(
        "--dup-m",
        type=float,
        default=500.0,
        help="Metres to consider same-name stations duplicates (default: 500m).",
    )
    parser.add_argument(
        "--summary-md",
        default="reports/station_summary.md",
        help="Path to summary markdown (default: reports/station_summary.md).",
    )
    parser.add_argument(
        "--duplicates-md",
        default="reports/station_duplicates.md",
        help="Path to duplicates report (default: reports/station_duplicates.md).",
    )
    parser.add_argument(
        "--candidates-csv",
        default="data/stations_candidates.csv",
        help="Path to output candidates CSV (default: data/stations_candidates.csv).",
    )
    parser.add_argument(
        "--as-of-date",
        type=str,
        default=None,
        help="Reference UTC date YYYY-MM-DD for recency calculation.",
    )
    parser.add_argument(
        "--include-outside",
        action="store_true",
        help="Include outside stations in candidates CSV (with area_id='outside').",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(argv)

    as_of: date | None = None
    if args.as_of_date:
        try:
            as_of = datetime.strptime(args.as_of_date.strip(), "%Y-%m-%d").date()
        except ValueError:
            print(
                f"Error: Invalid --as-of-date '{args.as_of_date}', "
                "expected YYYY-MM-DD.",
                file=sys.stderr,
            )
            return 1

    try:
        results = analyse_stations(
            licences_csv_path=args.licences_csv,
            areas_json_path=args.areas_json,
            max_km=args.max_km,
            dup_m=args.dup_m,
            summary_md_path=args.summary_md,
            duplicates_md_path=args.duplicates_md,
            candidates_csv_path=args.candidates_csv,
            as_of_date=as_of,
            include_outside=args.include_outside,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error during analysis: {e}", file=sys.stderr)
        return 1

    print("Station analysis complete:")
    print(f"  Total locations: {results['total_stations']}")
    print(f"  Kept candidates: {results['kept_candidates']}")
    print(f"  Outside locations: {results['outside_count']}")
    print(f"  Duplicate groups: {results['duplicate_groups_count']}")
    print(f"  Duplicate stations: {results['duplicate_stations_count']}")
    print(f"  Same-name far apart: {results['far_apart_count']}")
    print(f"  Summary report: {args.summary_md}")
    print(f"  Duplicates report: {args.duplicates_md}")
    print(f"  Candidates CSV: {args.candidates_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
