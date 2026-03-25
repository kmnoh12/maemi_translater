from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    inventory_path = ROOT / "ml-workspace" / "reports" / "inat_full_inventory.csv"
    out_json = ROOT / "ml-workspace" / "reports" / "korea_subset_report.json"
    out_md = ROOT / "ml-workspace" / "reports" / "korea_subset_report.md"

    rows = [row for row in load_csv(inventory_path) if row.get("is_korea", "").lower() == "true"]

    species_counts = Counter()
    duration_by_species = defaultdict(float)
    quality_counts = Counter()
    license_counts = Counter()

    for row in rows:
        species_counts[row["species_code"]] += 1
        duration_by_species[row["species_code"]] += float(row["duration_sec"])
        quality_counts[row.get("quality_grade", "") or "unknown"] += 1
        license_counts[row.get("license_code", "")] += 1

    payload = {
        "row_count": len(rows),
        "species_counts": dict(species_counts),
        "duration_by_species": {k: round(v, 2) for k, v in duration_by_species.items()},
        "quality_counts": dict(quality_counts),
        "license_counts": dict(license_counts),
    }

    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Korea Subset Report",
        "",
        f"- Korea rows: {payload['row_count']}",
        "",
        "## Species counts",
    ]
    for species, count in sorted(payload["species_counts"].items()):
        lines.append(f"- {species}: {count}")
    lines.extend(["", "## Duration by species"])
    for species, duration in sorted(payload["duration_by_species"].items()):
        lines.append(f"- {species}: {duration} sec")

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()
