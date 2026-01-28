"""Routine Studio API 중앙 설정

환경변수 또는 .env 파일에서 설정을 로드합니다.
Docker 환경에서는 172.17.0.1 (gateway)을 기본값으로 사용합니다.
"""

import os
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """API 서버 설정"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # === Server ===
    host: str = Field(default="0.0.0.0", description="API 서버 호스트")
    port: int = Field(default=18002, description="API 서버 포트")
    debug: bool = Field(default=False, description="디버그 모드")
    
    # === CORS ===
    cors_origins: str = Field(
        default="http://100.82.192.109:5182,http://100.82.192.109:5183,http://100.82.192.109:15182,http://localhost:5173,http://localhost:5182,http://localhost:5183",
        description="CORS 허용 오리진 (쉼표로 구분)"
    )
    
    # === Auth ===
    jwt_secret: str = Field(
        default="routine-studio-secret-key-change-in-production",
        description="JWT 시크릿 키"
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_hours: int = Field(default=24)
    
    # === AI Services (Docker gateway: 172.17.0.1) ===
    vision_api_url: str = Field(
        default="http://172.17.0.1:8016/v1",
        description="Qwen3-VL Vision API"
    )
    vision_model: str = Field(default="qwen3-vl-30b")
    
    llm_api_url: str = Field(
        default="http://172.17.0.1:8017/v1",
        description="LLM API (gpt-oss-120b)"
    )
    llm_model: str = Field(default="gpt-oss-120b-longctx")
    
    tts_base_url: str = Field(
        default="http://172.17.0.1:8310",
        description="TTS Base (클로닝)"
    )
    tts_custom_url: str = Field(
        default="http://172.17.0.1:8311",
        description="TTS Custom (프리셋)"
    )
    tts_design_url: str = Field(
        default="http://172.17.0.1:8312",
        description="TTS VoiceDesign"
    )
    
    comfyui_url: str = Field(
        default="http://172.17.0.1:8188",
        description="ComfyUI API"
    )
    
    whisper_url: str = Field(
        default="http://172.17.0.1:8400",
        description="Whisper STT API"
    )
    
    # === Music Generation ===
    diffrhythm_url: str = Field(
        default="http://172.17.0.1:8601",
        description="DiffRhythm2 음악 생성"
    )
    acestep_url: str = Field(
        default="http://172.17.0.1:8700",
        description="ACE-Step 음악 생성"
    )
    
    # === External APIs ===
    gemini_api_key: str = Field(default="", description="Gemini API Key")
    groq_api_key: str = Field(default="", description="Groq API Key")
    openrouter_api_key: str = Field(default="", description="OpenRouter API Key")
    anthropic_api_key: str = Field(default="", description="Anthropic API Key")
    
    # === GCP ===
    gcp_project_id: str = Field(default="", description="GCP Project ID")
    gcp_location: str = Field(default="us-central1")
    google_application_credentials: str = Field(default="")
    
    # === Storage ===
    output_dir: str = Field(default="/app/output", description="출력 디렉토리")
    data_dir: str = Field(default="/data/dbs/routine/youtube-studio")
    
    # === Database ===
    database_url: str = Field(
        default="sqlite:///./routine_studio.db",
        description="SQLite DB URL"
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """CORS origins를 리스트로 반환"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """설정 싱글톤 반환"""
    return Settings()


# 싱글톤 인스턴스
settings = get_settings()
