"""YouTube 매미 소리 매니페스트 생성기.

사용법
------
1) URL 목록 파일에서 매니페스트 생성:
   python build_youtube_manifest.py --from-urls urls.txt --species yujimaemi

2) 검색어로 자동 검색 → 매니페스트 생성:
   python build_youtube_manifest.py --search "유지매미 울음소리" --species yujimaemi --max-results 30

3) 기존 매니페스트에 추가:
   python build_youtube_manifest.py --search "アブラゼミ 鳴き声" --species yujimaemi --append

출력
----
data-workspace/metadata/youtube_manifest.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "data-workspace" / "metadata" / "youtube_manifest.csv"
DEFAULT_SEARCH_TERMS = ROOT / "data-workspace" / "metadata" / "youtube_species_search_terms.json"

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

DEFAULT_MIN_DURATION = 5
DEFAULT_MAX_DURATION = 900
DEFAULT_TITLE_BLACKLIST = (
    "shorts",
    "asmr",
    "music",
    "remix",
    "cover",
    "meme",
    "news",
    "podcast",
    "interview",
    "reaction",
    "compilation",
)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass


def load_species_catalog() -> list[dict]:
    catalog_path = ROOT / "data-workspace" / "metadata" / "species_catalog.json"
    with catalog_path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_search_terms(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def safe_filename(title: str, video_id: str) -> str:
    """파일 시스템에 안전한 이름으로 변환."""
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title)
    clean = clean.strip(". ")
    if len(clean) > 80:
        clean = clean[:80].rstrip(". ")
    return f"{clean} [{video_id}]"


def fetch_video_info(url_or_id: str) -> dict | None:
    """yt-dlp로 영상 메타데이터만 가져온다 (다운로드하지 않음)."""
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--dump-json",
        "--no-download",
        "--no-playlist",
        "--",
        url_or_id,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, encoding="utf-8"
        )
        if result.returncode != 0:
            print(f"  [WARN] yt-dlp failed for {url_or_id}: {result.stderr[:200]}")
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print(f"  [WARN] Error fetching info for {url_or_id}: {exc}")
        return None


def search_youtube(query: str, max_results: int = 20) -> list[dict]:
    """yt-dlp의 ytsearch 기능으로 검색."""
    search_url = f"ytsearch{max_results}:{query}"
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--dump-json",
        "--no-download",
        "--flat-playlist",
        search_url,
    ]
    results = []
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, encoding="utf-8"
        )
        for line in proc.stdout.strip().split("\n"):
            if not line.strip():
                continue
            try:
                info = json.loads(line)
                results.append(info)
            except json.JSONDecodeError:
                continue
    except subprocess.TimeoutExpired:
        print(f"  [WARN] Search timed out for: {query}")
    return results


def build_row(
    info: dict,
    species_code: str,
    search_query: str = "",
) -> dict[str, str]:
    """yt-dlp 영상 정보를 매니페스트 행으로 변환."""
    video_id = info.get("id", "")
    title = info.get("title", "") or info.get("fulltitle", "") or video_id
    channel = info.get("channel", "") or info.get("uploader", "") or ""
    upload_date = info.get("upload_date", "")
    if upload_date and len(upload_date) == 8:
        upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
    duration = str(info.get("duration") or "")

    base_name = safe_filename(title, video_id)

    return {
        "source": "youtube",
        "video_id": video_id,
        "video_title": title,
        "channel": channel,
        "upload_date": upload_date,
        "duration_seconds": duration,
        "species_code": species_code,
        "label_confidence": "probable",
        "license_note": "research_fair_use_kr_art35_5",
        "search_query": search_query,
        "video_url": f"https://www.youtube.com/watch?v={video_id}",
        "download_date": "",
        "local_raw_path": f"data-workspace/raw_audio/youtube_candidates/{species_code}/{base_name}.wav",
        "local_derived_path": f"data-workspace/derived_audio/youtube_candidates/{species_code}/{base_name}_16k_mono.wav",
        "status": "pending",
    }


def load_existing_rows(manifest_path: Path) -> list[dict[str, str]]:
    """기존 매니페스트 행을 그대로 읽어 반환."""
    if not manifest_path.exists():
        return []
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_existing_ids(manifest_path: Path) -> set[str]:
    """기존 매니페스트에서 이미 등록된 video_id 세트 반환."""
    return {row["video_id"] for row in load_existing_rows(manifest_path) if row.get("video_id")}


def should_keep_video(
    info: dict,
    min_duration: int,
    max_duration: int,
    blacklist_terms: tuple[str, ...],
) -> tuple[bool, str]:
    """분류 혼동을 줄이기 위해 검색 결과를 간단히 필터링한다."""
    title = (info.get("title") or info.get("fulltitle") or "").lower()
    channel = (info.get("channel") or info.get("uploader") or "").lower()
    duration = info.get("duration")
    is_live = bool(info.get("is_live") or info.get("was_live"))

    if is_live:
        return False, "live"

    if isinstance(duration, (int, float)):
        if duration < min_duration:
            return False, f"too_short:{int(duration)}s"
        if duration > max_duration:
            return False, f"too_long:{int(duration)}s"

    haystack = f"{title} {channel}"
    for term in blacklist_terms:
        if term and term in haystack:
            return False, f"blacklist:{term}"

    return True, ""


def generate_multilingual_queries(
    species_code: str,
    scientific_name: str,
    search_terms_path: Path,
) -> list[str]:
    """종별 별칭, 언어별 suffix, 고정 쿼리를 조합해 자동 검색어 목록을 만든다."""
    config = load_search_terms(search_terms_path)
    aliases = list(config.get("species", {}).get(species_code, []))
    suffixes = [s.strip() for s in config.get("search_suffixes", []) if s and s.strip()]
    direct_queries = [
        q.strip()
        for q in config.get("direct_queries", {}).get(species_code, [])
        if q and q.strip()
    ]

    if scientific_name and scientific_name not in aliases:
        aliases.insert(0, scientific_name)

    queries: list[str] = []
    seen: set[str] = set()
    for alias in aliases:
        alias = alias.strip()
        if not alias:
            continue
        candidates = [alias] + [f"{alias} {suffix}" for suffix in suffixes]
        for query in candidates:
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


def write_manifest(
    rows: list[dict[str, str]], out_path: Path, append: bool = False
) -> None:
    """매니페스트를 CSV로 쓴다."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    existing_rows = load_existing_rows(out_path) if out_path.exists() else []
    merged_rows = rows
    if append or existing_rows:
        merged_rows = existing_rows + rows

    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(merged_rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="YouTube 매미 소리 매니페스트 생성기"
    )
    parser.add_argument(
        "--from-urls",
        type=Path,
        help="한 줄에 하나씩 YouTube URL/ID가 적힌 텍스트 파일",
    )
    parser.add_argument(
        "--search",
        type=str,
        help="YouTube 검색어 (예: '유지매미 울음소리')",
    )
    parser.add_argument(
        "--species",
        type=str,
        required=True,
        help="종 코드 (chammaemi, malmaemi, yujimaemi, aemaemi, sseureummaemi, teolmaemi)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=20,
        help="검색 모드에서 최대 결과 수 (기본 20)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"출력 매니페스트 경로 (기본: {DEFAULT_OUT.relative_to(ROOT)})",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="기존 매니페스트에 추가 (덮어쓰지 않음)",
    )
    parser.add_argument(
        "--all-species",
        action="store_true",
        help="species_catalog의 6종 전체를 대상으로 자동 다국어 검색",
    )
    parser.add_argument(
        "--auto-multilingual",
        action="store_true",
        help="지정한 종에 대해 다국어 검색어를 자동 생성",
    )
    parser.add_argument(
        "--search-terms-config",
        type=Path,
        default=DEFAULT_SEARCH_TERMS,
        help=f"종별 다국어 검색어 설정 파일 (기본: {DEFAULT_SEARCH_TERMS.relative_to(ROOT)})",
    )
    parser.add_argument(
        "--min-duration",
        type=int,
        default=DEFAULT_MIN_DURATION,
        help=f"검색 결과 최소 길이(초). 기본 {DEFAULT_MIN_DURATION}",
    )
    parser.add_argument(
        "--max-duration",
        type=int,
        default=DEFAULT_MAX_DURATION,
        help=f"검색 결과 최대 길이(초). 기본 {DEFAULT_MAX_DURATION}",
    )
    parser.add_argument(
        "--title-blacklist",
        type=str,
        default=",".join(DEFAULT_TITLE_BLACKLIST),
        help="검색 결과 제외 키워드(쉼표 구분)",
    )
    args = parser.parse_args()

    if not args.from_urls and not args.search and not args.auto_multilingual and not args.all_species:
        parser.error("--from-urls, --search, --auto-multilingual, --all-species 중 하나를 지정해야 합니다")

    if args.min_duration < 0 or args.max_duration <= 0 or args.min_duration > args.max_duration:
        parser.error("duration 필터 값이 올바르지 않습니다")

    blacklist_terms = tuple(
        term.strip().lower() for term in args.title_blacklist.split(",") if term.strip()
    )

    existing_ids = load_existing_ids(args.out)
    new_rows: list[dict[str, str]] = []

    def process_query(species_code: str, query: str) -> None:
        print(f"YouTube 검색: '{query}' ({species_code}, 최대 {args.max_results}개)")
        results = search_youtube(query, args.max_results)
        print(f"  검색 결과: {len(results)}개")

        for info in results:
            vid = info.get("id", "")
            if not vid or vid in existing_ids:
                continue

            full_info = fetch_video_info(vid)
            if not full_info:
                continue

            keep, reason = should_keep_video(
                full_info,
                min_duration=args.min_duration,
                max_duration=args.max_duration,
                blacklist_terms=blacklist_terms,
            )
            if not keep:
                print(f"  [SKIP] {full_info.get('title', vid)} ({reason})")
                continue

            row = build_row(full_info, species_code, search_query=query)
            new_rows.append(row)
            existing_ids.add(vid)
            print(f"  [ADD] {full_info.get('title', vid)}")

    # --- URL 목록에서 가져오기 ---
    if args.from_urls:
        urls_file = args.from_urls.resolve()
        if not urls_file.exists():
            parser.error(f"URL 파일을 찾을 수 없습니다: {urls_file}")

        urls = [
            line.strip()
            for line in urls_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        print(f"URL 파일에서 {len(urls)}개 항목 발견")

        for url in urls:
            info = fetch_video_info(url)
            if not info:
                continue
            vid = info.get("id", "")
            if vid in existing_ids:
                print(f"  [SKIP] 이미 매니페스트에 있음: {vid}")
                continue
            row = build_row(info, args.species)
            new_rows.append(row)
            existing_ids.add(vid)
            print(f"  [ADD] {info.get('title', vid)}")

    # --- 단일 검색 ---
    if args.search:
        process_query(args.species, args.search)

    # --- 지정 종 다국어 자동 검색 ---
    if args.auto_multilingual:
        catalog = load_species_catalog()
        species_info = next((item for item in catalog if item["species_code"] == args.species), None)
        if not species_info:
            parser.error(f"species_catalog에 없는 종 코드입니다: {args.species}")
        queries = generate_multilingual_queries(
            species_code=args.species,
            scientific_name=species_info.get("scientific_name", ""),
            search_terms_path=args.search_terms_config.resolve(),
        )
        for query in queries:
            process_query(args.species, query)

    # --- 6종 전체 다국어 자동 검색 ---
    if args.all_species:
        catalog = load_species_catalog()
        for species_info in catalog:
            species_code = species_info["species_code"]
            queries = generate_multilingual_queries(
                species_code=species_code,
                scientific_name=species_info.get("scientific_name", ""),
                search_terms_path=args.search_terms_config.resolve(),
            )
            for query in queries:
                process_query(species_code, query)

    if not new_rows:
        print("새로 추가할 항목이 없습니다.")
        return

    write_manifest(new_rows, args.out, append=args.append)
    print(f"\n{len(new_rows)}개 항목을 {args.out.relative_to(ROOT)}에 {'추가' if args.append else '기록'}했습니다.")


if __name__ == "__main__":
    main()
