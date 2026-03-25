from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def bucket_duration(duration: float) -> str:
    if duration < 5:
        return "<5s"
    if duration < 15:
        return "5-15s"
    if duration < 30:
        return "15-30s"
    if duration < 60:
        return "30-60s"
    return "60s+"


def main() -> None:
    inventory_path = ROOT / "ml-workspace" / "reports" / "inat_full_inventory.csv"
    duplicates_path = ROOT / "ml-workspace" / "reports" / "inat_full_hash_duplicates.csv"
    report_json_path = ROOT / "ml-workspace" / "reports" / "dataset_health_report.json"
    report_md_path = ROOT / "ml-workspace" / "reports" / "dataset_health_report.md"

    rows = load_csv(inventory_path)
    duplicates = load_csv(duplicates_path)

    by_species = defaultdict(lambda: {
        "files": 0,
        "korea": 0,
        "duration_sec": 0.0,
        "licenses": Counter(),
        "quality": Counter(),
        "duration_buckets": Counter(),
    })
    quality_counter = Counter()
    license_counter = Counter()
    duration_bucket_counter = Counter()

    for row in rows:
        species = row["species_code"]
        duration = float(row["duration_sec"])
        bucket = bucket_duration(duration)
        by_species[species]["files"] += 1
        by_species[species]["duration_sec"] += duration
        by_species[species]["licenses"][row.get("license_code", "")] += 1
        by_species[species]["quality"][row.get("quality_grade", "") or "unknown"] += 1
        by_species[species]["duration_buckets"][bucket] += 1
        if row.get("is_korea", "").lower() == "true":
            by_species[species]["korea"] += 1
        quality_counter[row.get("quality_grade", "") or "unknown"] += 1
        license_counter[row.get("license_code", "")] += 1
        duration_bucket_counter[bucket] += 1

    duplicate_groups = len({row["sha256"] for row in duplicates})

    payload = {
        "inventory_rows": len(rows),
        "duplicate_groups": duplicate_groups,
        "licenses": dict(license_counter),
        "quality": dict(quality_counter),
        "duration_buckets": dict(duration_bucket_counter),
        "species": {
            species: {
                "files": stats["files"],
                "korea": stats["korea"],
                "duration_sec": round(stats["duration_sec"], 2),
                "licenses": dict(stats["licenses"]),
                "quality": dict(stats["quality"]),
                "duration_buckets": dict(stats["duration_buckets"]),
            }
            for species, stats in sorted(by_species.items())
        },
    }
    report_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Dataset Health Report",
        "",
        f"- Inventory rows: {payload['inventory_rows']}",
        f"- Duplicate groups: {payload['duplicate_groups']}",
        "",
        "## Duration buckets",
    ]
    for bucket, count in payload["duration_buckets"].items():
        lines.append(f"- {bucket}: {count}")
    lines.extend(["", "## Quality labels"])
    for quality, count in payload["quality"].items():
        lines.append(f"- {quality}: {count}")
    lines.extend(["", "## Species summary"])
    for species, stats in payload["species"].items():
        lines.append(
            f"- {species}: files {stats['files']}, korea {stats['korea']}, duration {stats['duration_sec']} sec"
        )
    report_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {report_json_path}")
    print(f"Wrote {report_md_path}")


if __name__ == "__main__":
    main()
