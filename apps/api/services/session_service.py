"""
Session Service - DB와 Session dict 간 변환 및 저장/로드
"""
import sys
from typing import Dict, Any, Optional
from datetime import datetime

sys.path.insert(0, "/app/apps/api")

from database import get_db_context
from models import Project, Character


def session_to_project(session_dict: Dict[str, Any], user_id: str = "default") -> Project:
    """Session dict를 Project 모델로 변환"""
    context = session_dict.get("context", {})
    
    return Project(
        id=session_dict["id"],
        user_id=user_id,
        channel_name=context.get("selected_channel_name"),
        user_request=context.get("user_request"),
        current_step=session_dict.get("current_step", "channel_name"),
        status="in_progress",
        context_json=context,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


def project_to_session_dict(project: Project) -> Dict[str, Any]:
    """Project 모델을 Session dict로 변환"""
    return {
        "id": project.id,
        "current_step": project.current_step,
        "context": project.context_json or {},
        "history": project.context_json.get("history", []) if project.context_json else []
    }


def save_session_to_db(session_dict: Dict[str, Any], user_id: str = "default") -> bool:
    """세션을 DB에 저장"""
    try:
        with get_db_context() as db:
            session_id = session_dict["id"]
            context = session_dict.get("context", {})
            
            # 기존 프로젝트 검색
            project = db.query(Project).filter(Project.id == session_id).first()
            
            if project:
                # 업데이트
                project.channel_name = context.get("selected_channel_name")
                project.user_request = context.get("user_request")
                project.current_step = session_dict.get("current_step", "channel_name")
                project.context_json = context
                project.updated_at = datetime.utcnow()
            else:
                # 새로 생성
                project = session_to_project(session_dict, user_id)
                db.add(project)
            
            # 캐릭터 정보 추출 및 저장
            _save_character_if_present(db, session_id, context)
            
            db.commit()
            print(f"[SessionService] Saved session {session_id} to DB")
            return True
            
    except Exception as e:
        print(f"[SessionService] Error saving session to DB: {e}")
        return False


def load_session_from_db(session_id: str) -> Optional[Dict[str, Any]]:
    """DB에서 세션 로드"""
    try:
        with get_db_context() as db:
            project = db.query(Project).filter(Project.id == session_id).first()
            
            if not project:
                print(f"[SessionService] Session {session_id} not found in DB")
                return None
            
            session_dict = project_to_session_dict(project)
            print(f"[SessionService] Loaded session {session_id} from DB")
            return session_dict
            
    except Exception as e:
        print(f"[SessionService] Error loading session from DB: {e}")
        return None


def _save_character_if_present(db, project_id: str, context: Dict[str, Any]):
    """context에서 캐릭터 정보 추출하여 저장"""
    char_info = context.get("character_info")
    char_image = context.get("character_image")
    
    if not char_info and not char_image:
        return
    
    # 기존 캐릭터 검색
    existing = db.query(Character).filter(Character.project_id == project_id).first()
    
    if existing:
        # 업데이트
        if char_info:
            existing.character_type = char_info.get("character_type")
            existing.gender = char_info.get("gender")
            existing.clothing = char_info.get("clothing")
            existing.expression = char_info.get("expression")
            existing.art_style = char_info.get("art_style")
            existing.personality = char_info.get("personality_vibe")
        if char_image:
            existing.image_base64 = char_image
    else:
        # 새로 생성
        character = Character(
            project_id=project_id,
            character_type=char_info.get("character_type") if char_info else None,
            gender=char_info.get("gender") if char_info else None,
            clothing=char_info.get("clothing") if char_info else None,
            expression=char_info.get("expression") if char_info else None,
            art_style=char_info.get("art_style") if char_info else None,
            personality=char_info.get("personality_vibe") if char_info else None,
            image_base64=char_image
        )
        db.add(character)


def list_sessions_from_db(user_id: str = None, limit: int = 50) -> list:
    """DB에서 세션 목록 조회"""
    try:
        with get_db_context() as db:
            query = db.query(Project)
            if user_id:
                query = query.filter(Project.user_id == user_id)
            projects = query.order_by(Project.updated_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": p.id,
                    "channel_name": p.channel_name,
                    "user_request": p.user_request,
                    "current_step": p.current_step,
                    "status": p.status,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None
                }
                for p in projects
            ]
    except Exception as e:
        print(f"[SessionService] Error listing sessions: {e}")
        return []


def delete_session_from_db(session_id: str) -> bool:
    """DB에서 세션 삭제"""
    try:
        with get_db_context() as db:
            project = db.query(Project).filter(Project.id == session_id).first()
            if project:
                db.delete(project)
                db.commit()
                print(f"[SessionService] Deleted session {session_id} from DB")
                return True
            return False
    except Exception as e:
        print(f"[SessionService] Error deleting session: {e}")
        return False
