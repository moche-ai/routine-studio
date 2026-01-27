#!/usr/bin/env python3
"""
세션 JSON 파일을 SQLite DB로 마이그레이션
"""
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "/data/routine/routine-studio-v2/apps/api")

from database import get_db_context, init_db
from models import Project, Character

SESSIONS_DIR = Path("/data/routine/routine-studio-v2/output/.sessions")
DEFAULT_USER_ID = "default"


def migrate_sessions():
    """모든 세션 JSON 파일을 DB로 마이그레이션"""
    
    # DB 초기화
    init_db()
    
    if not SESSIONS_DIR.exists():
        print(f"[Migration] Sessions directory not found: {SESSIONS_DIR}")
        return 0
    
    session_files = list(SESSIONS_DIR.glob("*.json"))
    print(f"[Migration] Found {len(session_files)} session files")
    
    migrated = 0
    skipped = 0
    errors = 0
    
    with get_db_context() as db:
        for session_file in session_files:
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                session_id = data.get("id")
                if not session_id:
                    print(f"[Migration] Skipping {session_file.name}: no id")
                    skipped += 1
                    continue
                
                # 기존 프로젝트 확인
                existing = db.query(Project).filter(Project.id == session_id).first()
                if existing:
                    print(f"[Migration] Skipping {session_id}: already exists")
                    skipped += 1
                    continue
                
                context = data.get("context", {})
                
                # Project 생성
                project = Project(
                    id=session_id,
                    user_id=DEFAULT_USER_ID,
                    channel_name=context.get("selected_channel_name"),
                    user_request=context.get("user_request"),
                    current_step=data.get("current_step", "channel_name"),
                    status="in_progress",
                    context_json=context,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(project)
                
                # 캐릭터 정보 추출
                char_info = context.get("character_info")
                char_image = context.get("character_image")
                
                if char_info or char_image:
                    character = Character(
                        project_id=session_id,
                        character_type=char_info.get("character_type") if char_info else None,
                        gender=char_info.get("gender") if char_info else None,
                        clothing=char_info.get("clothing") if char_info else None,
                        expression=char_info.get("expression") if char_info else None,
                        art_style=char_info.get("art_style") if char_info else None,
                        personality=char_info.get("personality_vibe") if char_info else None,
                        image_base64=char_image
                    )
                    db.add(character)
                
                migrated += 1
                print(f"[Migration] Migrated: {session_id}")
                
            except Exception as e:
                print(f"[Migration] Error migrating {session_file.name}: {e}")
                errors += 1
        
        db.commit()
    
    print(f"\n[Migration] Complete!")
    print(f"  - Migrated: {migrated}")
    print(f"  - Skipped: {skipped}")
    print(f"  - Errors: {errors}")
    
    return migrated


if __name__ == "__main__":
    migrate_sessions()
