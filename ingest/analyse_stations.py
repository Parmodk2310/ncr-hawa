"""Analyse OpenAQ station metadata, detect duplicates, and propose decisions."""

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
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Detect likely duplicate stations by normalised name and distance <= dup_m.

    Returns:
    - dup_map: dict of station_id -> {group_id, dup_note, group_members}
    - dup_groups: list of duplicate group dicts
    - far_apart_cases: list of same-name stations farther than dup_m
    """
    dup_map: dict[str, dict[str, Any]] = {}
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
                dup_map[sid] = {
                    "group_id": "",
                    "dup_note": "",
                    "group_members": [],
                }
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
                    "group_members": [],
                }

        n_valid = len(valid_list)
        if n_valid < 2:
            for s, _, _ in valid_list:
                sid = clean_field(s.get("station_id"))
                dup_map[sid] = {
                    "group_id": "",
                    "dup_note": "same name, other station(s) missing coordinates",
                    "group_members": [],
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
                        "group_members": group_stns,
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
                    "group_members": [],
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


def generate_duplicates_markdown(
    dup_groups: list[dict[str, Any]],
    far_apart_cases: list[dict[str, Any]],
    licences_csv_path: str,
    dup_m: float,
    total_stations: int,
) -> str:
    """Generate Markdown text for duplicate station report."""
    dup_lines: list[str] = [
        f"# Station Duplicate Detection Report ({dup_m:.0f} m Threshold)",
        "",
        "## Overview",
        f"- **Input Licences File**: `{licences_csv_path}`",
        f"- **Distance Threshold (`--dup-m`)**: `{dup_m:.0f} m` (maintainer guess)",
        f"- **Total Locations Evaluated**: `{total_stations}`",
        f"- **Likely Duplicate Groups Found**: `{len(dup_groups)}`",
        f"- **Total Duplicate Stations**: "
        f"`{sum(len(g['stations']) for g in dup_groups)}`",
        f"- **Same-Name Stations Separated Beyond Threshold**: "
        f"`{len(far_apart_cases)}`",
        "",
        f"## 1. Likely Duplicate Groups (<= {dup_m:.0f} m, Same Name)",
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

                dist_notes = []
                for pw in g["pairwise"]:
                    if pw["s1_id"] == sid:
                        dist_notes.append(f"{pw['dist_m']:.1f} m (to {pw['s2_id']})")
                    elif pw["s2_id"] == sid:
                        dist_notes.append(f"{pw['dist_m']:.1f} m (to {pw['s1_id']})")
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
            f"farther apart than `{dup_m:.0f} m`. "
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
    return "\n".join(dup_lines)


def propose_decisions(
    stations: list[dict[str, Any]],
    dup_map: dict[str, dict[str, Any]],
    dup_groups: list[dict[str, Any]],
    ref_date: date,
    cutoff_date: date,
) -> dict[str, dict[str, str]]:
    """Assign proposed_decision, proposed_reason, publish_candidate per station.

    Rules applied in order:
    1. has_pm25 is 'no' or unknown -> 'exclude', 'no PM2.5'
    2. datetime_last missing -> 'review', 'last date unknown'
    5. Same name as another station but > 5 km apart ->
       'review', 'same name far apart, check coordinates' (overrides rules 3 and 4)
    3. In a duplicate group:
       - latest datetime_last -> 'use' (if active) or 'history_only' (if inactive)
       - other members -> 'history_only', 'older duplicate of <station_id>'
    4. datetime_last older than 30 days -> 'history_only', 'no data in 30 days'
    6. Everything else -> 'use', 'active monitor'
    """
    # Find stations sharing normalised name with another station > 5 km apart
    by_name: dict[str, list[tuple[dict[str, Any], float, float]]] = defaultdict(list)
    for s in stations:
        norm = normalise_station_name(s.get("name"))
        try:
            lat = float(str(s.get("lat")).strip())
            lon = float(str(s.get("lon")).strip())
            by_name[norm].append((s, lat, lon))
        except (ValueError, TypeError, AttributeError):
            pass

    same_name_over_5km_ids: set[str] = set()
    for _, stn_list in by_name.items():
        if len(stn_list) < 2:
            continue
        for i in range(len(stn_list)):
            for j in range(i + 1, len(stn_list)):
                d_m = (
                    haversine_distance_km(
                        stn_list[i][1],
                        stn_list[i][2],
                        stn_list[j][1],
                        stn_list[j][2],
                    )
                    * 1000.0
                )
                if d_m > 5000.0:
                    same_name_over_5km_ids.add(
                        clean_field(stn_list[i][0].get("station_id"))
                    )
                    same_name_over_5km_ids.add(
                        clean_field(stn_list[j][0].get("station_id"))
                    )

    # Pre-calculate duplicate group latest member and activity
    # Rule 3 info: find primary member for each group and check same provider
    dup_group_info: dict[str, dict[str, Any]] = {}
    for g in dup_groups:
        members = g["stations"]
        if not members:
            continue

        providers = {clean_field(stn.get("provider")).lower() for stn in members}
        same_provider = len(providers) == 1

        def _get_dt(stn: dict[str, Any]) -> date:
            d = parse_iso_date(stn.get("datetime_last"))
            return d if d is not None else date.min

        # Sort descending by date, then deterministically by station_id
        sorted_members = sorted(
            members,
            key=lambda stn: (_get_dt(stn), clean_field(stn.get("station_id"))),
            reverse=True,
        )
        primary_stn = sorted_members[0]
        primary_dt = _get_dt(primary_stn)
        is_active = primary_dt >= cutoff_date
        dup_group_info[g["group_id"]] = {
            "primary_id": clean_field(primary_stn.get("station_id")),
            "is_active": is_active,
            "same_provider": same_provider,
        }

    decisions_map: dict[str, dict[str, str]] = {}

    for s in stations:
        sid = clean_field(s.get("station_id"))
        pm25_val = str(s.get("has_pm25", "")).strip().lower()
        has_pm25 = pm25_val in ("true", "t", "yes", "1")
        has_pm25_no = pm25_val in ("false", "f", "no", "0")
        has_pm25_unknown = not has_pm25 and not has_pm25_no

        dt_last_str = str(s.get("datetime_last", "")).strip()
        dt_last = parse_iso_date(dt_last_str)

        gid = dup_map.get(sid, {}).get("group_id", "")

        # Rule 1: has_pm25 is 'no' or unknown
        if has_pm25_no or has_pm25_unknown:
            prop_dec = "exclude"
            prop_reason = "no PM2.5"
        # Rule 5 (override): Same name as another station but > 5 km apart
        elif sid in same_name_over_5km_ids:
            prop_dec = "review"
            prop_reason = "same name far apart, check coordinates"
        # Rule 3: In a duplicate group
        elif gid and gid in dup_group_info:
            g_info = dup_group_info[gid]
            if g_info["same_provider"]:
                # Rule 3 exception: same-provider cluster
                prop_dec = "review"
                prop_reason = "same-provider cluster, check if separate devices"
            elif not dt_last_str or dt_last is None:
                prop_dec = "review"
                prop_reason = "last date unknown"
            else:
                prim_id = g_info["primary_id"]
                if not g_info["is_active"]:
                    # All members inactive
                    prop_dec = "history_only"
                    if sid == prim_id:
                        prop_reason = "no data in 30 days"
                    else:
                        prop_reason = f"older duplicate of {prim_id}"
                else:
                    if sid == prim_id:
                        prop_dec = "use"
                        prop_reason = "active monitor"
                    else:
                        prop_dec = "history_only"
                        prop_reason = f"older duplicate of {prim_id}"
        # Rule 2: datetime_last missing (stations not in duplicate groups)
        elif not dt_last_str or dt_last is None:
            prop_dec = "review"
            prop_reason = "last date unknown"
        # Rule 4: datetime_last older than 30 days
        elif dt_last < cutoff_date:
            prop_dec = "history_only"
            prop_reason = "no data in 30 days"
        # Rule 6: Everything else
        else:
            prop_dec = "use"
            prop_reason = "active monitor"

        # publish_candidate: yes only if redistributionAllowed is True,
        # licence is non-blank, and proposed_decision is 'use'
        redist_val = str(s.get("redistributionAllowed", "")).strip().lower()
        redist_allowed = redist_val in ("true", "t", "yes", "1")
        lic_name = str(s.get("licence_name", "")).strip()
        has_lic = bool(lic_name and lic_name.lower() != "unknown")

        if redist_allowed and has_lic and prop_dec == "use":
            pub_cand = "yes"
        else:
            pub_cand = "no"

        decisions_map[sid] = {
            "proposed_decision": prop_dec,
            "proposed_reason": prop_reason,
            "publish_candidate": pub_cand,
        }

    return decisions_map


def generate_proposed_decisions_markdown(
    candidates_rows: list[dict[str, Any]],
    areas: list[dict[str, Any]],
    licences_csv_path: str,
    ref_date: date,
    cutoff_date: date,
    proposal_dup_m: float = 500.0,
) -> str:
    """Generate Markdown text for proposed decisions report."""
    total_candidates = len(candidates_rows)
    dec_counts = Counter(r["proposed_decision"] for r in candidates_rows)
    pub_counts = Counter(r["publish_candidate"] for r in candidates_rows)

    # Area decision breakdown
    area_dec_map: dict[str, Counter[str]] = defaultdict(Counter)
    for r in candidates_rows:
        area_dec_map[r["area_id"]][r["proposed_decision"]] += 1

    md_lines: list[str] = [
        "# Proposed Station Decisions Report (Task A-003c)",
        "",
        "## Overview & Decision Rules",
        f"- **Input Licences File**: `{licences_csv_path}`",
        (
            f"- **Duplicate Threshold for Proposals (`--proposal-dup-m`)**: "
            f"`{proposal_dup_m:.0f} m` (maintainer guess)"
        ),
        f"- **Reference UTC Date**: `{ref_date.isoformat()}`",
        f"- **Active Cutoff Date (30 days)**: `{cutoff_date.isoformat()}`",
        f"- **Total Candidate Locations**: `{total_candidates}`",
        "",
        "### Decision Rules Hierarchy",
        (
            f"Duplicate detection threshold feeding these proposals is "
            f"`{proposal_dup_m:.0f} m`."
        ),
        "The following rules were applied in strict sequential order:",
        "",
        (
            "| Rule # | Condition | Proposed Decision | "
            "Proposed Reason | Priority / Notes |"
        ),
        "|---|---|---|---|---|",
        (
            "| **1** | `has_pm25` is `no` or unknown | "
            "`exclude` | `no PM2.5` | Highest priority |"
        ),
        (
            "| **5** | Same name as another station > 5 km apart | "
            "`review` | `same name far apart, check coordinates` | "
            "**Overrides rules 3 & 4** |"
        ),
        (
            "| **3** | In duplicate group (same provider) | "
            "`review` | `same-provider cluster, check if separate devices` | "
            "Rule 3 exception: never marked `history_only` |"
        ),
        (
            "| **3** | In duplicate group (different providers) | "
            "`use` (active) / `history_only` (inactive) | "
            "`active monitor` / `no data in 30 days` | "
            "Other members: `older duplicate of <id>` |"
        ),
        (
            "| **2** | `datetime_last` missing / invalid | "
            "`review` | `last date unknown` | Evaluated before recency |"
        ),
        (
            "| **4** | `datetime_last` older than 30 days | "
            "`history_only` | `no data in 30 days` | "
            "Inactive historical stations |"
        ),
        (
            "| **6** | Everything else | `use` | `active monitor` | "
            "Default for active valid monitors |"
        ),
        "",
        "> [!IMPORTANT]",
        "> **Publishing Policy Note (`AQ_11`)**:",
        "> `proposed_decision` is **never** set to `publish`.",
        (
            "> A separate column `publish_candidate = yes` is set **only if** "
            "`redistributionAllowed` is `True`,"
        ),
        "> `licence_name` is non-blank, and `proposed_decision` is `use`.",
        (
            "> **This does NOT mean publishing is allowed until the maintainer "
            "has read and verified the licence text.**"
        ),
        "",
        "## 1. Summary of Proposed Decisions",
        "| Proposed Decision | Station Count | Share | Description |",
        "|---|---|---|---|",
        (
            f"| `use` | {dec_counts.get('use', 0)} | "
            f"{_fmt_pct(dec_counts.get('use', 0), total_candidates)} | "
            "Active monitors recommended for forecast training/evaluation |"
        ),
        (
            f"| `history_only` | {dec_counts.get('history_only', 0)} | "
            f"{_fmt_pct(dec_counts.get('history_only', 0), total_candidates)} | "
            "Inactive (> 30 days) or older duplicates of active stations |"
        ),
        (
            f"| `review` | {dec_counts.get('review', 0)} | "
            f"{_fmt_pct(dec_counts.get('review', 0), total_candidates)} | "
            "Stations with same name > 5 km apart, missing dates, or clusters |"
        ),
        (
            f"| `exclude` | {dec_counts.get('exclude', 0)} | "
            f"{_fmt_pct(dec_counts.get('exclude', 0), total_candidates)} | "
            "Stations without confirmed PM2.5 capability |"
        ),
        (
            f"| **Total** | **{total_candidates}** | **100.0%** | "
            "All candidate stations within radius |"
        ),
        "",
        (
            f"- **Publish Candidates (`publish_candidate = yes`)**: "
            f"**{pub_counts.get('yes', 0)}** "
            f"({_fmt_pct(pub_counts.get('yes', 0), total_candidates)})"
        ),
        (
            f"- **Non-Publish Candidates (`publish_candidate = no`)**: "
            f"**{pub_counts.get('no', 0)}** "
            f"({_fmt_pct(pub_counts.get('no', 0), total_candidates)})"
        ),
        "",
        "## 2. Proposed Decisions by Forecast Area",
        (
            "| Area ID | Area Name | `use` | `history_only` | "
            "`review` | `exclude` | Total |"
        ),
        "|---|---|---|---|---|---|---|",
    ]

    for a in areas:
        aid = str(a["area_id"])
        aname = str(a.get("name", aid))
        counts = area_dec_map[aid]
        sub_total = sum(counts.values())
        md_lines.append(
            f"| `{aid}` | {aname} | {counts.get('use', 0)} | "
            f"{counts.get('history_only', 0)} | {counts.get('review', 0)} | "
            f"{counts.get('exclude', 0)} | **{sub_total}** |"
        )

    # Stations requiring review
    review_stations = [r for r in candidates_rows if r["proposed_decision"] == "review"]
    md_lines.extend(
        [
            "",
            "## 3. Stations Requiring Manual Review (`review`)",
            f"Total stations flagged for review: **{len(review_stations)}**",
            "",
            "| Station ID | Name | Area ID | Distance (km) | Reason | datetime_last |",
            "|---|---|---|---|---|---|",
        ]
    )

    for r in review_stations:
        sid = r["station_id"]
        name = r["name"]
        aid = r["area_id"]
        dist = r["distance_km"]
        reason = r["proposed_reason"]
        dt_last = r["datetime_last"]
        md_lines.append(
            f"| {sid} | {name} | `{aid}` | {dist} | `{reason}` | `{dt_last}` |"
        )

    # Publish candidates table
    pub_stations = [r for r in candidates_rows if r["publish_candidate"] == "yes"]
    md_lines.extend(
        [
            "",
            "## 4. Preliminary Publish Candidates (`publish_candidate = yes`)",
            f"Total publish candidate stations: **{len(pub_stations)}**",
            "",
            "> [!NOTE]",
            (
                f"> All other stations ({pub_counts.get('no', 0)}) have "
                "`redistributionAllowed = unknown` or blank licences;"
            ),
            "> internal use of unlicensed stations is unverified.",
            "",
            "| Station ID | Name | Provider | Licence Name | redistributionAllowed |",
            "|---|---|---|---|---|",
        ]
    )

    for r in pub_stations:
        sid = r["station_id"]
        name = r["name"]
        prov = r["provider"]
        lic = r["licence_name"]
        redist = r["redistributionAllowed"]
        md_lines.append(f"| {sid} | {name} | `{prov}` | `{lic}` | `{redist}` |")

    md_lines.extend(
        [
            "",
            "## 5. Next Steps for Maintainer",
            "1. Open `data/stations_candidates.csv`.",
            (
                "2. Inspect the `review` stations in Section 3 and confirm "
                "GPS coordinates."
            ),
            (
                "3. Copy or adjust `proposed_decision` values into the official "
                "`decision` column (`use` or `exclude`)."
            ),
            "4. Leave `decision` empty for any station still under verification.",
            "",
        ]
    )

    return "\n".join(md_lines)


def analyse_stations(
    licences_csv_path: str,
    areas_json_path: str,
    max_km: float = 25.0,
    dup_m: float = 500.0,
    proposal_dup_m: float = 500.0,
    summary_md_path: str | None = None,
    duplicates_md_path: str | None = None,
    duplicates_1000_md_path: str | None = None,
    proposed_decisions_md_path: str | None = None,
    candidates_csv_path: str | None = None,
    as_of_date: date | None = None,
    include_outside: bool = False,
) -> dict[str, Any]:
    """Analyse station licences CSV, detect duplicates, propose decisions."""
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

    # 1. Run duplicate detection at dup_m (default 500m)
    dup_map, dup_groups, far_apart_cases = detect_duplicates(raw_rows, dup_m=dup_m)

    # 2. Run duplicate detection at 1000m for secondary report
    _, dup_groups_1000, far_apart_1000 = detect_duplicates(raw_rows, dup_m=1000.0)

    # 3. Duplicate detection feeding proposed decisions
    if proposal_dup_m == dup_m:
        prop_dup_map = dup_map
        prop_dup_groups = dup_groups
    elif proposal_dup_m == 1000.0:
        prop_dup_map = {
            s["station_id"]: {
                "group_id": s["duplicate_group_id"],
                "dup_note": s["dup_note"],
            }
            for g in dup_groups_1000
            for s in g["stations"]
        }
        prop_dup_groups = dup_groups_1000
    else:
        prop_dup_map, prop_dup_groups, _ = detect_duplicates(
            raw_rows, dup_m=proposal_dup_m
        )

    # 4. Propose decisions
    cutoff_date = ref_date - timedelta(days=30)
    decisions_map = propose_decisions(
        raw_rows, prop_dup_map, prop_dup_groups, ref_date, cutoff_date
    )

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
        dec_info = decisions_map.get(
            sid,
            {
                "proposed_decision": "review",
                "proposed_reason": "unprocessed",
                "publish_candidate": "no",
            },
        )

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
            "proposed_decision": dec_info["proposed_decision"],
            "proposed_reason": dec_info["proposed_reason"],
            "publish_candidate": dec_info["publish_candidate"],
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

        is_candidate = area_id not in ("outside", "unknown")
        if is_candidate or include_outside:
            candidates_rows.append(row_item)

    # Write candidates CSV
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

    # Write reports/station_duplicates.md (500m)
    if duplicates_md_path:
        dup_md_dir = os.path.dirname(os.path.abspath(duplicates_md_path))
        os.makedirs(dup_md_dir, exist_ok=True)
        dup_md_text = generate_duplicates_markdown(
            dup_groups, far_apart_cases, licences_csv_path, dup_m, total_stations
        )
        with open(duplicates_md_path, "w", encoding="utf-8") as f:
            f.write(dup_md_text)

    # Write reports/station_duplicates_1000m.md (1000m)
    if duplicates_1000_md_path:
        dup_1000_dir = os.path.dirname(os.path.abspath(duplicates_1000_md_path))
        os.makedirs(dup_1000_dir, exist_ok=True)
        dup_1000_text = generate_duplicates_markdown(
            dup_groups_1000,
            far_apart_1000,
            licences_csv_path,
            1000.0,
            total_stations,
        )
        with open(duplicates_1000_md_path, "w", encoding="utf-8") as f:
            f.write(dup_1000_text)

    # Write reports/proposed_decisions.md
    if proposed_decisions_md_path:
        prop_dir = os.path.dirname(os.path.abspath(proposed_decisions_md_path))
        os.makedirs(prop_dir, exist_ok=True)
        prop_md_text = generate_proposed_decisions_markdown(
            candidates_rows,
            areas,
            licences_csv_path,
            ref_date,
            cutoff_date,
            proposal_dup_m=proposal_dup_m,
        )
        with open(proposed_decisions_md_path, "w", encoding="utf-8") as f:
            f.write(prop_md_text)

    # Write reports/station_summary.md
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
            f"- **Duplicate Groups Detected (500m)**: `{len(dup_groups)}`",
            f"- **Duplicate Groups Detected (1000m)**: `{len(dup_groups_1000)}`",
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
                f"- **Threshold 500m**: `{len(dup_groups)}` duplicate groups "
                "(see `reports/station_duplicates.md`).",
                f"- **Threshold 1000m**: `{len(dup_groups_1000)}` duplicate groups "
                "(see `reports/station_duplicates_1000m.md`).",
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
                "## 8. Proposed Decisions Summary",
                (
                    "- Detailed rule rationale and table in "
                    "`reports/proposed_decisions.md`."
                ),
                (
                    "- Review `data/stations_candidates.csv` before filling official "
                    "`decision`."
                ),
                "",
            ]
        )

        with open(summary_md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

    cand_dec_counts = Counter(r["proposed_decision"] for r in candidates_rows)

    return {
        "total_stations": total_stations,
        "kept_candidates": kept_count,
        "outside_count": len(outside_rows),
        "duplicate_groups_500m": len(dup_groups),
        "duplicate_groups_1000m": len(dup_groups_1000),
        "proposal_dup_m": proposal_dup_m,
        "proposed_decisions": dict(cand_dec_counts),
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
        "--proposal-dup-m",
        type=float,
        default=500.0,
        help=(
            "Duplicate distance threshold in metres used for proposed "
            "decisions (default: 500.0m)."
        ),
    )
    parser.add_argument(
        "--summary-md",
        default="reports/station_summary.md",
        help="Path to summary markdown (default: reports/station_summary.md).",
    )
    parser.add_argument(
        "--duplicates-md",
        default="reports/station_duplicates.md",
        help="Path to 500m duplicates report (default: reports/station_duplicates.md).",
    )
    parser.add_argument(
        "--duplicates-1000-md",
        default="reports/station_duplicates_1000m.md",
        help=(
            "Path to 1000m duplicates report "
            "(default: reports/station_duplicates_1000m.md)."
        ),
    )
    parser.add_argument(
        "--proposed-decisions-md",
        default="reports/proposed_decisions.md",
        help=(
            "Path to proposed decisions report "
            "(default: reports/proposed_decisions.md)."
        ),
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
            proposal_dup_m=args.proposal_dup_m,
            summary_md_path=args.summary_md,
            duplicates_md_path=args.duplicates_md,
            duplicates_1000_md_path=args.duplicates_1000_md,
            proposed_decisions_md_path=args.proposed_decisions_md,
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

    print("Station analysis and proposed decisions complete:")
    print(f"  Total locations: {results['total_stations']}")
    print(f"  Kept candidates: {results['kept_candidates']}")
    print(f"  Outside locations: {results['outside_count']}")
    print(f"  Duplicate groups (500m): {results['duplicate_groups_500m']}")
    print(f"  Duplicate groups (1000m): {results['duplicate_groups_1000m']}")
    print(f"  Proposal duplicate threshold: {results['proposal_dup_m']:.0f} m")
    print(f"  Proposed decisions: {results['proposed_decisions']}")
    print(f"  Summary report: {args.summary_md}")
    print(f"  Duplicates report (500m): {args.duplicates_md}")
    print(f"  Duplicates report (1000m): {args.duplicates_1000_md}")
    print(f"  Proposed decisions report: {args.proposed_decisions_md}")
    print(f"  Candidates CSV: {args.candidates_csv}")
    return 0
    print(f"  Candidates CSV: {args.candidates_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
