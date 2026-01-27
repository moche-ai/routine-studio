#!/usr/bin/env python3
"""
벤치마크 캐시 JSON 파일을 SQLite DB로 마이그레이션
"""
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "/data/routine/routine-studio-v2/apps/api")

from database import get_db_context, init_db
from models import Benchmark

CACHE_DIR = Path("/data/routine/routine-studio-v2/output/benchmark_cache")


def migrate_benchmarks():
    """모든 벤치마크 캐시 JSON 파일을 DB로 마이그레이션"""
    
    # DB 초기화
    init_db()
    
    if not CACHE_DIR.exists():
        print(f"[Migration] Benchmark cache directory not found: {CACHE_DIR}")
        return 0
    
    # index_ 파일 제외하고 실제 캐시 파일만 찾기
    cache_files = [f for f in CACHE_DIR.glob("*.json") if not f.name.startswith("index_")]
    print(f"[Migration] Found {len(cache_files)} benchmark cache files")
    
    migrated = 0
    skipped = 0
    errors = 0
    
    with get_db_context() as db:
        for cache_file in cache_files:
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                channel_urls = data.get("channel_urls", [])
                normalized_urls = data.get("normalized_urls", [])
                report = data.get("report", {})
                created_at = data.get("created_at")
                
                if not channel_urls and not normalized_urls:
                    print(f"[Migration] Skipping {cache_file.name}: no channel urls")
                    skipped += 1
                    continue
                
                # 각 채널 URL에 대해 벤치마크 생성
                urls_to_process = normalized_urls if normalized_urls else channel_urls
                
                for channel_url in urls_to_process:
                    # 기존 벤치마크 확인
                    existing = db.query(Benchmark).filter(
                        Benchmark.channel_url == channel_url
                    ).first()
                    
                    if existing:
                        print(f"[Migration] Skipping {channel_url}: already exists")
                        skipped += 1
                        continue
                    
                    # 날짜 파싱
                    analyzed_at = None
                    if created_at:
                        try:
                            analyzed_at = datetime.fromisoformat(created_at)
                        except:
                            analyzed_at = datetime.utcnow()
                    else:
                        analyzed_at = datetime.utcnow()
                    
                    # Benchmark 생성
                    benchmark = Benchmark(
                        project_id=None,  # 마이그레이션된 데이터는 프로젝트 연결 없음
                        channel_url=channel_url,
                        channel_name=report.get("channel_name"),
                        subscriber_count=report.get("subscriber_count"),
                        video_count=report.get("video_count"),
                        channel_concept=report.get("channel_concept"),
                        unique_selling_point=report.get("unique_selling_point"),
                        brand_voice=report.get("brand_voice"),
                        thumbnail_pattern=report.get("thumbnail_pattern"),
                        script_pattern=report.get("script_pattern"),
                        content_strategy=report.get("content_strategy"),
                        audience_profile=report.get("audience_profile"),
                        replication_guide=report,
                        analyzed_at=analyzed_at
                    )
                    db.add(benchmark)
                    migrated += 1
                    print(f"[Migration] Migrated: {channel_url}")
                
            except Exception as e:
                print(f"[Migration] Error migrating {cache_file.name}: {e}")
                errors += 1
        
        db.commit()
    
    print(f"\n[Migration] Complete!")
    print(f"  - Migrated: {migrated}")
    print(f"  - Skipped: {skipped}")
    print(f"  - Errors: {errors}")
    
    return migrated


if __name__ == "__main__":
    migrate_benchmarks()
