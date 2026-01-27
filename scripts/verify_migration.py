#!/usr/bin/env python3
"""
마이그레이션 검증 스크립트
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, "/data/routine/routine-studio-v2/apps/api")

from database import get_db_context, init_db
from models import Project, Character, Benchmark

SESSIONS_DIR = Path("/data/routine/routine-studio-v2/output/.sessions")
CACHE_DIR = Path("/data/routine/routine-studio-v2/output/benchmark_cache")


def verify_migration():
    """마이그레이션 결과 검증"""
    
    print("="*60)
    print("마이그레이션 검증 리포트")
    print("="*60)
    
    # JSON 파일 수 확인
    session_files = list(SESSIONS_DIR.glob("*.json")) if SESSIONS_DIR.exists() else []
    cache_files = [f for f in CACHE_DIR.glob("*.json") if not f.name.startswith("index_")] if CACHE_DIR.exists() else []
    
    print(f"\n[JSON 파일]")
    print(f"  - 세션 파일: {len(session_files)}개")
    print(f"  - 벤치마크 캐시 파일: {len(cache_files)}개")
    
    # DB 레코드 수 확인
    with get_db_context() as db:
        project_count = db.query(Project).count()
        character_count = db.query(Character).count()
        benchmark_count = db.query(Benchmark).count()
        
        print(f"\n[DB 레코드]")
        print(f"  - projects 테이블: {project_count}개")
        print(f"  - characters 테이블: {character_count}개")
        print(f"  - benchmarks 테이블: {benchmark_count}개")
        
        # 샘플 데이터 확인
        print(f"\n[샘플 데이터 검증]")
        
        # 프로젝트 샘플
        sample_project = db.query(Project).first()
        if sample_project:
            print(f"\n  프로젝트 샘플:")
            print(f"    - ID: {sample_project.id}")
            print(f"    - 채널명: {sample_project.channel_name}")
            print(f"    - 현재 단계: {sample_project.current_step}")
            print(f"    - context_json 키: {list(sample_project.context_json.keys()) if sample_project.context_json else 'None'}")
        else:
            print(f"\n  프로젝트 샘플: 없음")
        
        # 캐릭터 샘플
        sample_character = db.query(Character).first()
        if sample_character:
            print(f"\n  캐릭터 샘플:")
            print(f"    - ID: {sample_character.id}")
            print(f"    - 프로젝트 ID: {sample_character.project_id}")
            print(f"    - 타입: {sample_character.character_type}")
            print(f"    - 이미지 존재: {'Yes' if sample_character.image_base64 else 'No'}")
        else:
            print(f"\n  캐릭터 샘플: 없음")
        
        # 벤치마크 샘플
        sample_benchmark = db.query(Benchmark).first()
        if sample_benchmark:
            print(f"\n  벤치마크 샘플:")
            print(f"    - ID: {sample_benchmark.id}")
            print(f"    - 채널 URL: {sample_benchmark.channel_url}")
            print(f"    - 채널명: {sample_benchmark.channel_name}")
            print(f"    - 분석 일시: {sample_benchmark.analyzed_at}")
        else:
            print(f"\n  벤치마크 샘플: 없음")
    
    # 무결성 검증
    print(f"\n[무결성 검증]")
    
    errors = []
    
    # JSON 파일과 DB 레코드 매칭 확인
    with get_db_context() as db:
        for session_file in session_files[:5]:  # 처음 5개만 검증
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                session_id = json_data.get("id")
                if session_id:
                    db_project = db.query(Project).filter(Project.id == session_id).first()
                    if db_project:
                        # context_json 비교
                        json_context = json_data.get("context", {})
                        db_context = db_project.context_json or {}
                        
                        if json_context.get("user_request") != db_context.get("user_request"):
                            errors.append(f"user_request mismatch for {session_id}")
                    else:
                        errors.append(f"Session {session_id} not found in DB")
            except Exception as e:
                errors.append(f"Error checking {session_file.name}: {e}")
    
    if errors:
        print(f"  - 오류: {len(errors)}개")
        for err in errors[:5]:
            print(f"    * {err}")
    else:
        print(f"  - 모든 샘플 데이터 검증 통과!")
    
    print(f"\n" + "="*60)
    print("검증 완료")
    print("="*60)


if __name__ == "__main__":
    verify_migration()
