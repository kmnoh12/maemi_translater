from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "data-workspace" / "metadata" / "youtube_manifest.csv"
DEFAULT_REPORT_MD = ROOT / "docs" / "youtube_collection_report.md"
DEFAULT_REPORT_JSON = ROOT / "docs" / "youtube_collection_report.json"

DEFAULT_TITLE_BLACKLIST = (
    "shorts",
    "asmr",
    "music",
    "remix",
    "cover",
    "podcast",
    "interview",
    "reaction",
    "compilation",
)


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def duration_bucket(seconds: float) -> str:
    if seconds < 5:
        return "<5s"
    if seconds < 15:
        return "5-15s"
    if seconds < 30:
        return "15-30s"
    if seconds < 60:
        return "30-60s"
    if seconds < 180:
        return "1-3m"
    if seconds < 600:
        return "3-10m"
    return "10m+"


def is_suspicious_title(title: str, blacklist_terms: tuple[str, ...]) -> str:
    lower = title.lower()
    for term in blacklist_terms:
        if term and term in lower:
            return term
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize the YouTube cicada collection manifest and highlight suspicious rows."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_REPORT_MD)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument(
        "--title-blacklist",
        type=str,
        default=",".join(DEFAULT_TITLE_BLACKLIST),
        help="Comma-separated title terms to flag as suspicious.",
    )
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")

    rows = load_rows(manifest_path)
    blacklist_terms = tuple(
        term.strip().lower() for term in args.title_blacklist.split(",") if term.strip()
    )

    counts_by_species = Counter()
    status_counter = Counter()
    duration_buckets = Counter()
    raw_exists = 0
    derived_exists = 0
    missing_raw = 0
    missing_derived = 0
    long_rows = 0
    short_rows = 0
    suspicious_rows: list[dict[str, str]] = []
    duplicate_video_ids: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        species = row.get("species_code", "") or "unknown"
        status = (row.get("status") or "").strip().lower() or "unknown"
        counts_by_species[species] += 1
        status_counter[status] += 1

        raw_path = ROOT / row["local_raw_path"]
        derived_path = ROOT / row["local_derived_path"]
        raw_ok = raw_path.exists()
        derived_ok = derived_path.exists()
        if raw_ok:
            raw_exists += 1
        else:
            missing_raw += 1
        if derived_ok:
            derived_exists += 1
        else:
            missing_derived += 1

        duration = parse_float(row.get("duration_seconds", ""))
        if duration is not None:
            duration_buckets[duration_bucket(duration)] += 1
            if duration < 5:
                short_rows += 1
            if duration > 600:
                long_rows += 1

        title = row.get("video_title", "")
        suspicious_reason = is_suspicious_title(title, blacklist_terms)
        if suspicious_reason or status != "downloaded" or not raw_ok or not derived_ok:
            suspicious_rows.append(
                {
                    "video_id": row.get("video_id", ""),
                    "species_code": species,
                    "status": status,
                    "reason": suspicious_reason
                    or ("missing_raw" if not raw_ok else "")
                    or ("missing_derived" if not derived_ok else "")
                    or ("non_downloaded" if status != "downloaded" else ""),
                    "title": title,
                    "raw_path": row.get("local_raw_path", ""),
                    "derived_path": row.get("local_derived_path", ""),
                    "duration_seconds": row.get("duration_seconds", ""),
                }
            )

        duplicate_video_ids[row.get("video_id", "")].append(row)

    duplicate_groups = [
        rows_for_id
        for video_id, rows_for_id in duplicate_video_ids.items()
        if video_id and len(rows_for_id) > 1
    ]

    payload = {
        "manifest": str(manifest_path.relative_to(ROOT)),
        "rows": len(rows),
        "species": dict(counts_by_species),
        "status": dict(status_counter),
        "duration_buckets": dict(duration_buckets),
        "raw_exists": raw_exists,
        "derived_exists": derived_exists,
        "missing_raw": missing_raw,
        "missing_derived": missing_derived,
        "short_rows": short_rows,
        "long_rows": long_rows,
        "duplicate_video_groups": len(duplicate_groups),
        "suspicious_rows": suspicious_rows[:50],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# YouTube Cicada Collection Report",
        "",
        f"- Manifest: `{payload['manifest']}`",
        f"- Rows: {payload['rows']}",
        f"- Raw files present: {payload['raw_exists']}",
        f"- Derived files present: {payload['derived_exists']}",
        f"- Missing raw files: {payload['missing_raw']}",
        f"- Missing derived files: {payload['missing_derived']}",
        f"- Duplicate video groups: {payload['duplicate_video_groups']}",
        "",
        "## Status",
    ]
    for status, count in status_counter.most_common():
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Species"])
    for species, count in counts_by_species.most_common():
        lines.append(f"- {species}: {count}")
    lines.extend(["", "## Duration Buckets"])
    for bucket, count in duration_buckets.most_common():
        lines.append(f"- {bucket}: {count}")
    lines.extend(["", "## Suspicious Rows"])
    if suspicious_rows:
        for row in suspicious_rows[:25]:
            lines.append(
                f"- {row['species_code']} | {row['status']} | {row['reason']} | {row['title']} | {row['video_id']}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Notes"])
    lines.append("- Suspicious rows include non-downloaded items, missing files, or blacklisted titles.")
    lines.append("- The JSON report includes up to 50 suspicious rows for quick triage.")
    args.out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {args.out_md}")
    print(f"Wrote {args.out_json}")
    print(f"Rows: {payload['rows']}, suspicious: {len(suspicious_rows)}")


if __name__ == "__main__":
    main()
