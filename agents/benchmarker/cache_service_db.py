"""벤치마크 결과 DB 캐시 서비스 - cache_service.py와 동일 인터페이스"""

import sys
import hashlib
import re
from typing import Optional, Dict, Any
from datetime import datetime
from urllib.parse import unquote

sys.path.insert(0, "/data/routine/routine-studio-v2/apps/api")

from database import get_db_context
from models import Benchmark


def normalize_channel_url(url: str) -> str:
    """채널 URL 정규화 (URL 디코딩 포함)"""
    url = url.strip().rstrip('/')
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

    # 이미 @로 시작하는 경우 (이미 정규화됨)
    if url.startswith('@'):
        return url.lower()

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
    return hashlib.md5(normalized.encode()).hexdigest()[:16]


def save_benchmark(channel_urls: list, report_data: Dict[str, Any], project_id: str = None) -> str:
    """벤치마크 결과를 DB에 저장"""
    cache_key = get_cache_key(channel_urls)
    
    try:
        with get_db_context() as db:
            # 기존 벤치마크 검색 (채널 URL 기준)
            for url in channel_urls:
                normalized = normalize_channel_url(url)
                existing = db.query(Benchmark).filter(
                    Benchmark.channel_url == normalized
                ).first()
                
                if existing:
                    # 업데이트
                    existing.channel_name = report_data.get("channel_name")
                    existing.subscriber_count = report_data.get("subscriber_count")
                    existing.video_count = report_data.get("video_count")
                    existing.channel_concept = report_data.get("channel_concept")
                    existing.unique_selling_point = report_data.get("unique_selling_point")
                    existing.brand_voice = report_data.get("brand_voice")
                    existing.thumbnail_pattern = report_data.get("thumbnail_pattern")
                    existing.script_pattern = report_data.get("script_pattern")
                    existing.content_strategy = report_data.get("content_strategy")
                    existing.audience_profile = report_data.get("audience_profile")
                    existing.replication_guide = report_data
                    existing.analyzed_at = datetime.utcnow()
                    if project_id:
                        existing.project_id = project_id
                else:
                    # 새로 생성
                    benchmark = Benchmark(
                        project_id=project_id,
                        channel_url=normalized,
                        channel_name=report_data.get("channel_name"),
                        subscriber_count=report_data.get("subscriber_count"),
                        video_count=report_data.get("video_count"),
                        channel_concept=report_data.get("channel_concept"),
                        unique_selling_point=report_data.get("unique_selling_point"),
                        brand_voice=report_data.get("brand_voice"),
                        thumbnail_pattern=report_data.get("thumbnail_pattern"),
                        script_pattern=report_data.get("script_pattern"),
                        content_strategy=report_data.get("content_strategy"),
                        audience_profile=report_data.get("audience_profile"),
                        replication_guide=report_data,
                        analyzed_at=datetime.utcnow()
                    )
                    db.add(benchmark)
            
            db.commit()
            print(f"[BenchmarkCacheDB] Saved: {cache_key} for {[normalize_channel_url(u) for u in channel_urls]}")
            return cache_key
            
    except Exception as e:
        print(f"[BenchmarkCacheDB] Error saving benchmark: {e}")
        return cache_key


def find_benchmark(channel_url: str) -> Optional[Dict[str, Any]]:
    """채널에 대한 기존 벤치마크 검색"""
    normalized = normalize_channel_url(channel_url)
    
    print(f"[BenchmarkCacheDB] Looking for: {normalized}")
    
    try:
        with get_db_context() as db:
            benchmark = db.query(Benchmark).filter(
                Benchmark.channel_url == normalized
            ).first()
            
            if not benchmark:
                print(f"[BenchmarkCacheDB] Not found in DB: {normalized}")
                return None
            
            # cache_service.py와 동일한 형식으로 반환
            result = {
                "cache_key": get_single_channel_key(channel_url),
                "channel_urls": [channel_url],
                "normalized_urls": [normalized],
                "created_at": benchmark.analyzed_at.isoformat() if benchmark.analyzed_at else None,
                "updated_at": benchmark.analyzed_at.isoformat() if benchmark.analyzed_at else None,
                "report": benchmark.replication_guide or {
                    "channel_name": benchmark.channel_name,
                    "channel_concept": benchmark.channel_concept,
                    "unique_selling_point": benchmark.unique_selling_point,
                    "brand_voice": benchmark.brand_voice,
                    "thumbnail_pattern": benchmark.thumbnail_pattern,
                    "script_pattern": benchmark.script_pattern,
                    "content_strategy": benchmark.content_strategy,
                    "audience_profile": benchmark.audience_profile,
                }
            }
            
            print(f"[BenchmarkCacheDB] Found in DB: {normalized}")
            return result
            
    except Exception as e:
        print(f"[BenchmarkCacheDB] Error finding benchmark: {e}")
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
            channel_names.append(normalized[1:])
        else:
            channel_names.append(normalized)

    channel_list = ", ".join(channel_names)

    summary = f"""**이미 벤치마킹된 채널입니다!**

**채널:** {channel_list}
**분석 일시:** {date_str}
"""

    if report:
        concept = report.get("channel_concept", "")
        if concept and isinstance(concept, str) and len(concept) > 10:
            summary += f"\n**컨셉:** {concept[:100]}..."

    summary += "\n\n• **기존 결과 사용:** '확인' 또는 '다음'\n• **새로 분석:** '업데이트' 또는 '다시 분석'"

    return summary


def delete_benchmark(channel_url: str) -> bool:
    """벤치마크 캐시 삭제"""
    normalized = normalize_channel_url(channel_url)
    
    try:
        with get_db_context() as db:
            benchmark = db.query(Benchmark).filter(
                Benchmark.channel_url == normalized
            ).first()
            
            if benchmark:
                db.delete(benchmark)
                db.commit()
                print(f"[BenchmarkCacheDB] Deleted: {normalized}")
                return True
            return False
            
    except Exception as e:
        print(f"[BenchmarkCacheDB] Error deleting benchmark: {e}")
        return False


def list_all_benchmarks(limit: int = 100) -> list:
    """모든 벤치마크 목록 조회"""
    try:
        with get_db_context() as db:
            benchmarks = db.query(Benchmark).order_by(
                Benchmark.analyzed_at.desc()
            ).limit(limit).all()
            
            return [
                {
                    "id": b.id,
                    "channel_url": b.channel_url,
                    "channel_name": b.channel_name,
                    "analyzed_at": b.analyzed_at.isoformat() if b.analyzed_at else None
                }
                for b in benchmarks
            ]
    except Exception as e:
        print(f"[BenchmarkCacheDB] Error listing benchmarks: {e}")
        return []
