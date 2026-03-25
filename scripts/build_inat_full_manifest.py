from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data-workspace" / "metadata" / "species_catalog.json"
DEFAULT_OUT = ROOT / "data-workspace" / "metadata" / "inat_full_manifest.csv"


def api_json(url: str) -> dict:
    with urlopen(url) as response:
        return json.load(response)


def safe_extension(file_url: str) -> str:
    stem = file_url.split("?")[0]
    suffix = Path(stem).suffix.lower()
    return suffix or ".bin"


def fetch_species_rows(species: dict, per_page: int, max_pages: int) -> list[dict[str, str]]:
    taxon_id = species["inat_taxon_id"]
    rows: list[dict[str, str]] = []
    seen_sound_ids: set[str] = set()

    for page in range(1, max_pages + 1):
        url = (
            "https://api.inaturalist.org/v1/observations"
            f"?taxon_id={taxon_id}"
            "&sounds=true"
            f"&per_page={per_page}"
            f"&page={page}"
            "&order=desc"
            "&order_by=created_at"
        )
        data = api_json(url)
        results = data.get("results", [])
        if not results:
            break

        for obs in results:
            place_guess = obs.get("place_guess") or ""
            is_korea = (
                "South Korea" in place_guess
                or "대한민국" in place_guess
                or ", KR" in place_guess
                or "KR-" in place_guess
            )
            for sound in obs.get("sounds", []):
                sound_id = str(sound.get("id"))
                license_code = (sound.get("license_code") or "").strip().lower()
                file_url = sound.get("file_url")
                if sound_id in seen_sound_ids:
                    continue
                if not license_code:
                    continue
                if not file_url:
                    continue
                ext = safe_extension(file_url)
                base_name = f"inat_obs{obs['id']}_sound{sound_id}"
                rows.append(
                    {
                        "species_code": species["species_code"],
                        "common_name_ko": species["common_name_ko"],
                        "scientific_name": species["scientific_name"],
                        "inat_query_name": species["inat_query_name"],
                        "inat_taxon_id": str(species["inat_taxon_id"]),
                        "observation_id": str(obs["id"]),
                        "sound_id": sound_id,
                        "quality_grade": obs.get("quality_grade") or "",
                        "license_code": license_code,
                        "place_guess": place_guess,
                        "observed_on": obs.get("observed_on") or "",
                        "source_url": f"https://www.inaturalist.org/observations/{obs['id']}",
                        "file_url": file_url,
                        "is_korea": "true" if is_korea else "false",
                        "local_raw_path": f"data-workspace/raw_audio/inat_full/{species['species_code']}/{base_name}{ext}",
                        "local_derived_path": f"data-workspace/derived_audio/inat_full/{species['species_code']}/{base_name}_16k_mono.wav",
                    }
                )
                seen_sound_ids.add(sound_id)

        total_results = data.get("total_results") or 0
        if page * per_page >= total_results:
            break

    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-page", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    rows: list[dict[str, str]] = []
    for species in catalog:
        rows.extend(fetch_species_rows(species, per_page=args.per_page, max_pages=args.max_pages))

    rows.sort(key=lambda row: (row["species_code"], row["is_korea"] != "true", row["observation_id"], row["sound_id"]))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "species_code",
        "common_name_ko",
        "scientific_name",
        "inat_query_name",
        "inat_taxon_id",
        "observation_id",
        "sound_id",
        "quality_grade",
        "license_code",
        "place_guess",
        "observed_on",
        "source_url",
        "file_url",
        "is_korea",
        "local_raw_path",
        "local_derived_path",
    ]
    with args.out.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
