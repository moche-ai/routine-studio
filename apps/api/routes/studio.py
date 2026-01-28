"""
Studio Routes - 어드민 대시보드용 공개 API
인증 없이 접근 가능 (내부 네트워크 전용)
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from database import get_db
from models import User, Project, Character, Benchmark

router = APIRouter(prefix="/api/studio", tags=["studio"])


# ============ Members ============
@router.get("/admin/members")
async def get_members(db: Session = Depends(get_db)):
    """멤버 목록 조회"""
    users = db.query(User).all()
    members = []
    
    for user in users:
        project_count = db.query(Project).filter(Project.user_id == user.id).count()
        members.append({
            "id": user.id,
            "email": user.username,
            "name": user.name,
            "role": user.role or "VIEWER",
            "is_active": True,
            "is_verified": True,
            "is_approved": user.is_approved or False,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login_at": user.created_at.isoformat() if user.created_at else None,
            "channel_count": 0,
            "project_count": project_count
        })
    return {"members": members}


# ============ Sessions ============
@router.get("/admin/sessions")
async def get_sessions(db: Session = Depends(get_db)):
    """활성 세션 목록"""
    projects = db.query(Project).filter(Project.status == "in_progress").limit(20).all()
    sessions = []
    
    for p in projects:
        user = db.query(User).filter(User.id == p.user_id).first()
        sessions.append({
            "id": p.id[:8],
            "member_id": p.user_id,
            "member_email": user.username if user else "unknown",
            "member_name": user.name if user else None,
            "device_type": "desktop",
            "browser": "Chrome",
            "os": "Unknown",
            "ip_address": "internal",
            "location": "Studio",
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "last_activity_at": p.updated_at.isoformat() if p.updated_at else None
        })
    return {"sessions": sessions}


# ============ Activity Logs ============
@router.get("/admin/activity-logs")
async def get_activity_logs(limit: int = 100, db: Session = Depends(get_db)):
    """활동 로그"""
    projects = db.query(Project).order_by(Project.updated_at.desc()).limit(limit).all()
    logs = []
    
    for i, p in enumerate(projects):
        user = db.query(User).filter(User.id == p.user_id).first()
        logs.append({
            "id": f"log_{i}",
            "member_id": p.user_id,
            "member_email": user.username if user else "unknown",
            "member_name": user.name if user else None,
            "action": "session_update",
            "resource_type": "session",
            "resource_id": p.id,
            "details": p.current_step,
            "ip_address": "internal",
            "created_at": p.updated_at.isoformat() if p.updated_at else None
        })
    return {"logs": logs}


# ============ Channels ============
@router.get("/admin/channels")
async def get_channels(db: Session = Depends(get_db)):
    """채널 목록 (프로젝트 기반)"""
    projects = db.query(Project).filter(Project.channel_name != None).all()
    channels = []
    
    for p in projects:
        user = db.query(User).filter(User.id == p.user_id).first()
        channels.append({
            "id": p.id,
            "youtube_channel_id": None,
            "channel_name": p.channel_name,
            "channel_url": None,
            "subscriber_count": 0,
            "video_count": 0,
            "is_connected": False,
            "owner_id": p.user_id,
            "owner_email": user.username if user else None,
            "owner_name": user.name if user else None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "last_sync_at": None
        })
    return {"channels": channels}


@router.get("/admin/channel-settings")
async def get_channel_settings(db: Session = Depends(get_db)):
    """채널 설정"""
    projects = db.query(Project).filter(Project.channel_name != None).all()
    settings = []
    
    for p in projects:
        settings.append({
            "id": f"settings_{p.id[:8]}",
            "channel_id": p.id,
            "channel_name": p.channel_name,
            "auto_publish": False,
            "default_language": "ko",
            "default_category": "entertainment",
            "thumbnail_style": "default",
            "voice_id": None,
            "bgm_enabled": True,
            "watermark_enabled": False,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None
        })
    return {"settings": settings}


# ============ Characters ============
@router.get("/admin/characters")
async def get_characters(db: Session = Depends(get_db)):
    """캐릭터 목록"""
    characters = db.query(Character).all()
    result = []
    
    for c in characters:
        project = db.query(Project).filter(Project.id == c.project_id).first()
        user = db.query(User).filter(User.id == project.user_id).first() if project else None
        
        result.append({
            "id": c.id,
            "name": c.personality or "AI Character",
            "description": f"{c.character_type or ''} {c.gender or ''} {c.art_style or ''}".strip(),
            "voice_id": None,
            "voice_name": None,
            "avatar_url": None,
            "channel_id": c.project_id,
            "channel_name": project.channel_name if project else None,
            "owner_id": project.user_id if project else None,
            "owner_email": user.username if user else None,
            "is_active": True,
            "video_count": 0,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.created_at.isoformat() if c.created_at else None
        })
    return {"characters": result}


# ============ Projects ============
@router.get("/admin/projects")
async def get_projects(limit: int = 100, status: Optional[str] = None, db: Session = Depends(get_db)):
    """프로젝트 목록"""
    query = db.query(Project)
    if status:
        query = query.filter(Project.status == status)
    projects = query.order_by(Project.updated_at.desc()).limit(limit).all()
    
    result = []
    for p in projects:
        user = db.query(User).filter(User.id == p.user_id).first()
        result.append({
            "id": p.id,
            "title": p.channel_name or p.user_request or "Untitled",
            "description": p.user_request,
            "status": p.status,
            "channel_id": p.id,
            "channel_name": p.channel_name,
            "owner_id": p.user_id,
            "owner_email": user.username if user else None,
            "video_url": None,
            "thumbnail_url": None,
            "duration_seconds": None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "published_at": None
        })
    return {"projects": result}


# ============ Scripts ============
@router.get("/admin/scripts")
async def get_scripts(limit: int = 100, db: Session = Depends(get_db)):
    """스크립트 목록"""
    projects = db.query(Project).filter(Project.context_json.isnot(None)).limit(limit).all()
    scripts = []
    
    for p in projects:
        context = p.context_json or {}
        script = context.get("script")
        if script:
            content = script.get("full_script", "") if isinstance(script, dict) else str(script)
            word_count = len(content.split())
            
            scripts.append({
                "id": f"script_{p.id[:8]}",
                "project_id": p.id,
                "project_title": p.channel_name or "Untitled",
                "channel_id": p.id,
                "channel_name": p.channel_name,
                "owner_email": None,
                "content": content[:500] + "..." if len(content) > 500 else content,
                "word_count": word_count,
                "estimated_duration_seconds": word_count * 0.5,
                "language": "ko",
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None
            })
    return {"scripts": scripts}


# ============ Media ============
@router.get("/admin/media")
async def get_media(limit: int = 100, type: Optional[str] = None, db: Session = Depends(get_db)):
    """미디어 에셋 목록"""
    characters = db.query(Character).filter(Character.image_base64 != None).limit(limit).all()
    assets = []
    
    for c in characters:
        project = db.query(Project).filter(Project.id == c.project_id).first()
        assets.append({
            "id": f"char_img_{c.id}",
            "project_id": c.project_id,
            "project_title": project.channel_name if project else "Unknown",
            "type": "image",
            "filename": f"character_{c.id}.png",
            "url": None,
            "size_bytes": len(c.image_base64) if c.image_base64 else 0,
            "mime_type": "image/png",
            "width": 512,
            "height": 512,
            "duration_seconds": None,
            "owner_email": None,
            "created_at": c.created_at.isoformat() if c.created_at else None
        })
    
    if type:
        assets = [a for a in assets if a["type"] == type]
    
    return {"assets": assets}


# ============ Analytics ============
@router.get("/admin/analytics/overview")
async def get_analytics_overview(period: str = "30d", db: Session = Depends(get_db)):
    """분석 개요"""
    user_count = db.query(User).count()
    project_count = db.query(Project).count()
    active_count = db.query(Project).filter(Project.status == "in_progress").count()
    character_count = db.query(Character).count()
    benchmark_count = db.query(Benchmark).count()
    
    return {
        "total_members": user_count,
        "total_channels": project_count,
        "total_projects": project_count,
        "total_published_videos": 0,
        "members_change": 0,
        "channels_change": 0,
        "projects_change": 0,
        "videos_change": 0,
        "recent_activity": [],
        "top_channels": [],
        "extra": {
            "active_sessions": active_count,
            "total_characters": character_count,
            "total_benchmarks": benchmark_count
        }
    }


@router.get("/admin/analytics/usage")
async def get_analytics_usage(period: str = "30d", db: Session = Depends(get_db)):
    """사용량 통계"""
    project_count = db.query(Project).count()
    
    return {
        "period": period,
        "api_calls": {
            "total": project_count * 10,
            "by_service": {
                "llm": project_count * 5,
                "image_gen": project_count * 2,
                "tts": project_count,
                "youtube": project_count
            },
            "trend": 0
        },
        "compute": {
            "total_minutes": project_count * 5,
            "gpu_minutes": project_count * 2,
            "cpu_minutes": project_count * 3,
            "trend": 0
        },
        "storage": {
            "total_gb": 0.5,
            "media_gb": 0.3,
            "database_gb": 0.2,
            "trend": 0
        },
        "costs": {
            "total_usd": 0,
            "api_usd": 0,
            "compute_usd": 0,
            "storage_usd": 0,
            "trend": 0
        },
        "daily_breakdown": []
    }

# ============ DELETE Operations ============
import os
import shutil
import logging

logger = logging.getLogger(__name__)


def cleanup_session_files(session_id: str, base_path: str = "/app"):
    """세션 관련 파일 정리"""
    cleaned = []
    
    # 1. JSON 세션 파일 삭제
    session_json = os.path.join(base_path, "sessions", f"{session_id}.json")
    if os.path.exists(session_json):
        os.remove(session_json)
        cleaned.append(session_json)
    
    # 2. 세션별 에셋 폴더 삭제
    assets_dir = os.path.join(base_path, "assets", session_id)
    if os.path.exists(assets_dir):
        shutil.rmtree(assets_dir)
        cleaned.append(assets_dir)
    
    # 3. 세션별 outputs 폴더 삭제
    outputs_dir = os.path.join(base_path, "outputs", session_id)
    if os.path.exists(outputs_dir):
        shutil.rmtree(outputs_dir)
        cleaned.append(outputs_dir)
    
    return cleaned


def cleanup_generated_assets(project, base_path: str = "/app"):
    """GeneratedAsset의 file_path 파일들 삭제"""
    cleaned = []
    
    for asset in project.generated_assets:
        if asset.file_path and os.path.exists(asset.file_path):
            try:
                os.remove(asset.file_path)
                cleaned.append(asset.file_path)
            except Exception as e:
                logger.warning(f"Failed to delete asset file {asset.file_path}: {e}")
    
    return cleaned


@router.delete("/admin/sessions/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db)):
    """세션 삭제 (DB + 파일)"""
    # 짧은 ID로 조회 시 전체 ID 찾기
    if len(session_id) <= 8:
        project = db.query(Project).filter(Project.id.like(f"{session_id}%")).first()
    else:
        project = db.query(Project).filter(Project.id == session_id).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Session not found")
    
    full_id = project.id
    
    # 파일 정리
    cleaned_files = cleanup_session_files(full_id)
    cleaned_assets = cleanup_generated_assets(project)
    
    # DB 삭제 (cascade로 관련 데이터 자동 삭제)
    db.delete(project)
    db.commit()
    
    return {
        "success": True,
        "deleted_session_id": full_id,
        "cleaned_files": cleaned_files + cleaned_assets
    }


@router.delete("/admin/projects/{project_id}")
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    """프로젝트 삭제 (세션 삭제와 동일)"""
    return await delete_session(project_id, db)


@router.delete("/admin/channels/{channel_id}")
async def delete_channel(channel_id: str, db: Session = Depends(get_db)):
    """채널 삭제 (프로젝트 삭제와 동일)"""
    return await delete_session(channel_id, db)


@router.delete("/admin/characters/{character_id}")
async def delete_character(character_id: int, db: Session = Depends(get_db)):
    """캐릭터 삭제"""
    character = db.query(Character).filter(Character.id == character_id).first()
    
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    cleaned_files = []
    
    # 캐릭터 이미지 파일 삭제
    if character.image_path and os.path.exists(character.image_path):
        try:
            os.remove(character.image_path)
            cleaned_files.append(character.image_path)
        except Exception as e:
            logger.warning(f"Failed to delete character image: {e}")
    
    db.delete(character)
    db.commit()
    
    return {
        "success": True,
        "deleted_character_id": character_id,
        "cleaned_files": cleaned_files
    }


@router.delete("/admin/benchmarks/{benchmark_id}")
async def delete_benchmark(benchmark_id: int, db: Session = Depends(get_db)):
    """벤치마크 삭제"""
    benchmark = db.query(Benchmark).filter(Benchmark.id == benchmark_id).first()
    
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    
    # 벤치마크 캐시 JSON 파일 삭제
    cleaned_files = []
    cache_dir = "/app/benchmark_cache"
    
    if benchmark.channel_url:
        # cache_key 생성해서 파일 찾기
        handle = benchmark.channel_url.split("/")[-1].lstrip("@")
        for ext in [".json"]:
            cache_file = os.path.join(cache_dir, f"{handle}{ext}")
            if os.path.exists(cache_file):
                os.remove(cache_file)
                cleaned_files.append(cache_file)
    
    db.delete(benchmark)
    db.commit()
    
    return {
        "success": True,
        "deleted_benchmark_id": benchmark_id,
        "cleaned_files": cleaned_files
    }


@router.delete("/admin/members/{member_id}")
async def delete_member(member_id: str, db: Session = Depends(get_db)):
    """멤버 삭제 (관련 모든 데이터 cascade 삭제)"""
    user = db.query(User).filter(User.id == member_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # 해당 유저의 모든 프로젝트 파일 정리
    cleaned_files = []
    for project in user.projects:
        cleaned_files.extend(cleanup_session_files(project.id))
        cleaned_files.extend(cleanup_generated_assets(project))
    
    # DB 삭제 (cascade로 관련 데이터 자동 삭제)
    db.delete(user)
    db.commit()
    
    return {
        "success": True,
        "deleted_member_id": member_id,
        "cleaned_files": cleaned_files
    }
