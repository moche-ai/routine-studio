"""벤치마크 결과 캐시 서비스"""

import json
import hashlib
import re
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from urllib.parse import unquote

CACHE_DIR = Path("/app/output/benchmark_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def normalize_channel_url(url: str) -> str:
    """채널 URL 정규화 (URL 디코딩 포함)"""
    url = url.strip().rstrip('/')

    # URL 디코딩 (한글 처리)
    url = unquote(url)

    # @handle 형식
    match = re.search(r'youtube\.com/@([^/?]+)', url)
    if match:
        return f"@{match.group(1).lower()}"

    # channel/UC... 형식
    match = re.search(r'youtube\.com/channel/([^/?]+)', url)
    if match:
        return match.group(1)

    # /c/name 형식
    match = re.search(r'youtube\.com/c/([^/?]+)', url)
    if match:
        return f"c/{match.group(1).lower()}"

    # 그냥 채널명인 경우
    if not url.startswith('http'):
        return f"@{url.lower().replace(' ', '')}"

    return url


def get_cache_key(channel_urls: list) -> str:
    """채널 URL 목록에서 캐시 키 생성"""
    normalized = sorted([normalize_channel_url(url) for url in channel_urls])
    combined = "|".join(normalized)
    return hashlib.md5(combined.encode()).hexdigest()[:16]


def get_single_channel_key(channel_url: str) -> str:
    """단일 채널 캐시 키 (해시 기반)"""
    normalized = normalize_channel_url(channel_url)
    # 해시로 변환하여 파일명 문제 방지
    return hashlib.md5(normalized.encode()).hexdigest()[:16]


def save_benchmark(channel_urls: list, report_data: Dict[str, Any]) -> str:
    """벤치마크 결과 저장"""
    cache_key = get_cache_key(channel_urls)

    cache_data = {
        "cache_key": cache_key,
        "channel_urls": channel_urls,
        "normalized_urls": [normalize_channel_url(url) for url in channel_urls],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "report": report_data
    }

    cache_file = CACHE_DIR / f"{cache_key}.json"
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)

    # 채널별 인덱스도 저장 (빠른 검색용)
    for url in channel_urls:
        single_key = get_single_channel_key(url)
        index_file = CACHE_DIR / f"index_{single_key}.json"
        index_data = {
            "channel_url": url,
            "normalized_url": normalize_channel_url(url),
            "cache_key": cache_key,
            "updated_at": datetime.now().isoformat()
        }
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

    print(f"[BenchmarkCache] Saved: {cache_key} for {[normalize_channel_url(u) for u in channel_urls]}")
    return cache_key


def find_benchmark(channel_url: str) -> Optional[Dict[str, Any]]:
    """채널에 대한 기존 벤치마크 검색"""
    normalized = normalize_channel_url(channel_url)
    single_key = get_single_channel_key(channel_url)
    index_file = CACHE_DIR / f"index_{single_key}.json"

    print(f"[BenchmarkCache] Looking for: {normalized} -> index_{single_key}.json")

    if not index_file.exists():
        print(f"[BenchmarkCache] Index not found: {index_file}")
        return None

    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)

        cache_key = index_data.get("cache_key")
        cache_file = CACHE_DIR / f"{cache_key}.json"

        if not cache_file.exists():
            print(f"[BenchmarkCache] Cache file not found: {cache_file}")
            return None

        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"[BenchmarkCache] Found cache: {cache_key}")
            return data
    except Exception as e:
        print(f"[BenchmarkCache] Error loading cache: {e}")
        return None


def get_cache_summary(cache_data: Dict[str, Any]) -> str:
    """캐시된 벤치마크 요약 생성"""
    channels = cache_data.get("channel_urls", [])
    created = cache_data.get("created_at", "알 수 없음")
    report = cache_data.get("report", {})

    # 날짜 포맷팅
    try:
        dt = datetime.fromisoformat(created)
        date_str = dt.strftime("%Y년 %m월 %d일 %H:%M")
    except:
        date_str = created

    # 채널명 정리
    channel_names = []
    for url in channels:
        normalized = normalize_channel_url(url)
        if normalized.startswith("@"):
            channel_names.append(normalized[1:])  # @ 제거
        else:
            channel_names.append(normalized)

    channel_list = ", ".join(channel_names)

    summary = f"""**이미 벤치마킹된 채널입니다!**

**채널:** {channel_list}
**분석 일시:** {date_str}
"""

    # 리포트 요약 추가
    if report:
        concept = report.get("channel_concept", "")
        if concept and isinstance(concept, str) and len(concept) > 10:
            summary += f"\n**컨셉:** {concept[:100]}..."

    summary += "\n\n• **기존 결과 사용:** '확인' 또는 '다음'\n• **새로 분석:** '업데이트' 또는 '다시 분석'"

    return summary


def delete_benchmark(channel_url: str) -> bool:
    """벤치마크 캐시 삭제"""
    single_key = get_single_channel_key(channel_url)
    index_file = CACHE_DIR / f"index_{single_key}.json"

    if not index_file.exists():
        return False

    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)

        cache_key = index_data.get("cache_key")
        cache_file = CACHE_DIR / f"{cache_key}.json"

        if cache_file.exists():
            cache_file.unlink()
        index_file.unlink()

        return True
    except Exception as e:
        print(f"[BenchmarkCache] Error deleting cache: {e}")
        return False


def rebuild_index():
    """모든 캐시 파일의 인덱스 재구축"""
    count = 0
    for cache_file in CACHE_DIR.glob("*.json"):
        if cache_file.name.startswith("index_"):
            continue

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            cache_key = data.get("cache_key")
            channel_urls = data.get("channel_urls", [])

            for url in channel_urls:
                single_key = get_single_channel_key(url)
                index_file = CACHE_DIR / f"index_{single_key}.json"
                index_data = {
                    "channel_url": url,
                    "normalized_url": normalize_channel_url(url),
                    "cache_key": cache_key,
                    "updated_at": datetime.now().isoformat()
                }
                with open(index_file, 'w', encoding='utf-8') as f:
                    json.dump(index_data, f, ensure_ascii=False, indent=2)
                count += 1
                print(f"[BenchmarkCache] Indexed: {normalize_channel_url(url)}")
        except Exception as e:
            print(f"[BenchmarkCache] Error indexing {cache_file}: {e}")

    return count
