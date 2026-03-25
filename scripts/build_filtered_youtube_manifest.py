from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_YOUTUBE = ROOT / "data-workspace" / "metadata" / "youtube_manifest.csv"
DEFAULT_SPECIES = ROOT / "data-workspace" / "metadata" / "youtube_species_search_terms.json"
DEFAULT_OUT = ROOT / "data-workspace" / "metadata" / "youtube_manifest_filtered.csv"

GLOBAL_BLOCKLIST = (
    "asmr",
    "ost",
    "opening",
    "ending",
    "cover",
    "piano",
    "bgm",
    "drama",
    "anime",
    "game",
    "higurashi no naku koro ni",
    "when they cry",
    "cicada 3301",
    "해부",
    "특징",
    "만들기",
    "먹는",
    "수액",
    "reaction",
    "interview",
    "podcast",
    "music",
    "song",
    "rap",
    "scares",
    "jumpscare",
    "ost -",
)


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_species_terms(path: Path) -> dict[str, list[str]]:
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    terms: dict[str, list[str]] = {}
    for species, aliases in config.get("species", {}).items():
        direct = config.get("direct_queries", {}).get(species, [])
        normalized = []
        seen = set()
        for item in list(aliases) + list(direct):
            key = item.strip().lower()
            if key and key not in seen:
                seen.add(key)
                normalized.append(key)
        terms[species] = normalized
    return terms


def should_keep(row: dict[str, str], species_terms: dict[str, list[str]]) -> tuple[bool, str]:
    status = (row.get("status") or "").strip().lower()
    if status != "downloaded":
        return False, "not_downloaded"

    derived = (row.get("local_derived_path") or "").strip()
    if not derived or not (ROOT / derived).exists():
        return False, "missing_derived"

    title = (row.get("video_title") or "").lower()
    duration = 0
    try:
        duration = int(float(row.get("duration_seconds") or 0))
    except ValueError:
        duration = 0

    if duration < 8:
        return False, "too_short"
    if duration > 420:
        return False, "too_long"

    for term in GLOBAL_BLOCKLIST:
        if term in title:
            return False, f"blocked:{term}"

    species_code = row.get("species_code", "")
    aliases = species_terms.get(species_code, [])
    if not any(alias in title for alias in aliases):
        if "cicada" not in title and "매미" not in title and "蝉" not in title and "蟬" not in title and "セミ" not in title:
            return False, "no_species_signal"

    return True, ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter YouTube cicada manifest to a stricter training subset.")
    parser.add_argument("--youtube-manifest", type=Path, default=DEFAULT_YOUTUBE)
    parser.add_argument("--species-terms", type=Path, default=DEFAULT_SPECIES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    rows = load_rows(args.youtube_manifest.resolve())
    species_terms = load_species_terms(args.species_terms.resolve())
    kept: list[dict[str, str]] = []
    rejected = 0
    for row in rows:
        keep, _ = should_keep(row, species_terms)
        if keep:
            kept.append(row)
        else:
            rejected += 1

    args.out = args.out.resolve()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(kept)

    print(f"Wrote {len(kept)} filtered rows to {args.out}")
    print(f"Rejected {rejected} rows")


if __name__ == "__main__":
    main()
