from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_YOUTUBE = ROOT / "data-workspace" / "metadata" / "youtube_manifest.csv"
DEFAULT_SPECIES = ROOT / "data-workspace" / "metadata" / "youtube_species_search_terms.json"
DEFAULT_FILTERED = ROOT / "data-workspace" / "metadata" / "youtube_manifest_filtered.csv"

HARD_BLOCKLIST = (
    "animal crossing",
    "anime",
    "asmr",
    "bgm",
    "body built for song",
    "brain",
    "brood x",
    "cicada 3301",
    "cover",
    "creditless",
    "drama",
    "eating",
    "ending",
    "game",
    "gou",
    "higurashi no naku koro ni",
    "interview",
    "jumpscare",
    "lyrics",
    "main theme",
    "music",
    "opening",
    "ost",
    "podcast",
    "reaction",
    "rei",
    "remix",
    "sotsu",
    "sound effect",
    "theme song",
    "when they cry",
)

OFF_TARGET_TOKENS = (
    "aleeta",
    "arcyptera",
    "diceroprocta",
    "gryllus",
    "hexacentrus",
    "katydid",
    "macrotristria",
    "magicicada",
    "natula",
    "neotibicen",
    "pomponia",
    "teleogryllus",
    "tibicen",
)

SPECIES_CANONICAL = {
    "yujimaemi": ("graptopsaltria", "nigrofuscata", "aburazemi", "유지매미", "アブラゼミ", "油蝉", "油蟬"),
    "chammaemi": ("hyalessa", "maculaticollis", "minmin", "minminzemi", "minmin-zemi", "참매미", "ミンミンゼミ", "鸣鸣蝉", "鳴鳴蟬"),
    "malmaemi": ("cryptotympana", "atrata", "말매미", "クマゼミ", "kumazemi", "熊蝉", "熊蟬", "紅脈熊蟬"),
    "aemaemi": ("meimuna", "opalifera", "애매미", "ツクツクボウシ", "tsukutsuku", "walker", "寒蝉", "寒蟬"),
    "sseureummaemi": ("meimuna", "mongolica", "쓰름매미", "mongolian cicada", "蒙古寒蝉", "蒙古寒蟬"),
    "teolmaemi": ("tanna", "japonensis", "털매미", "ヒグラシ", "higurashi", "暮蝉", "暮蟬", "evening cicada"),
}

SPECIES_MISMATCH_TOKENS = {
    "yujimaemi": ("hyalessa", "maculaticollis", "cryptotympana", "atrata", "opalifera", "mongolica", "tanna", "japonensis", "minminzemi", "kumazemi", "ツクツクボウシ", "ヒグラシ"),
    "chammaemi": ("graptopsaltria", "nigrofuscata", "cryptotympana", "atrata", "opalifera", "mongolica", "tanna", "japonensis", "aburazemi", "kumazemi", "ツクツクボウシ", "ヒグラシ"),
    "malmaemi": ("graptopsaltria", "nigrofuscata", "hyalessa", "maculaticollis", "opalifera", "mongolica", "tanna", "japonensis", "aburazemi", "minminzemi", "ツクツクボウシ", "ヒグラシ"),
    "aemaemi": ("graptopsaltria", "nigrofuscata", "hyalessa", "maculaticollis", "cryptotympana", "atrata", "mongolica", "tanna", "japonensis", "aburazemi", "minminzemi", "kumazemi", "ヒグラシ"),
    "sseureummaemi": ("graptopsaltria", "nigrofuscata", "hyalessa", "maculaticollis", "cryptotympana", "atrata", "opalifera", "tanna", "japonensis", "aburazemi", "minminzemi", "kumazemi", "ツクツクボウシ", "ヒグラシ"),
    "teolmaemi": ("graptopsaltria", "nigrofuscata", "hyalessa", "maculaticollis", "cryptotympana", "atrata", "opalifera", "mongolica", "aburazemi", "minminzemi", "kumazemi", "ツクツクボウシ"),
}


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_species_terms(path: Path) -> dict[str, list[str]]:
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    terms: dict[str, list[str]] = {}
    for species in SPECIES_CANONICAL:
        combined: list[str] = []
        combined.extend(SPECIES_CANONICAL[species])
        combined.extend(config.get("species", {}).get(species, []))
        combined.extend(config.get("direct_queries", {}).get(species, []))
        seen = set()
        normalized = []
        for item in combined:
            key = item.strip().lower()
            if key and key not in seen:
                seen.add(key)
                normalized.append(key)
        terms[species] = normalized
    return terms


def contains_any(text: str, tokens: tuple[str, ...] | list[str]) -> str:
    for token in tokens:
        if token and token in text:
            return token
    return ""


def evaluate_row(row: dict[str, str], species_terms: dict[str, list[str]]) -> tuple[str, str]:
    status = (row.get("status") or "").strip().lower()
    if status != "downloaded":
        return "rejected", "not_downloaded"

    derived = (row.get("local_derived_path") or "").strip()
    if not derived or not (ROOT / derived).exists():
        return "rejected", "missing_derived"

    raw = (row.get("local_raw_path") or "").strip()
    if not raw or not (ROOT / raw).exists():
        return "rejected", "missing_raw"

    title = (row.get("video_title") or "").lower()
    query = (row.get("search_query") or "").lower()
    merged = f"{title} || {query}"

    try:
        duration = int(float(row.get("duration_seconds") or 0))
    except ValueError:
        duration = 0

    if duration < 8:
        return "rejected", "too_short"
    if duration > 360:
        return "rejected", "too_long"

    blocked = contains_any(merged, HARD_BLOCKLIST)
    if blocked:
        return "rejected", f"blocked:{blocked}"

    off_target = contains_any(merged, OFF_TARGET_TOKENS)
    if off_target:
        return "rejected", f"off_target:{off_target}"

    species_code = row.get("species_code", "").strip()
    positive_terms = species_terms.get(species_code, [])
    positive_hit = contains_any(merged, positive_terms)
    mismatch_hit = contains_any(merged, SPECIES_MISMATCH_TOKENS.get(species_code, ()))

    if mismatch_hit:
        return "rejected", f"species_mismatch:{mismatch_hit}"

    if not positive_hit:
        return "rejected", "weak_species_signal"

    generic_noise = ("cicada song", "cicada sound", "cicada call", "summer sound", "sound of cicadas")
    if contains_any(title, generic_noise) and not contains_any(title, SPECIES_CANONICAL[species_code]):
        return "rejected", "too_generic"

    return "downloaded", "approved_strict"


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggressively reject low-quality YouTube rows and rebuild the strict filtered manifest.")
    parser.add_argument("--youtube-manifest", type=Path, default=DEFAULT_YOUTUBE)
    parser.add_argument("--species-terms", type=Path, default=DEFAULT_SPECIES)
    parser.add_argument("--filtered-out", type=Path, default=DEFAULT_FILTERED)
    args = parser.parse_args()

    manifest_path = args.youtube_manifest.resolve()
    filtered_path = args.filtered_out.resolve()
    rows = load_rows(manifest_path)
    species_terms = load_species_terms(args.species_terms.resolve())

    fieldnames = list(rows[0].keys())
    for extra in ("rejection_reason", "quality_flag"):
        if extra not in fieldnames:
            fieldnames.append(extra)

    kept_rows: list[dict[str, str]] = []
    reason_counts: Counter[str] = Counter()

    for row in rows:
        new_status, reason = evaluate_row(row, species_terms)
        row["status"] = new_status
        row["rejection_reason"] = "" if new_status == "downloaded" else reason
        row["quality_flag"] = "approved_strict" if new_status == "downloaded" else "rejected"
        reason_counts[reason] += 1
        if new_status == "downloaded":
            kept_rows.append(row.copy())

    write_csv(manifest_path, rows, fieldnames)
    write_csv(filtered_path, kept_rows, fieldnames)

    print(f"Updated source manifest: {manifest_path}")
    print(f"Strict filtered rows kept: {len(kept_rows)} / {len(rows)}")
    print("Top rejection reasons:")
    for reason, count in reason_counts.most_common(15):
        print(f"  {reason}: {count}")


if __name__ == "__main__":
    main()
