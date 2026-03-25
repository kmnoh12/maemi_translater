"""YouTube 매니페스트 기반 오디오 다운로더.

youtube_manifest.csv에서 status=pending인 항목의 오디오를 다운로드한다.
다운로드 완료 시 status를 downloaded로 갱신한다.

사용법
------
# 전체 pending 다운로드
python download_youtube_audio.py

# 특정 종만
python download_youtube_audio.py --species yujimaemi

# 최대 10개만
python download_youtube_audio.py --limit 10

# 다른 매니페스트 지정
python download_youtube_audio.py --manifest path/to/manifest.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "data-workspace" / "metadata" / "youtube_manifest.csv"

FIELDNAMES = [
    "source",
    "video_id",
    "video_title",
    "channel",
    "upload_date",
    "duration_seconds",
    "species_code",
    "label_confidence",
    "license_note",
    "search_query",
    "video_url",
    "download_date",
    "local_raw_path",
    "local_derived_path",
    "status",
]

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass


def download_audio(video_url: str, output_path: Path) -> bool:
    """yt-dlp로 오디오만 추출하여 WAV로 저장."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # yt-dlp로 최고 품질 오디오만 추출 → WAV로 변환
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--no-playlist",
        "-x",                          # 오디오만 추출
        "--audio-format", "wav",       # WAV 출력
        "--audio-quality", "0",        # 최고 품질
        "--no-keep-video",             # 비디오 파일 삭제
        "--no-post-overwrites",
        "-o", str(output_path),        # 출력 경로
        "--quiet",
        "--no-warnings",
        "--",
        video_url,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2분 타임아웃
            encoding="utf-8",
        )
        if result.returncode != 0:
            print(f"    [ERR] yt-dlp error: {result.stderr[:300]}")
            return False
        return output_path.exists()
    except subprocess.TimeoutExpired:
        print(f"    [ERR] 다운로드 타임아웃 (120초 초과)")
        return False


def write_sidecar(output_path: Path, row: dict[str, str]) -> None:
    """다운로드된 파일 옆에 메타데이터 JSON 생성."""
    sidecar = output_path.with_suffix(output_path.suffix + ".json")
    sidecar_data = {
        "source": row.get("source", "youtube"),
        "video_id": row.get("video_id", ""),
        "video_title": row.get("video_title", ""),
        "channel": row.get("channel", ""),
        "upload_date": row.get("upload_date", ""),
        "species_code": row.get("species_code", ""),
        "label_confidence": row.get("label_confidence", ""),
        "license_note": row.get("license_note", ""),
        "video_url": row.get("video_url", ""),
        "download_date": row.get("download_date", ""),
    }
    sidecar.write_text(
        json.dumps(sidecar_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="YouTube 매니페스트 기반 오디오 다운로더"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=f"매니페스트 경로 (기본: {DEFAULT_MANIFEST.relative_to(ROOT)})",
    )
    parser.add_argument(
        "--species",
        type=str,
        help="특정 종만 다운로드 (예: yujimaemi)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="최대 다운로드 수 (0=무제한)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="이미 다운로드된 파일도 다시 받기",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="status=failed 항목도 다시 시도",
    )
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    if not manifest_path.exists():
        print(f"매니페스트를 찾을 수 없습니다: {manifest_path}")
        sys.exit(1)

    # 매니페스트 읽기
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    downloaded = 0
    skipped = 0
    failed = 0
    updated_rows: list[dict[str, str]] = []

    for row in rows:
        # 필터링
        if args.species and row.get("species_code") != args.species:
            updated_rows.append(row)
            continue

        destination = ROOT / row["local_raw_path"]

        if row.get("status") == "failed" and not args.retry_failed and not args.force:
            updated_rows.append(row)
            skipped += 1
            continue

        # 이미 다운로드됨
        if not args.force and (
            row.get("status") == "downloaded" or destination.exists()
        ):
            if row.get("status") != "downloaded" and destination.exists():
                row["status"] = "downloaded"
            if not row.get("download_date") and destination.exists():
                row["download_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            updated_rows.append(row)
            skipped += 1
            continue

        video_url = row["video_url"]
        print(f"  [{downloaded + 1}] 다운로드: {row.get('video_title', video_url)[:60]}...")

        success = download_audio(video_url, destination)
        if success:
            row["download_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            write_sidecar(destination, row)
            row["status"] = "downloaded"
            downloaded += 1
            print(f"    [OK] → {row['local_raw_path']}")
        else:
            row["status"] = "failed"
            failed += 1

        updated_rows.append(row)

        if args.limit and downloaded >= args.limit:
            # 나머지 행은 그대로 유지
            updated_rows.extend(rows[len(updated_rows):])
            break

    # 매니페스트 status 갱신하여 다시 저장
    with manifest_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in updated_rows:
            # FIELDNAMES에 있는 키만 쓴다
            filtered = {k: row.get(k, "") for k in FIELDNAMES}
            writer.writerow(filtered)

    print(f"\n완료: 다운로드 {downloaded} / 스킵 {skipped} / 실패 {failed}")


if __name__ == "__main__":
    main()
