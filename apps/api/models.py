"""
SQLAlchemy Models for Routine Studio
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Text, Boolean, DateTime,
    ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    """사용자 테이블 (기존 users.json 대체)"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    name = Column(String(100))
    role = Column(String(20), default="VIEWER")  # ADMIN, MANAGER, VIEWER
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    """프로젝트/세션 테이블"""
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    channel_name = Column(String(200))
    user_request = Column(Text)
    current_step = Column(String(50), default="channel_name")
    status = Column(String(20), default="in_progress")  # in_progress, completed, archived
    context_json = Column(JSON, default=dict)  # Store full context for backward compat
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="projects")
    benchmarks = relationship("Benchmark", back_populates="project", cascade="all, delete-orphan")
    characters = relationship("Character", back_populates="project", cascade="all, delete-orphan")
    content_ideas = relationship("ContentIdea", back_populates="project", cascade="all, delete-orphan")
    generated_assets = relationship("GeneratedAsset", back_populates="project", cascade="all, delete-orphan")


class Benchmark(Base):
    """벤치마킹 결과 테이블 (캐시 + 영구 저장)"""
    __tablename__ = "benchmarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("projects.id"), index=True)
    channel_url = Column(String(500), nullable=False, index=True)
    channel_name = Column(String(200))
    subscriber_count = Column(Integer)
    video_count = Column(Integer)
    channel_concept = Column(Text)
    unique_selling_point = Column(Text)
    brand_voice = Column(Text)
    thumbnail_pattern = Column(JSON)  # ThumbnailPattern as JSON
    script_pattern = Column(JSON)  # ScriptPattern as JSON
    content_strategy = Column(JSON)  # ContentStrategy as JSON
    audience_profile = Column(JSON)  # AudienceProfile as JSON
    replication_guide = Column(JSON)  # Full guide as JSON
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="benchmarks")

    __table_args__ = (
        Index("idx_benchmark_channel_url", "channel_url"),
    )


class Character(Base):
    """캐릭터 정보 테이블"""
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    character_type = Column(String(50))  # human, animal, fantasy
    gender = Column(String(20))
    clothing = Column(String(200))
    expression = Column(String(100))
    art_style = Column(String(100))
    personality = Column(String(200))
    image_path = Column(Text)  # Path to stored character image
    image_base64 = Column(Text)  # Or base64 encoded image
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="characters")


class ContentIdea(Base):
    """콘텐츠 아이디어 테이블"""
    __tablename__ = "content_ideas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    title = Column(String(300))
    hook = Column(Text)
    summary = Column(Text)
    script = Column(JSON)  # Script sections as JSON
    is_selected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="content_ideas")
    generated_assets = relationship("GeneratedAsset", back_populates="content_idea")


class GeneratedAsset(Base):
    """생성된 에셋 테이블"""
    __tablename__ = "generated_assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    content_idea_id = Column(Integer, ForeignKey("content_ideas.id"), index=True)
    asset_type = Column(String(50))  # image, video, audio, subtitle
    file_path = Column(Text, nullable=False)
    asset_metadata = Column(JSON)  # Additional metadata as JSON
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="generated_assets")
    content_idea = relationship("ContentIdea", back_populates="generated_assets")


# Helper functions for model serialization
def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "role": user.role,
        "is_approved": user.is_approved,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }


def project_to_dict(project: Project) -> dict:
    return {
        "id": project.id,
        "user_id": project.user_id,
        "channel_name": project.channel_name,
        "user_request": project.user_request,
        "current_step": project.current_step,
        "status": project.status,
        "context": project.context_json,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None
    }


def benchmark_to_dict(benchmark: Benchmark) -> dict:
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
