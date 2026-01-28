"""에이전트 전용 설정

에이전트 모듈에서 사용하는 서비스 URL 설정입니다.
Docker 환경에서는 172.17.0.1 (gateway)을 기본값으로 사용합니다.
"""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """에이전트 서비스 URL 설정"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # === TTS Services ===
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
    
    # === Vision Service ===
    vision_api_url: str = Field(
        default="http://172.17.0.1:8016/v1",
        description="Vision API"
    )
    vision_model: str = Field(default="qwen3-vl-30b")
    
    # === LLM Service ===
    llm_api_url: str = Field(
        default="http://172.17.0.1:8017/v1",
        description="LLM API"
    )
    llm_model: str = Field(default="gpt-oss-120b-longctx")
    
    # === ComfyUI ===
    comfyui_url: str = Field(
        default="http://172.17.0.1:8188",
        description="ComfyUI API"
    )
    
    # === Whisper ===
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
    
    # === Frontend (E2E Test) ===
    frontend_url: str = Field(
        default="http://localhost:5183",
        description="Frontend URL for testing"
    )


@lru_cache
def get_agent_settings() -> AgentSettings:
    """설정 싱글톤 반환"""
    return AgentSettings()


# 싱글톤 인스턴스
agent_settings = get_agent_settings()
