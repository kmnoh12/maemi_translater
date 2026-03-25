from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STRICT = ROOT / "data-workspace" / "metadata" / "youtube_manifest_filtered_strict.csv"
DEFAULT_SPECIES = ROOT / "data-workspace" / "metadata" / "youtube_species_search_terms.json"
DEFAULT_OUT = ROOT / "data-workspace" / "metadata" / "youtube_manifest_top200.csv"

CANONICAL_TOKENS = {
    "yujimaemi": ("graptopsaltria", "nigrofuscata", "aburazemi", "유지매미", "アブラゼミ", "油蝉", "油蟬"),
    "chammaemi": ("hyalessa", "maculaticollis", "minminzemi", "minmin", "참매미", "ミンミンゼミ", "鸣鸣蝉", "鳴鳴蟬"),
    "malmaemi": ("cryptotympana", "atrata", "kumazemi", "말매미", "クマゼミ", "熊蝉", "熊蟬", "紅脈熊蟬"),
    "aemaemi": ("meimuna", "opalifera", "tsukutsuku", "애매미", "ツクツクボウシ", "walker", "寒蝉", "寒蟬"),
    "sseureummaemi": ("meimuna", "mongolica", "쓰름매미", "蒙古寒蝉", "蒙古寒蟬"),
    "teolmaemi": ("tanna", "japonensis", "higurashi", "털매미", "ヒグラシ", "暮蝉", "暮蟬", "evening cicada"),
}

GENERIC_PENALTIES = (
    "a very loud cicada",
    "cicada sound",
    "cicada song",
    "cicada call",
    "cicada calling",
    "summer sound",
    "sound of cicadas",
    "chorus",
    "noise artist",
    "free hd sound effect",
)

POSITIVE_SOUND_TOKENS = (
    "울음소리",
    "우는소리",
    "鳴き声",
    "鳴聲",
    "鸣声",
    "叫聲",
    "叫声",
    "chirping",
    "calling",
    "singing",
    "sound",
    "call",
)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_species_terms(path: Path) -> dict[str, list[str]]:
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    terms: dict[str, list[str]] = {}
    for species in CANONICAL_TOKENS:
        seen = set()
        items: list[str] = []
        for source in (CANONICAL_TOKENS[species], config.get("species", {}).get(species, []), config.get("direct_queries", {}).get(species, [])):
            for item in source:
                key = normalize(item)
                if key and key not in seen:
                    seen.add(key)
                    items.append(key)
        terms[species] = items
    return terms


def score_row(row: dict[str, str], species_terms: dict[str, list[str]]) -> tuple[float, str]:
    species_code = row["species_code"]
    title = normalize(row.get("video_title", ""))
    query = normalize(row.get("search_query", ""))
    text = f"{title} || {query}"
    score = 0.0
    reasons: list[str] = []

    canonical_hits = sum(1 for token in CANONICAL_TOKENS[species_code] if normalize(token) in text)
    alias_hits = sum(1 for token in species_terms.get(species_code, []) if token in text)

    score += canonical_hits * 5.0
    if canonical_hits:
        reasons.append(f"canonical:{canonical_hits}")
    score += min(alias_hits, 4) * 2.0
    if alias_hits:
        reasons.append(f"alias:{alias_hits}")

    sound_hits = sum(1 for token in POSITIVE_SOUND_TOKENS if normalize(token) in text)
    score += min(sound_hits, 3) * 1.5
    if sound_hits:
        reasons.append(f"sound:{sound_hits}")

    search_query = normalize(row.get("search_query", ""))
    if any(token in search_query for token in CANONICAL_TOKENS[species_code]):
        score += 2.0
        reasons.append("query_match")

    try:
        duration = float(row.get("duration_seconds") or 0)
    except ValueError:
        duration = 0.0

    if 12 <= duration <= 45:
        score += 4.0
        reasons.append("dur:12-45")
    elif 45 < duration <= 90:
        score += 2.5
        reasons.append("dur:45-90")
    elif 90 < duration <= 180:
        score += 1.0
        reasons.append("dur:90-180")
    elif duration > 180:
        score -= min((duration - 180) / 40.0, 4.0)
        reasons.append("long_penalty")

    generic_hit = next((token for token in GENERIC_PENALTIES if token in title), "")
    if generic_hit:
        score -= 4.0
        reasons.append(f"generic:{generic_hit}")

    # Prefer titles that explicitly name a single species rather than a broad clip.
    if "," in title or "&" in title or " and " in title:
        score -= 1.5
        reasons.append("multi_subject")

    # Small deterministic tie-breaker based on title richness.
    richness = len(set(re.findall(r"[a-z가-힣一-龥ぁ-んァ-ン]+", title)))
    score += min(richness / 20.0, 1.0)

    return score, ",".join(reasons)


def allocate_targets(rows: list[dict[str, str]], total_target: int) -> dict[str, int]:
    counts = Counter(row["species_code"] for row in rows)
    species = sorted(counts)
    floor = total_target // len(species)
    targets = {sp: min(counts[sp], floor) for sp in species}
    remaining = total_target - sum(targets.values())

    while remaining > 0:
        candidates = sorted(
            (sp for sp in species if targets[sp] < counts[sp]),
            key=lambda sp: (counts[sp] - targets[sp], counts[sp]),
            reverse=True,
        )
        if not candidates:
            break
        for sp in candidates:
            if remaining <= 0:
                break
            if targets[sp] < counts[sp]:
                targets[sp] += 1
                remaining -= 1
    return targets


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Select a high-confidence balanced YouTube subset for retraining.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_STRICT)
    parser.add_argument("--species-terms", type=Path, default=DEFAULT_SPECIES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--target-count", type=int, default=200)
    args = parser.parse_args()

    rows = load_rows(args.manifest.resolve())
    species_terms = load_species_terms(args.species_terms.resolve())

    scored: list[dict[str, str]] = []
    for row in rows:
        updated = dict(row)
        score, reason = score_row(updated, species_terms)
        updated["selection_score"] = f"{score:.2f}"
        updated["selection_reason"] = reason
        scored.append(updated)

    targets = allocate_targets(scored, args.target_count)
    selected: list[dict[str, str]] = []
    for species_code, target in targets.items():
        subset = [row for row in scored if row["species_code"] == species_code]
        subset.sort(key=lambda row: (-float(row["selection_score"]), normalize(row.get("video_title", ""))))
        selected.extend(subset[:target])

    selected.sort(key=lambda row: (row["species_code"], -float(row["selection_score"]), normalize(row.get("video_title", ""))))
    fieldnames = list(scored[0].keys()) if scored else []
    for extra in ("selection_score", "selection_reason"):
        if extra not in fieldnames:
            fieldnames.append(extra)

    write_csv(args.out.resolve(), selected, fieldnames)

    print(f"Selected {len(selected)} rows -> {args.out.resolve()}")
    print("Targets by species:")
    for species_code in sorted(targets):
        print(f"  {species_code}: {targets[species_code]}")


if __name__ == "__main__":
    main()
