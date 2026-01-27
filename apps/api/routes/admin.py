"""
Admin Routes - Using SQLite Database
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import json
import os
from datetime import datetime, timedelta
import random

from .auth import get_current_user, require_role, Role
from database import get_db
from models import User

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Data file paths (for channels/projects - not yet migrated)
DATA_DIR = "/data/routine/routine-studio-v2/data"
CHANNELS_FILE = f"{DATA_DIR}/channels.json"
PROJECTS_FILE = f"{DATA_DIR}/projects.json"


def load_json(filepath: str) -> dict | list:
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return {}


def load_channels() -> list:
    data = load_json(CHANNELS_FILE)
    return data if isinstance(data, list) else list(data.values()) if data else []


def load_projects() -> list:
    data = load_json(PROJECTS_FILE)
    return data if isinstance(data, list) else list(data.values()) if data else []


# ============ Members ============
@router.get("/members")
async def get_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    members = []
    channels = load_channels()
    projects = load_projects()

    for user in users:
        user_channels = [c for c in channels if c.get("owner_id") == user.id]
        user_projects = [p for p in projects if p.get("owner_id") == user.id]
        members.append({
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "role": user.role or "VIEWER",
            "is_active": True,
            "is_verified": True,
            "is_approved": user.is_approved or False,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login_at": user.created_at.isoformat() if user.created_at else None,
            "channel_count": len(user_channels),
            "project_count": len(user_projects)
        })
    return {"members": members}


@router.put("/members/{member_id}/approve")
async def approve_member(
    member_id: str,
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == member_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Member not found")

    user.is_approved = True
    db.commit()
    return {"success": True, "message": "Member approved"}


@router.put("/members/{member_id}/revoke")
async def revoke_member(
    member_id: str,
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == member_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Member not found")

    if member_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot revoke your own access")

    user.is_approved = False
    db.commit()
    return {"success": True, "message": "Member access revoked"}


@router.put("/members/{member_id}/role")
async def update_member_role(
    member_id: str,
    role: Role,
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == member_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Member not found")

    user.role = role.value
    db.commit()
    return {"success": True, "message": f"Role updated to {role.value}"}


@router.delete("/members/{member_id}")
async def delete_member(
    member_id: str,
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == member_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Member not found")

    if member_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    db.delete(user)
    db.commit()
    return {"success": True}


@router.get("/sessions")
async def get_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    users = db.query(User).limit(3).all()
    sessions = []
    for user in users:
        sessions.append({
            "id": f"sess_{user.id[:8]}",
            "member_id": user.id,
            "member_email": user.username,
            "member_name": user.name,
            "device_type": random.choice(["desktop", "mobile"]),
            "browser": random.choice(["Chrome", "Safari", "Firefox"]),
            "os": random.choice(["macOS", "Windows", "iOS", "Android"]),
            "ip_address": f"192.168.1.{random.randint(1, 255)}",
            "location": "Seoul, KR",
            "created_at": datetime.utcnow().isoformat(),
            "last_activity_at": datetime.utcnow().isoformat()
        })
    return {"sessions": sessions}


@router.delete("/sessions/{session_id}")
async def terminate_session(
    session_id: str,
    current_user: User = Depends(require_role(Role.ADMIN, Role.MANAGER))
):
    return {"success": True}


@router.get("/activity-logs")
async def get_activity_logs(
    limit: int = 100,
    action: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    users = db.query(User).limit(10).all()
    logs = []
    actions = ["login", "logout", "channel_create", "project_create", "settings_update"]

    for i, user in enumerate(users):
        for j in range(3):
            log_action = action if action else random.choice(actions)
            logs.append({
                "id": f"log_{i}_{j}",
                "member_id": user.id,
                "member_email": user.username,
                "member_name": user.name,
                "action": log_action,
                "resource_type": "channel" if "channel" in log_action else "project" if "project" in log_action else "user",
                "resource_id": None,
                "details": None,
                "ip_address": f"192.168.1.{random.randint(1, 255)}",
                "created_at": (datetime.utcnow() - timedelta(hours=i*2+j)).isoformat()
            })

    if action:
        logs = [l for l in logs if l["action"] == action]

    return {"logs": logs[:limit]}


# ============ Channels ============
@router.get("/channels")
async def get_channels(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    channels = load_channels()
    users = {u.id: u for u in db.query(User).all()}

    result = []
    for ch in channels:
        owner = users.get(ch.get("owner_id", ""))
        result.append({
            "id": ch.get("id"),
            "youtube_channel_id": ch.get("youtube_channel_id", ""),
            "channel_name": ch.get("name", "Unnamed"),
            "channel_url": ch.get("url"),
            "subscriber_count": ch.get("subscriber_count", 0),
            "video_count": ch.get("video_count", 0),
            "is_connected": ch.get("is_connected", False),
            "owner_id": ch.get("owner_id"),
            "owner_email": owner.username if owner else "",
            "owner_name": owner.name if owner else None,
            "created_at": ch.get("created_at"),
            "last_sync_at": ch.get("last_sync_at")
        })
    return {"channels": result}


@router.get("/channel-settings")
async def get_channel_settings(current_user: User = Depends(get_current_user)):
    channels = load_channels()
    settings = []
    for ch in channels:
        settings.append({
            "id": f"settings_{ch.get('id', '')}",
            "channel_id": ch.get("id"),
            "channel_name": ch.get("name", "Unnamed"),
            "auto_publish": ch.get("auto_publish", False),
            "default_language": ch.get("language", "ko"),
            "default_category": ch.get("category", "entertainment"),
            "thumbnail_style": ch.get("thumbnail_style", "default"),
            "voice_id": ch.get("voice_id"),
            "bgm_enabled": ch.get("bgm_enabled", True),
            "watermark_enabled": ch.get("watermark_enabled", False),
            "created_at": ch.get("created_at"),
            "updated_at": ch.get("updated_at", ch.get("created_at"))
        })
    return {"settings": settings}


@router.put("/channel-settings/{setting_id}")
async def update_channel_setting(
    setting_id: str,
    updates: dict,
    current_user: User = Depends(require_role(Role.ADMIN, Role.MANAGER))
):
    return {"success": True, "setting_id": setting_id}


@router.get("/characters")
async def get_characters(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    channels = load_channels()
    users = {u.id: u for u in db.query(User).all()}
    characters = []

    for ch in channels:
        if ch.get("character"):
            char = ch["character"]
            owner = users.get(ch.get("owner_id", ""))
            characters.append({
                "id": char.get("id", f"char_{ch.get('id', '')}"),
                "name": char.get("name", "AI Character"),
                "description": char.get("description"),
                "voice_id": char.get("voice_id"),
                "voice_name": char.get("voice_name"),
                "avatar_url": char.get("avatar_url"),
                "channel_id": ch.get("id"),
                "channel_name": ch.get("name"),
                "owner_id": ch.get("owner_id"),
                "owner_email": owner.username if owner else "",
                "is_active": True,
                "video_count": ch.get("video_count", 0),
                "created_at": char.get("created_at", ch.get("created_at")),
                "updated_at": char.get("updated_at", ch.get("created_at"))
            })
    return {"characters": characters}


# ============ Videos/Projects ============
@router.get("/projects")
async def get_projects(
    limit: int = 100,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    projects = load_projects()
    channels = load_channels()
    users = {u.id: u for u in db.query(User).all()}

    channel_map = {ch.get("id"): ch for ch in channels}

    result = []
    for proj in projects:
        ch = channel_map.get(proj.get("channel_id"), {})
        owner = users.get(proj.get("owner_id", ""))

        if status and proj.get("status") != status:
            continue

        result.append({
            "id": proj.get("id"),
            "title": proj.get("title", "Untitled"),
            "description": proj.get("description"),
            "status": proj.get("status", "draft"),
            "channel_id": proj.get("channel_id"),
            "channel_name": ch.get("name", "Unknown"),
            "owner_id": proj.get("owner_id"),
            "owner_email": owner.username if owner else "",
            "video_url": proj.get("video_url"),
            "thumbnail_url": proj.get("thumbnail_url"),
            "duration_seconds": proj.get("duration_seconds"),
            "created_at": proj.get("created_at"),
            "updated_at": proj.get("updated_at"),
            "published_at": proj.get("published_at")
        })

    return {"projects": result[:limit]}


@router.get("/scripts")
async def get_scripts(
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    projects = load_projects()
    channels = load_channels()

    channel_map = {ch.get("id"): ch for ch in channels}

    scripts = []
    for proj in projects:
        if proj.get("script"):
            ch = channel_map.get(proj.get("channel_id"), {})
            script = proj["script"]
            content = script if isinstance(script, str) else script.get("content", "")
            word_count = len(content.split())

            scripts.append({
                "id": f"script_{proj.get('id', '')}",
                "project_id": proj.get("id"),
                "project_title": proj.get("title", "Untitled"),
                "channel_id": proj.get("channel_id"),
                "channel_name": ch.get("name", "Unknown"),
                "owner_email": "",
                "content": content,
                "word_count": word_count,
                "estimated_duration_seconds": word_count * 0.5,
                "language": "ko",
                "created_at": proj.get("created_at"),
                "updated_at": proj.get("updated_at")
            })

    return {"scripts": scripts[:limit]}


@router.get("/media")
async def get_media(
    limit: int = 100,
    type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    projects = load_projects()

    assets = []
    for proj in projects:
        proj_id = proj.get('id', '')
        if proj.get("thumbnail_url"):
            assets.append({
                "id": f"thumb_{proj_id}",
                "project_id": proj_id,
                "project_title": proj.get("title", "Untitled"),
                "type": "thumbnail",
                "filename": f"thumbnail_{proj_id}.jpg",
                "url": proj["thumbnail_url"],
                "size_bytes": random.randint(50000, 500000),
                "mime_type": "image/jpeg",
                "width": 1280,
                "height": 720,
                "duration_seconds": None,
                "owner_email": "",
                "created_at": proj.get("created_at")
            })

        if proj.get("video_url"):
            assets.append({
                "id": f"video_{proj_id}",
                "project_id": proj_id,
                "project_title": proj.get("title", "Untitled"),
                "type": "video",
                "filename": f"video_{proj_id}.mp4",
                "url": proj["video_url"],
                "size_bytes": random.randint(10000000, 100000000),
                "mime_type": "video/mp4",
                "width": 1920,
                "height": 1080,
                "duration_seconds": proj.get("duration_seconds"),
                "owner_email": "",
                "created_at": proj.get("created_at")
            })

    if type:
        assets = [a for a in assets if a["type"] == type]

    return {"assets": assets[:limit]}


# ============ Analytics ============
@router.get("/analytics/overview")
async def get_analytics_overview(
    period: str = "30d",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_count = db.query(User).count()
    channels = load_channels()
    projects = load_projects()

    published = [p for p in projects if p.get("status") == "published"]

    days = int(period.replace("d", ""))
    change_factor = days / 30

    return {
        "total_members": user_count,
        "total_channels": len(channels),
        "total_projects": len(projects),
        "total_published_videos": len(published),
        "members_change": round(random.uniform(-5, 15) * change_factor, 1),
        "channels_change": round(random.uniform(-3, 10) * change_factor, 1),
        "projects_change": round(random.uniform(0, 20) * change_factor, 1),
        "videos_change": round(random.uniform(0, 25) * change_factor, 1),
        "recent_activity": [
            {"date": (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d"),
             "members": random.randint(0, 3),
             "projects": random.randint(0, 5),
             "videos": random.randint(0, 2)}
            for i in range(min(days, 14))
        ],
        "top_channels": [
            {"id": ch.get("id"), "name": ch.get("name", "Unknown"),
             "videos_count": ch.get("video_count", 0),
             "subscriber_count": ch.get("subscriber_count", 0)}
            for ch in sorted(channels, key=lambda x: x.get("video_count", 0), reverse=True)[:5]
        ]
    }


@router.get("/analytics/usage")
async def get_analytics_usage(
    period: str = "30d",
    current_user: User = Depends(get_current_user)
):
    days = int(period.replace("d", ""))

    return {
        "period": period,
        "api_calls": {
            "total": random.randint(1000, 10000) * (days // 7),
            "by_service": {
                "openai": random.randint(500, 3000),
                "tts": random.randint(200, 1000),
                "image_gen": random.randint(100, 500),
                "youtube": random.randint(50, 200)
            },
            "trend": round(random.uniform(-10, 20), 1)
        },
        "compute": {
            "total_minutes": random.randint(100, 1000) * (days // 7),
            "gpu_minutes": random.randint(50, 500),
            "cpu_minutes": random.randint(50, 500),
            "trend": round(random.uniform(-5, 15), 1)
        },
        "storage": {
            "total_gb": round(random.uniform(10, 100), 2),
            "media_gb": round(random.uniform(5, 80), 2),
            "database_gb": round(random.uniform(1, 10), 2),
            "trend": round(random.uniform(0, 10), 1)
        },
        "costs": {
            "total_usd": round(random.uniform(50, 500), 2),
            "api_usd": round(random.uniform(20, 200), 2),
            "compute_usd": round(random.uniform(20, 200), 2),
            "storage_usd": round(random.uniform(5, 50), 2),
            "trend": round(random.uniform(-15, 25), 1)
        },
        "daily_breakdown": [
            {"date": (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d"),
             "api_calls": random.randint(100, 500),
             "compute_minutes": random.randint(10, 100),
             "cost_usd": round(random.uniform(1, 20), 2)}
            for i in range(min(days, 14))
        ]
    }


# ============ Studio Integration (DB) ============
from models import Project, Character, Benchmark


@router.get("/studio/sessions")
async def get_studio_sessions(
    limit: int = 100,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """DB에서 Studio 세션(프로젝트) 목록 조회"""
    query = db.query(Project)
    
    if status:
        query = query.filter(Project.status == status)
    
    projects = query.order_by(Project.updated_at.desc()).limit(limit).all()
    
    result = []
    for p in projects:
        # 관련 캐릭터 수 조회
        char_count = db.query(Character).filter(Character.project_id == p.id).count()
        
        result.append({
            "id": p.id,
            "channel_name": p.channel_name,
            "user_request": p.user_request,
            "current_step": p.current_step,
            "status": p.status,
            "character_count": char_count,
            "has_benchmark": bool(p.context_json.get("benchmark_report")) if p.context_json else False,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None
        })
    
    return {"sessions": result, "total": len(result)}


@router.get("/studio/sessions/{session_id}")
async def get_studio_session_detail(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Studio 세션 상세 조회"""
    project = db.query(Project).filter(Project.id == session_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 관련 캐릭터 조회
    characters = db.query(Character).filter(Character.project_id == session_id).all()
    
    return {
        "id": project.id,
        "channel_name": project.channel_name,
        "user_request": project.user_request,
        "current_step": project.current_step,
        "status": project.status,
        "context": project.context_json,
        "characters": [
            {
                "id": c.id,
                "character_type": c.character_type,
                "gender": c.gender,
                "clothing": c.clothing,
                "expression": c.expression,
                "art_style": c.art_style,
                "personality": c.personality,
                "has_image": bool(c.image_base64)
            }
            for c in characters
        ],
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None
    }


@router.delete("/studio/sessions/{session_id}")
async def delete_studio_session(
    session_id: str,
    current_user: User = Depends(require_role(Role.ADMIN, Role.MANAGER)),
    db: Session = Depends(get_db)
):
    """Studio 세션 삭제"""
    project = db.query(Project).filter(Project.id == session_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(project)
    db.commit()
    return {"success": True, "message": "Session deleted"}


@router.get("/studio/benchmarks")
async def get_studio_benchmarks(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """DB에서 벤치마크 결과 목록 조회"""
    benchmarks = db.query(Benchmark).order_by(Benchmark.analyzed_at.desc()).limit(limit).all()
    
    result = []
    for b in benchmarks:
        result.append({
            "id": b.id,
            "project_id": b.project_id,
            "channel_url": b.channel_url,
            "channel_name": b.channel_name,
            "subscriber_count": b.subscriber_count,
            "video_count": b.video_count,
            "channel_concept": b.channel_concept[:200] if b.channel_concept else None,
            "analyzed_at": b.analyzed_at.isoformat() if b.analyzed_at else None
        })
    
    return {"benchmarks": result, "total": len(result)}


@router.get("/studio/benchmarks/{benchmark_id}")
async def get_studio_benchmark_detail(
    benchmark_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """벤치마크 상세 조회"""
    benchmark = db.query(Benchmark).filter(Benchmark.id == benchmark_id).first()
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    
    return {
        "id": benchmark.id,
        "project_id": benchmark.project_id,
        "channel_url": benchmark.channel_url,
        "channel_name": benchmark.channel_name,
        "subscriber_count": benchmark.subscriber_count,
        "video_count": benchmark.video_count,
        "channel_concept": benchmark.channel_concept,
        "unique_selling_point": benchmark.unique_selling_point,
        "brand_voice": benchmark.brand_voice,
        "thumbnail_pattern": benchmark.thumbnail_pattern,
        "script_pattern": benchmark.script_pattern,
        "content_strategy": benchmark.content_strategy,
        "audience_profile": benchmark.audience_profile,
        "replication_guide": benchmark.replication_guide,
        "analyzed_at": benchmark.analyzed_at.isoformat() if benchmark.analyzed_at else None
    }


@router.delete("/studio/benchmarks/{benchmark_id}")
async def delete_studio_benchmark(
    benchmark_id: int,
    current_user: User = Depends(require_role(Role.ADMIN, Role.MANAGER)),
    db: Session = Depends(get_db)
):
    """벤치마크 삭제"""
    benchmark = db.query(Benchmark).filter(Benchmark.id == benchmark_id).first()
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    
    db.delete(benchmark)
    db.commit()
    return {"success": True, "message": "Benchmark deleted"}


@router.get("/studio/characters")
async def get_studio_characters(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """DB에서 캐릭터 목록 조회"""
    characters = db.query(Character).order_by(Character.created_at.desc()).limit(limit).all()
    
    result = []
    for c in characters:
        # 관련 프로젝트 정보 조회
        project = db.query(Project).filter(Project.id == c.project_id).first()
        
        result.append({
            "id": c.id,
            "project_id": c.project_id,
            "channel_name": project.channel_name if project else None,
            "character_type": c.character_type,
            "gender": c.gender,
            "clothing": c.clothing,
            "expression": c.expression,
            "art_style": c.art_style,
            "personality": c.personality,
            "has_image": bool(c.image_base64),
            "created_at": c.created_at.isoformat() if c.created_at else None
        })
    
    return {"characters": result, "total": len(result)}


@router.get("/studio/characters/{character_id}")
async def get_studio_character_detail(
    character_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """캐릭터 상세 조회 (이미지 포함)"""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    project = db.query(Project).filter(Project.id == character.project_id).first()
    
    return {
        "id": character.id,
        "project_id": character.project_id,
        "channel_name": project.channel_name if project else None,
        "character_type": character.character_type,
        "gender": character.gender,
        "clothing": character.clothing,
        "expression": character.expression,
        "art_style": character.art_style,
        "personality": character.personality,
        "image_base64": character.image_base64,
        "created_at": character.created_at.isoformat() if character.created_at else None
    }


@router.get("/studio/overview")
async def get_studio_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Studio 대시보드 통계"""
    total_sessions = db.query(Project).count()
    active_sessions = db.query(Project).filter(Project.status == "in_progress").count()
    completed_sessions = db.query(Project).filter(Project.status == "completed").count()
    total_benchmarks = db.query(Benchmark).count()
    total_characters = db.query(Character).count()
    
    # 최근 세션 5개
    recent_sessions = db.query(Project).order_by(Project.updated_at.desc()).limit(5).all()
    
    # 단계별 통계
    step_counts = {}
    all_projects = db.query(Project).all()
    for p in all_projects:
        step = p.current_step or "unknown"
        step_counts[step] = step_counts.get(step, 0) + 1
    
    return {
        "total_sessions": total_sessions,
        "active_sessions": active_sessions,
        "completed_sessions": completed_sessions,
        "total_benchmarks": total_benchmarks,
        "total_characters": total_characters,
        "step_distribution": step_counts,
        "recent_sessions": [
            {
                "id": p.id,
                "channel_name": p.channel_name,
                "current_step": p.current_step,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None
            }
            for p in recent_sessions
        ]
    }
