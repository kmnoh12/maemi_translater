from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "data-workspace" / "metadata" / "youtube_manifest.csv"


@dataclass(frozen=True)
class Shard:
    species: str
    path: Path
    count: int


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def shard_rows(rows: list[dict[str, str]], include_failed: bool) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        status = (row.get("status") or "").strip().lower()
        if status == "downloaded":
            continue
        if status == "failed" and not include_failed:
            continue
        species = (row.get("species_code") or "unknown").strip() or "unknown"
        grouped[species].append(row)
    return grouped


def build_shards(
    grouped: dict[str, list[dict[str, str]]],
    temp_dir: Path,
    fieldnames: list[str],
) -> list[Shard]:
    shards: list[Shard] = []
    for species, species_rows in grouped.items():
        shard_path = temp_dir / f"{species}.csv"
        write_rows(shard_path, species_rows, fieldnames)
        shards.append(Shard(species=species, path=shard_path, count=len(species_rows)))
    shards.sort(key=lambda shard: (-shard.count, shard.species))
    return shards


def run_worker(
    species: str,
    shard_manifest: Path,
    retry_failed: bool,
    force: bool,
) -> subprocess.Popen[str]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "download_youtube_audio.py"),
        "--manifest",
        str(shard_manifest),
        "--species",
        species,
    ]
    if retry_failed:
        cmd.append("--retry-failed")
    if force:
        cmd.append("--force")
    return subprocess.Popen(cmd, cwd=ROOT, text=True)


def merge_back(
    main_manifest: Path,
    shard_paths: list[Path],
    fieldnames: list[str],
) -> None:
    rows = load_rows(main_manifest)
    by_video_id = {row.get("video_id", ""): row for row in rows}

    for shard_path in shard_paths:
        for shard_row in load_rows(shard_path):
            video_id = shard_row.get("video_id", "")
            if not video_id or video_id not in by_video_id:
                continue
            target = by_video_id[video_id]
            target["status"] = shard_row.get("status", target.get("status", ""))
            target["download_date"] = shard_row.get("download_date", target.get("download_date", ""))

    write_rows(main_manifest, rows, fieldnames)


def print_plan(shards: list[Shard], workers: int) -> None:
    total = sum(shard.count for shard in shards)
    print(f"Pending rows: {total}")
    print(f"Workers: {workers}")
    for shard in shards:
        print(f"  {shard.species}: {shard.count}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run YouTube audio downloads in parallel using per-species manifest shards."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Maximum parallel species workers to run at once. Default 4.",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Include failed rows in the shards so they are retried.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Pass through force mode to each worker.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned shard distribution and exit without downloading.",
    )
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    if args.workers < 1:
        raise SystemExit("--workers must be >= 1")

    rows = load_rows(manifest_path)
    fieldnames = list(rows[0].keys()) if rows else []
    grouped = shard_rows(rows, include_failed=args.retry_failed)
    if not grouped:
        print("No pending shard work found.")
        return

    temp_dir = Path(tempfile.mkdtemp(prefix="youtube_shards_", dir=ROOT))
    shards: list[Shard] = []

    try:
        shards = build_shards(grouped, temp_dir, fieldnames)
        print_plan(shards, args.workers)
        if args.dry_run:
            return

        queue = list(shards)
        running: list[tuple[Shard, subprocess.Popen[str]]] = []

        while queue or running:
            while queue and len(running) < args.workers:
                shard = queue.pop(0)
                proc = run_worker(
                    species=shard.species,
                    shard_manifest=shard.path,
                    retry_failed=args.retry_failed,
                    force=args.force,
                )
                print(f"[START] {shard.species} count={shard.count} pid={proc.pid}")
                running.append((shard, proc))

            next_running: list[tuple[Shard, subprocess.Popen[str]]] = []
            for shard, proc in running:
                code = proc.poll()
                if code is None:
                    next_running.append((shard, proc))
                    continue
                print(f"[DONE] {shard.species} exit={code}")
            running = next_running
            if running:
                time.sleep(1)

        merge_back(manifest_path, [shard.path for shard in shards], fieldnames)
        print(f"Merged shard status updates into {manifest_path}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
