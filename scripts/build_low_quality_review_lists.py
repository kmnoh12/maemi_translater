from __future__ import annotations

import argparse
import contextlib
import csv
import json
import wave
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INAT = ROOT / "data-workspace" / "metadata" / "inat_full_manifest.csv"
DEFAULT_YOUTUBE = ROOT / "data-workspace" / "metadata" / "youtube_manifest.csv"
DEFAULT_OUT_DIR = ROOT / "data-workspace" / "metadata"


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def wav_duration_seconds(path: Path) -> float | None:
    try:
        with contextlib.closing(wave.open(str(path), "rb")) as wf:
            return wf.getnframes() / float(wf.getframerate())
    except Exception:
        return None


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_youtube_review_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    flagged: list[dict[str, str]] = []
    for row in rows:
        rejected_reason = (row.get("rejected_reason") or "").strip()
        strict_reason = (row.get("strict_filter_reason") or "").strip()
        if not rejected_reason and not strict_reason:
            continue
        flagged.append(
            {
                "source": "youtube",
                "species_code": row.get("species_code", ""),
                "item_id": row.get("video_id", ""),
                "title_or_place": row.get("video_title", ""),
                "quality_bucket": "rejected" if rejected_reason else "review",
                "quality_reason": rejected_reason or strict_reason,
                "quality_grade": row.get("label_confidence", ""),
                "duration_seconds": row.get("duration_seconds", ""),
                "source_url": row.get("video_url", ""),
                "local_derived_path": row.get("local_derived_path", ""),
            }
        )
    return flagged


def build_inat_review_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    flagged: list[dict[str, str]] = []
    for row in rows:
        reasons: list[str] = []
        bucket = "review"
        derived = (row.get("local_derived_path") or "").strip()
        derived_path = ROOT / derived if derived else None
        duration = None

        if not derived_path or not derived_path.exists():
            bucket = "rejected"
            reasons.append("missing_derived")
        else:
            duration = wav_duration_seconds(derived_path)
            if duration is None:
                bucket = "rejected"
                reasons.append("unreadable_derived")
            else:
                if duration < 5:
                    bucket = "rejected"
                    reasons.append("too_short_lt5s")
                elif duration < 8:
                    reasons.append("short_lt8s")
                if duration > 60:
                    reasons.append("long_gt60s")
                if duration > 90:
                    bucket = "rejected"
                    reasons.append("very_long_gt90s")

        quality_grade = (row.get("quality_grade") or "").strip().lower()
        if quality_grade == "casual":
            bucket = "rejected"
            reasons.append("quality_grade_casual")
        elif quality_grade == "needs_id":
            reasons.append("quality_grade_needs_id")

        place_guess = (row.get("place_guess") or "").strip()
        if not place_guess:
            reasons.append("missing_place_guess")

        if not reasons:
            continue

        flagged.append(
            {
                "source": "inat",
                "species_code": row.get("species_code", ""),
                "item_id": row.get("sound_id", ""),
                "title_or_place": place_guess,
                "quality_bucket": bucket,
                "quality_reason": ";".join(reasons),
                "quality_grade": row.get("quality_grade", ""),
                "duration_seconds": "" if duration is None else f"{duration:.2f}",
                "source_url": row.get("source_url", ""),
                "local_derived_path": row.get("local_derived_path", ""),
            }
        )
    return flagged


def main() -> None:
    parser = argparse.ArgumentParser(description="Build internal low-quality review lists for YouTube and iNaturalist audio.")
    parser.add_argument("--inat-manifest", type=Path, default=DEFAULT_INAT)
    parser.add_argument("--youtube-manifest", type=Path, default=DEFAULT_YOUTUBE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    inat_rows = load_rows(args.inat_manifest.resolve())
    youtube_rows = load_rows(args.youtube_manifest.resolve())

    youtube_flagged = build_youtube_review_rows(youtube_rows)
    inat_flagged = build_inat_review_rows(inat_rows)
    all_flagged = sorted(
        youtube_flagged + inat_flagged,
        key=lambda row: (row["source"], row["species_code"], row["quality_bucket"], row["item_id"]),
    )

    out_dir = args.out_dir.resolve()
    fieldnames = [
        "source",
        "species_code",
        "item_id",
        "title_or_place",
        "quality_bucket",
        "quality_reason",
        "quality_grade",
        "duration_seconds",
        "source_url",
        "local_derived_path",
    ]
    write_csv(out_dir / "youtube_low_quality_review.csv", youtube_flagged, fieldnames)
    write_csv(out_dir / "inat_low_quality_review.csv", inat_flagged, fieldnames)
    write_csv(out_dir / "all_low_quality_review.csv", all_flagged, fieldnames)

    summary = {
        "youtube_flagged": len(youtube_flagged),
        "inat_flagged": len(inat_flagged),
        "all_flagged": len(all_flagged),
        "youtube_buckets": Counter(row["quality_bucket"] for row in youtube_flagged),
        "inat_buckets": Counter(row["quality_bucket"] for row in inat_flagged),
        "youtube_reasons": Counter(row["quality_reason"] for row in youtube_flagged).most_common(20),
        "inat_reasons": Counter(row["quality_reason"] for row in inat_flagged).most_common(20),
    }
    (out_dir / "low_quality_review_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8-sig",
    )

    print(f"YouTube flagged: {len(youtube_flagged)}")
    print(f"iNat flagged: {len(inat_flagged)}")
    print(f"All flagged: {len(all_flagged)}")


if __name__ == "__main__":
    main()
