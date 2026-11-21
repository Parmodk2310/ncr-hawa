"""Apply station decisions from proposed decisions to candidates CSV."""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from typing import Any

ALLOWED_DECISIONS = {"use", "history_only", "exclude", "review"}

MAPPING_TABLE = [
    {
        "proposed": "use",
        "decision": "use",
        "description": "Active monitor used in forecast model training and evaluation",
    },
    {
        "proposed": "history_only",
        "decision": "history_only",
        "description": (
            "Inactive station or older duplicate; retained for historical "
            "reference only"
        ),
    },
    {
        "proposed": "exclude",
        "decision": "exclude",
        "description": ("Excluded from pipeline (e.g. no verified PM2.5 capability)"),
    },
    {
        "proposed": "review",
        "decision": "review",
        "description": (
            "Unresolved station pending manual investigation; NOT converted to exclude"
        ),
    },
]


def load_area_names(areas_path: str = "configs/areas.json") -> dict[str, str]:
    """Load area_id to display name mapping from configs/areas.json."""
    if not os.path.exists(areas_path):
        return {}
    try:
        with open(areas_path, encoding="utf-8") as f:
            data = json.load(f)
            return {
                a["area_id"]: a.get("name", a["area_id"])
                for a in data.get("areas", [])
                if "area_id" in a
            }
    except (OSError, json.JSONDecodeError):
        return {}


def apply_station_decisions(
    candidates_path: str,
    output_path: str | None = None,
    areas_path: str = "configs/areas.json",
    report_path: str = "reports/decision_summary.md",
) -> dict[str, Any]:
    """Apply decisions to candidate stations CSV and write summary report."""
    if output_path is None:
        output_path = candidates_path

    if not os.path.exists(candidates_path):
        raise FileNotFoundError(f"Candidates file not found: {candidates_path}")

    with open(candidates_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames or "decision" not in fieldnames:
            raise ValueError(f"Missing 'decision' column in {candidates_path}")
        if "proposed_decision" not in fieldnames:
            raise ValueError(f"Missing 'proposed_decision' column in {candidates_path}")
        rows = list(reader)

    skipped_count = 0
    applied_count = 0

    for row in rows:
        existing = row.get("decision", "").strip()
        if existing != "":
            skipped_count += 1
            continue

        proposed = row.get("proposed_decision", "").strip()
        if proposed == "publish":
            raise ValueError(
                "Invariant violated: proposed decision cannot be 'publish'"
            )
        if proposed in ALLOWED_DECISIONS:
            row["decision"] = proposed
            applied_count += 1
        elif proposed != "":
            # Unknown proposed decision left empty or flagged
            row["decision"] = ""

    # Atomic write to output CSV
    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)
    tmp_path = f"{output_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, output_path)

    # Compute stats for reporting
    area_names = load_area_names(areas_path)
    counts_by_area: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total_counts: dict[str, int] = defaultdict(int)
    review_stations: list[dict[str, str]] = []

    for row in rows:
        area_id = row.get("area_id", "unknown")
        dec = row.get("decision", "").strip() or "unassigned"
        counts_by_area[area_id][dec] += 1
        total_counts[dec] += 1

        if dec == "review":
            review_stations.append(
                {
                    "station_id": row.get("station_id", ""),
                    "name": row.get("name", ""),
                    "provider": row.get("provider", ""),
                    "area_id": area_id,
                    "proposed_reason": row.get("proposed_reason", ""),
                }
            )

    report_content = generate_decision_report(
        counts_by_area=counts_by_area,
        total_counts=total_counts,
        review_stations=review_stations,
        area_names=area_names,
        total_rows=len(rows),
        applied_count=applied_count,
        skipped_count=skipped_count,
    )

    if report_path:
        rep_dir = os.path.dirname(os.path.abspath(report_path))
        os.makedirs(rep_dir, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

    return {
        "total_rows": len(rows),
        "applied_count": applied_count,
        "skipped_count": skipped_count,
        "counts_by_area": dict(counts_by_area),
        "total_counts": dict(total_counts),
        "review_stations_count": len(review_stations),
    }


def generate_decision_report(
    counts_by_area: dict[str, dict[str, int]],
    total_counts: dict[str, int],
    review_stations: list[dict[str, str]],
    area_names: dict[str, str],
    total_rows: int,
    applied_count: int,
    skipped_count: int,
) -> str:
    """Format markdown decision summary report."""
    lines: list[str] = []
    lines.append("# Station Decision Summary Report (Task A-003d)")
    lines.append("")
    lines.append("## 1. Decision Mapping Table")
    lines.append(
        "Decisions were populated directly from `proposed_decision` according "
        "to the approved rule mappings below."
    )
    lines.append("")
    lines.append("| Proposed Decision | Applied Decision | Description / Policy |")
    lines.append("|---|---|---|")
    for item in MAPPING_TABLE:
        lines.append(
            f"| `{item['proposed']}` | `{item['decision']}` | {item['description']} |"
        )
    lines.append("")
    lines.append("> [!IMPORTANT]")
    lines.append("> **Safety & Policy Guardrails**:")
    lines.append(
        "> - **No 'publish' in decision**: `decision` is strictly limited to "
        "`use`, `history_only`, `exclude`, or `review`. "
        "It is **never** set to `publish`."
    )
    lines.append(
        "> - **Protected Columns**: `publish_candidate`, `proposed_decision`, and "
        "`proposed_reason` are never modified by this script."
    )
    lines.append(
        "> - **Skip-if-nonempty**: Any station row where `decision` was already "
        "non-empty was refused overwrite and preserved as-is."
    )
    lines.append("")
    lines.append("## 2. Decision Application Summary")
    lines.append(f"- **Total candidate stations**: {total_rows}")
    lines.append(f"- **Decisions newly applied**: {applied_count}")
    lines.append(f"- **Pre-existing decisions skipped**: {skipped_count}")
    lines.append("")
    lines.append("## 3. Decision Counts by Area")
    lines.append(
        "| Area ID | Area Name | `use` | `history_only` | `review` | `exclude` |"
        " Total |"
    )
    lines.append("|---|---|---|---|---|---|---|")

    # Sort areas by name or id
    sorted_areas = sorted(counts_by_area.keys())
    for aid in sorted_areas:
        aname = area_names.get(aid, aid.replace("_", " ").title())
        c_use = counts_by_area[aid].get("use", 0)
        c_hist = counts_by_area[aid].get("history_only", 0)
        c_rev = counts_by_area[aid].get("review", 0)
        c_exc = counts_by_area[aid].get("exclude", 0)
        row_tot = sum(counts_by_area[aid].values())
        line = (
            f"| `{aid}` | {aname} | {c_use} | {c_hist} | "
            f"{c_rev} | {c_exc} | **{row_tot}** |"
        )
        lines.append(line)

    tot_use = total_counts.get("use", 0)
    tot_hist = total_counts.get("history_only", 0)
    tot_rev = total_counts.get("review", 0)
    tot_exc = total_counts.get("exclude", 0)
    overall = sum(total_counts.values())
    lines.append(
        f"| **Total** | **All Areas** | **{tot_use}** | **{tot_hist}** | "
        f"**{tot_rev}** | **{tot_exc}** | **{overall}** |"
    )
    lines.append("")

    lines.append("## 4. Stations Pending Review (`decision = review`)")
    lines.append(
        "Stations marked `review` remain unresolved and require manual investigation. "
        "They are **not** turned into `exclude`."
    )
    lines.append("")
    if review_stations:
        lines.append(
            "| Station ID | Station Name | Provider | Area ID | Proposed Reason |"
        )
        lines.append("|---|---|---|---|---|")
        for s in review_stations:
            clean_name = s["name"].replace("|", "\\|")
            lines.append(
                f"| `{s['station_id']}` | {clean_name} | {s['provider']} | "
                f"`{s['area_id']}` | {s['proposed_reason']} |"
            )
    else:
        lines.append("No stations currently marked `review`.")

    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fill decision column from proposed_decision in stations candidates CSV."
        )
    )
    parser.add_argument(
        "--candidates",
        default="data/stations_candidates.csv",
        help="Path to stations candidates CSV (default: data/stations_candidates.csv).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to write updated CSV (default: overwrites --candidates in-place).",
    )
    parser.add_argument(
        "--areas",
        default="configs/areas.json",
        help="Path to areas.json for display names (default: configs/areas.json).",
    )
    parser.add_argument(
        "--report",
        default="reports/decision_summary.md",
        help="Path to output markdown report (default: reports/decision_summary.md).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    stats = apply_station_decisions(
        candidates_path=args.candidates,
        output_path=args.output,
        areas_path=args.areas,
        report_path=args.report,
    )
    print("Decision application finished:")
    print(f"  Total candidate rows: {stats['total_rows']}")
    print(f"  Decisions applied:    {stats['applied_count']}")
    print(f"  Rows skipped (non-empty): {stats['skipped_count']}")
    print(f"  Review stations:      {stats['review_stations_count']}")


if __name__ == "__main__":
    main()
