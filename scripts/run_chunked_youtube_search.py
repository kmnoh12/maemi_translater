from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "data-workspace" / "metadata" / "youtube_species_search_terms.json"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass


def load_species_catalog() -> list[dict]:
    path = ROOT / "data-workspace" / "metadata" / "species_catalog.json"
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_search_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def generate_queries(config: dict, species_code: str, scientific_name: str) -> list[str]:
    aliases = list(config.get("species", {}).get(species_code, []))
    suffixes = [s.strip() for s in config.get("search_suffixes", []) if s and s.strip()]
    direct_queries = [
        q.strip()
        for q in config.get("direct_queries", {}).get(species_code, [])
        if q and q.strip()
    ]
    if scientific_name and scientific_name not in aliases:
        aliases.insert(0, scientific_name)

    seen: set[str] = set()
    queries: list[str] = []
    for alias in aliases:
        alias = alias.strip()
        if not alias:
            continue
        for query in [alias] + [f"{alias} {suffix}" for suffix in suffixes]:
            key = query.lower()
            if key in seen:
                continue
            seen.add(key)
            queries.append(query)

    for query in direct_queries:
        key = query.lower()
        if key in seen:
            continue
        seen.add(key)
        queries.append(query)
    return queries


def run_query(species_code: str, query: str, max_results: int) -> int:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "build_youtube_manifest.py"),
        "--species",
        species_code,
        "--search",
        query,
        "--max-results",
        str(max_results),
    ]
    proc = subprocess.run(cmd, cwd=ROOT, text=True)
    return proc.returncode


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run chunked YouTube search query batches so manifest growth survives timeouts."
    )
    parser.add_argument(
        "--species",
        action="append",
        help="Target species_code. Repeat to specify multiple. Default: all 6 species.",
    )
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument(
        "--query-limit",
        type=int,
        default=20,
        help="Maximum queries per species for this run. Default 20.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
    )
    args = parser.parse_args()

    catalog = load_species_catalog()
    config = load_search_config(args.config.resolve())
    wanted = set(args.species or [item["species_code"] for item in catalog])

    total_runs = 0
    failures = 0
    for item in catalog:
        species_code = item["species_code"]
        if species_code not in wanted:
            continue
        queries = generate_queries(config, species_code, item.get("scientific_name", ""))
        limited_queries = queries[: args.query_limit]
        print(f"[SPECIES] {species_code} queries={len(limited_queries)}/{len(queries)}")
        for idx, query in enumerate(limited_queries, 1):
            print(f"[QUERY] {species_code} {idx}/{len(limited_queries)} :: {query}")
            code = run_query(species_code, query, args.max_results)
            total_runs += 1
            if code != 0:
                failures += 1
                print(f"[WARN] query failed with exit={code}")

    print(f"Completed query runs: {total_runs}, failures: {failures}")


if __name__ == "__main__":
    main()
