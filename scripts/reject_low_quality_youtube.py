from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "data-workspace" / "metadata" / "youtube_manifest.csv"
DEFAULT_SPECIES = ROOT / "data-workspace" / "metadata" / "youtube_species_search_terms.json"
DEFAULT_STRICT_OUT = ROOT / "data-workspace" / "metadata" / "youtube_manifest_filtered_strict.csv"

FIRST_PASS_BLOCKLIST = (
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
    "podcast",
    "interview",
    "reaction",
    "music",
    "rap",
    "jumpscare",
    "animal crossing",
    "higurashi",
    "when they cry",
    "cicada 3301",
    "free hd sound effect",
    "sound effect",
    "effect #",
    "vlog",
    "브이로그",
    "공략",
    "amv",
    "official lyric video",
)

FOREIGN_SPECIES_BLOCKLIST = (
    "diceroprocta",
    "tibicen",
    "neotibicen",
    "magicicada",
    "aleeta",
    "macrotristria",
    "cyclochila",
    "kikihia",
    "psaltoda",
    "mogannia",
    "euterpnosia",
    "macrosemia",
    "pomponia",
    "meimuna iwasakii",
    "meimuna oshimensis",
    "graptopsaltria bimaculata",
    "cryptotympana facialis",
    "cryptotympana takasagona",
    "cryptotympana kotoshoensis",
    "cryptotympana holsti",
    "cryptotympana recta",
)

BEHAVIOR_ONLY_BLOCKLIST = (
    "emergence",
    "emerging",
    "eclosion",
    "oviposition",
    "molt",
    "molting",
    "molted",
    "capture",
    "captured",
    "shell",
    "exuvia",
    "산란",
    "우화",
    "탈피",
    "허물",
    "捕獲",
    "羽化",
)

STRICT_TITLE_BLOCKLIST = (
    "album mix",
    "lyrics",
    "翻唱",
    "cover",
    "official lyric video",
    "19금",
    "해부",
    "채집",
    "捕獲失敗",
    "urinating",
    "오줌",
    "flying away",
    "날아감",
    "求愛",
    "절명",
)

STRONG_SOUND_TOKENS = (
    "울음",
    "울음소리",
    "우는 소리",
    "鳴き",
    "鳴声",
    "鳴聲",
    "蝉鸣",
    "蟬鳴",
    "蝉叫",
    "cicada sound",
    "cicada call",
    "cicada calling",
    "singing",
)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def split_variants(text: str) -> list[str]:
    base = normalize(text)
    if not base:
        return []
    items = {base}
    if "(" in base:
        items.add(base.split("(", 1)[0].strip())
    if "/" in base:
        items.update(part.strip() for part in base.split("/") if part.strip())
    return [item for item in items if len(item) >= 2]


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_species_terms(path: Path) -> dict[str, list[str]]:
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    terms: dict[str, list[str]] = {}
    generic_tokens = (
        "cicada sound",
        "cicada song",
        "cicada call",
        "매미 소리",
        "매미 우는소리",
        "鳴き声",
        "蝉鸣",
        "蟬鳴聲",
        "蝉叫声",
    )
    for species, aliases in config.get("species", {}).items():
        candidates: list[str] = []
        for item in list(aliases) + list(config.get("direct_queries", {}).get(species, [])):
            candidates.extend(split_variants(item))
        seen = set()
        normalized: list[str] = []
        for item in candidates:
            if any(token in item for token in generic_tokens):
                continue
            if item not in seen:
                seen.add(item)
                normalized.append(item)
        terms[species] = normalized
    return terms


def has_any(text: str, terms: tuple[str, ...] | list[str]) -> bool:
    return any(term in text for term in terms)


def find_cross_species_hits(title: str, species_code: str, species_terms: dict[str, list[str]]) -> list[str]:
    hits: list[str] = []
    for other_code, terms in species_terms.items():
        if other_code == species_code:
            continue
        if any(term in title for term in terms if len(term) >= 3):
            hits.append(other_code)
    return hits


def first_pass_reason(row: dict[str, str], species_terms: dict[str, list[str]]) -> str:
    title = normalize(row.get("video_title", ""))
    query = normalize(row.get("search_query", ""))
    text = f"{title} || {query}"
    species_code = row.get("species_code", "")
    own_terms = species_terms.get(species_code, [])
    own_hit = any(term in text for term in own_terms)
    cross_hits = find_cross_species_hits(title, species_code, species_terms)

    try:
        duration = float(row.get("duration_seconds") or 0)
    except ValueError:
        duration = 0

    if duration < 8:
        return "too_short"
    if duration > 360:
        return "too_long"
    if has_any(text, FIRST_PASS_BLOCKLIST):
        return "blocked_term"
    if has_any(title, FOREIGN_SPECIES_BLOCKLIST):
        return "foreign_species"
    if has_any(title, BEHAVIOR_ONLY_BLOCKLIST) and not has_any(title, STRONG_SOUND_TOKENS):
        return "behavior_only"
    if cross_hits and not own_hit:
        return f"species_mismatch:{','.join(cross_hits)}"
    return ""


def strict_keep_reason(row: dict[str, str], species_terms: dict[str, list[str]]) -> str:
    title = normalize(row.get("video_title", ""))
    query = normalize(row.get("search_query", ""))
    text = f"{title} || {query}"
    species_code = row.get("species_code", "")
    own_terms = species_terms.get(species_code, [])

    try:
        duration = float(row.get("duration_seconds") or 0)
    except ValueError:
        duration = 0

    if duration > 240:
        return "strict_too_long"
    if has_any(title, STRICT_TITLE_BLOCKLIST):
        return "strict_blocked_term"
    if not any(term in text for term in own_terms):
        return "strict_need_own_alias"
    if "cicada song" in title and not has_any(title, STRONG_SOUND_TOKENS):
        return "strict_generic_song"
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Reject low-quality YouTube rows in-place and write a stricter filtered manifest.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--species-terms", type=Path, default=DEFAULT_SPECIES)
    parser.add_argument("--strict-out", type=Path, default=DEFAULT_STRICT_OUT)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    rows = load_rows(manifest_path)
    species_terms = load_species_terms(args.species_terms.resolve())

    fieldnames = list(rows[0].keys()) if rows else []
    if "rejected_reason" not in fieldnames:
        fieldnames.append("rejected_reason")
    if "strict_filter_reason" not in fieldnames:
        fieldnames.append("strict_filter_reason")

    strict_rows: list[dict[str, str]] = []
    rejected = 0
    strict_rejected = 0
    for row in rows:
        updated = dict(row)
        updated.setdefault("rejected_reason", "")
        updated.setdefault("strict_filter_reason", "")

        if normalize(updated.get("status", "")) == "downloaded":
            reject_reason = first_pass_reason(updated, species_terms)
            if reject_reason:
                updated["status"] = "rejected"
                updated["rejected_reason"] = reject_reason
                updated["strict_filter_reason"] = ""
                rejected += 1
            else:
                updated["rejected_reason"] = ""
                strict_reason = strict_keep_reason(updated, species_terms)
                updated["strict_filter_reason"] = strict_reason
                if not strict_reason:
                    strict_rows.append(updated)
                else:
                    strict_rejected += 1
        row.clear()
        row.update(updated)

    with manifest_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    strict_out = args.strict_out.resolve()
    strict_out.parent.mkdir(parents=True, exist_ok=True)
    with strict_out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(strict_rows)

    print(f"Updated manifest: {manifest_path}")
    print(f"Rejected in-place: {rejected}")
    print(f"Strict filtered rows: {len(strict_rows)}")
    print(f"Strict filtered out: {strict_rejected}")


if __name__ == "__main__":
    main()
