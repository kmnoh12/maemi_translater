from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data-workspace" / "metadata" / "species_catalog.json"
DEFAULT_OUT = ROOT / "data-workspace" / "metadata" / "inat_targeted_public_manifest.csv"
KOREA_PLACE_ID = 6891


def api_json(url: str) -> dict:
    with urlopen(url) as response:
        return json.load(response)


def load_existing_sound_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {row["sound_id"] for row in csv.DictReader(handle)}


def safe_extension(file_url: str) -> str:
    stem = file_url.split("?")[0]
    suffix = Path(stem).suffix.lower()
    return suffix or ".bin"


def build_rows(
    species: dict,
    existing_sound_ids: set[str],
    per_region: int,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    queries = [("korea", KOREA_PLACE_ID), ("world", None)]

    for region_name, place_id in queries:
        page = 1
        while len([r for r in rows if r["region_scope"] == region_name]) < per_region and page <= 10:
            url = (
                "https://api.inaturalist.org/v1/observations"
                f"?taxon_name={quote(species['inat_query_name'])}"
                "&sounds=true"
                "&per_page=100"
                f"&page={page}"
                "&order=desc"
                "&order_by=created_at"
            )
            if place_id:
                url += f"&place_id={place_id}"
            data = api_json(url)
            results = data.get("results", [])
            if not results:
                break

            for obs in results:
                for sound in obs.get("sounds", []):
                    sound_id = str(sound.get("id"))
                    license_code = (sound.get("license_code") or "").strip().lower()
                    file_url = sound.get("file_url")
                    if not license_code or not file_url or sound_id in existing_sound_ids or sound_id in seen:
                        continue
                    ext = safe_extension(file_url)
                    base_name = f"inat_obs{obs['id']}_sound{sound_id}"
                    rows.append(
                        {
                            "species_code": species["species_code"],
                            "common_name_ko": species["common_name_ko"],
                            "scientific_name": species["scientific_name"],
                            "inat_query_name": species["inat_query_name"],
                            "inat_taxon_id": str(species.get("inat_taxon_id", "")),
                            "region_scope": region_name,
                            "observation_id": str(obs["id"]),
                            "sound_id": sound_id,
                            "quality_grade": obs.get("quality_grade") or "",
                            "license_code": license_code,
                            "place_guess": obs.get("place_guess") or "",
                            "observed_on": obs.get("observed_on") or "",
                            "source_url": f"https://www.inaturalist.org/observations/{obs['id']}",
                            "file_url": file_url,
                            "local_raw_path": f"data-workspace/raw_audio/inat_targeted/{species['species_code']}/{base_name}{ext}",
                            "local_derived_path": f"data-workspace/derived_audio/inat_targeted/{species['species_code']}/{base_name}_16k_mono.wav",
                        }
                    )
                    seen.add(sound_id)
                    if len([r for r in rows if r["region_scope"] == region_name]) >= per_region:
                        break
                if len([r for r in rows if r["region_scope"] == region_name]) >= per_region:
                    break
            page += 1
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--species", default="chammaemi,yujimaemi")
    parser.add_argument("--per-region", type=int, default=16)
    parser.add_argument("--existing-inventory", type=Path, default=ROOT / "ml-workspace" / "reports" / "inat_full_inventory.csv")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    target_species = {part.strip() for part in args.species.split(",") if part.strip()}
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    existing_sound_ids = load_existing_sound_ids(args.existing_inventory.resolve())

    rows: list[dict[str, str]] = []
    for species in catalog:
        if species["species_code"] not in target_species:
            continue
        rows.extend(build_rows(species, existing_sound_ids, args.per_region))

    args.out = args.out.resolve()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "species_code",
        "common_name_ko",
        "scientific_name",
        "inat_query_name",
        "inat_taxon_id",
        "region_scope",
        "observation_id",
        "sound_id",
        "quality_grade",
        "license_code",
        "place_guess",
        "observed_on",
        "source_url",
        "file_url",
        "local_raw_path",
        "local_derived_path",
    ]
    with args.out.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {args.out}")
    for species_code in sorted(target_species):
        species_rows = [row for row in rows if row["species_code"] == species_code]
        print(f"{species_code}: total={len(species_rows)}, korea={sum(1 for row in species_rows if row['region_scope']=='korea')}, world={sum(1 for row in species_rows if row['region_scope']=='world')}")


if __name__ == "__main__":
    main()
