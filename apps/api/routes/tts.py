"""
TTS Preview Routes - 음성 미리듣기 API
채널 생성 과정에서 TTS 설정용
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from services.tts import tts_preview_service, TTSError


router = APIRouter(prefix="/api/tts", tags=["tts"])


# === Request/Response Models ===

class TTSPreviewRequest(BaseModel):
    """TTS 미리듣기 요청"""
    text: str
    speaker: Optional[str] = None
    session_id: Optional[str] = None
    instruct: Optional[str] = None  # 감정/스타일 지시 (예: "슬프게", "신나게", "차분하게")
    speed: Optional[float] = None   # 속도 (0.5-2.0, 기본 1.0)
    pitch: Optional[int] = None     # 피치 (-20 to +20, 기본 0)


class TTSPreviewResponse(BaseModel):
    """TTS 미리듣기 응답"""
    audio_base64: str
    duration: float
    voice_name: str
    text: str


class YouTubeExtractRequest(BaseModel):
    """YouTube 오디오 추출 요청"""
    url: str
    start_time: str  # "00:00:00" 또는 "MM:SS" 또는 초(seconds)
    end_time: str
    session_id: Optional[str] = None


class YouTubeExtractResponse(BaseModel):
    """YouTube 오디오 추출 응답"""
    audio_base64: str
    duration: float
    video_id: str
    ref_text: str
    quality_score: float


class ClonePreviewRequest(BaseModel):
    """보이스 클로닝 미리듣기 요청"""
    text: str
    ref_audio_base64: str
    ref_text: Optional[str] = None
    session_id: Optional[str] = None


class SampleAudioResponse(BaseModel):
    """샘플 오디오 응답"""
    voice_id: str
    filename: str
    prompt_text: str
    audio_base64: str


# === Endpoints ===

@router.get("/samples")
async def get_voice_samples(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50)
):
    """
    음성 샘플 목록 조회 (페이지네이션)
    
    YouTube에서 추출된 다양한 음성 샘플 목록을 반환합니다.
    """
    result = tts_preview_service.get_voice_samples(page=page, per_page=per_page)
    return result


@router.get("/sample/{voice_id}")
async def get_sample_audio(voice_id: str):
    """
    특정 음성 샘플 오디오 조회
    
    voice_id에 해당하는 샘플의 오디오와 정보를 반환합니다.
    """
    # 샘플 정보 조회
    info = tts_preview_service.get_sample_info(voice_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"샘플을 찾을 수 없습니다: {voice_id}")
    
    # 오디오 로드
    audio_base64 = tts_preview_service.get_sample_audio(voice_id)
    if not audio_base64:
        raise HTTPException(status_code=404, detail=f"오디오 파일을 찾을 수 없습니다: {voice_id}")
    
    return SampleAudioResponse(
        voice_id=voice_id,
        filename=info["filename"],
        prompt_text=info["prompt_text"],
        audio_base64=audio_base64
    )


@router.post("/preview", response_model=TTSPreviewResponse)
async def generate_tts_preview(request: TTSPreviewRequest):
    """
    TTS 미리듣기 생성
    
    기본 보이스(Sohee)로 텍스트를 음성으로 변환합니다.
    Rate limit: 10초당 3회
    """
    # Rate limit 체크
    session_id = request.session_id or "anonymous"
    if not tts_preview_service.check_rate_limit(session_id):
        wait_time = tts_preview_service.get_rate_limit_wait_time(session_id)
        raise HTTPException(
            status_code=429, 
            detail=f"요청이 너무 많습니다. {wait_time:.1f}초 후에 다시 시도해주세요."
        )
    
    # 텍스트 길이 제한
    if len(request.text) > 500:
        raise HTTPException(
            status_code=400,
            detail="텍스트는 500자 이내로 입력해주세요."
        )
    
    if len(request.text.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="텍스트를 입력해주세요."
        )
    
    try:
        result = await tts_preview_service.generate_preview(
            text=request.text,
            speaker=request.speaker,
            session_id=session_id,
            instruct=request.instruct,  # NEW
            speed=request.speed,        # NEW
            pitch=request.pitch         # NEW
        )
        return TTSPreviewResponse(
            audio_base64=result.audio_base64,
            duration=result.duration,
            voice_name=result.voice_name,
            text=result.text
        )
    except TTSError as e:
        raise HTTPException(status_code=500, detail=e.user_message)


@router.post("/extract-youtube", response_model=YouTubeExtractResponse)
async def extract_youtube_audio(request: YouTubeExtractRequest):
    """
    YouTube에서 오디오 추출
    
    지정된 YouTube URL에서 특정 구간의 오디오를 추출합니다.
    추출된 오디오는 보이스 클로닝에 사용할 수 있습니다.
    Rate limit: 10초당 3회
    """
    # Rate limit 체크
    session_id = request.session_id or "anonymous"
    if not tts_preview_service.check_rate_limit(session_id):
        wait_time = tts_preview_service.get_rate_limit_wait_time(session_id)
        raise HTTPException(
            status_code=429,
            detail=f"요청이 너무 많습니다. {wait_time:.1f}초 후에 다시 시도해주세요."
        )
    
    try:
        result = await tts_preview_service.extract_youtube_audio(
            url=request.url,
            start_time=request.start_time,
            end_time=request.end_time,
            session_id=session_id
        )
        return YouTubeExtractResponse(**result)
    except TTSError as e:
        raise HTTPException(status_code=500, detail=e.user_message)


@router.post("/clone-preview", response_model=TTSPreviewResponse)
async def clone_voice_preview(request: ClonePreviewRequest):
    """
    보이스 클로닝 미리듣기
    
    제공된 참조 오디오로 보이스를 클로닝하여 텍스트를 음성으로 변환합니다.
    Rate limit: 10초당 3회
    """
    # Rate limit 체크
    session_id = request.session_id or "anonymous"
    if not tts_preview_service.check_rate_limit(session_id):
        wait_time = tts_preview_service.get_rate_limit_wait_time(session_id)
        raise HTTPException(
            status_code=429,
            detail=f"요청이 너무 많습니다. {wait_time:.1f}초 후에 다시 시도해주세요."
        )
    
    # 텍스트 길이 제한
    if len(request.text) > 500:
        raise HTTPException(
            status_code=400,
            detail="텍스트는 500자 이내로 입력해주세요."
        )
    
    if len(request.text.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="텍스트를 입력해주세요."
        )
    
    try:
        result = await tts_preview_service.clone_voice_preview(
            text=request.text,
            ref_audio_base64=request.ref_audio_base64,
            ref_text=request.ref_text,
            session_id=session_id
        )
        return TTSPreviewResponse(
            audio_base64=result.audio_base64,
            duration=result.duration,
            voice_name=result.voice_name,
            text=result.text
        )
    except TTSError as e:
        raise HTTPException(status_code=500, detail=e.user_message)


@router.get("/test-text")
async def get_test_text(channel_name: str = Query("채널", description="채널 이름")):
    """
    기본 테스트 문장 반환
    
    TTS 미리듣기용 기본 테스트 문장을 반환합니다.
    """
    return {
        "text": tts_preview_service.get_default_test_text(channel_name)
    }


@router.get("/instruct-examples")
async def get_instruct_examples():
    """감정/스타일 지시어 예시 목록"""
    return {
        "emotions": [
            {"label": "기본", "value": "", "description": "기본 톤"},
            {"label": "신나게", "value": "신나고 밝은 목소리로", "description": "밝고 에너지 넘치는 톤"},
            {"label": "차분하게", "value": "차분하고 안정적인 목소리로", "description": "편안하고 안정적인 톤"},
            {"label": "슬프게", "value": "슬프고 감성적인 목소리로", "description": "감성적이고 우울한 톤"},
            {"label": "진지하게", "value": "진지하고 무거운 목소리로", "description": "진중하고 권위있는 톤"},
            {"label": "친근하게", "value": "친근하고 따뜻한 목소리로", "description": "다정하고 친밀한 톤"},
        ],
        "speed_range": {"min": 0.5, "max": 2.0, "default": 1.0, "step": 0.1},
        "pitch_range": {"min": -20, "max": 20, "default": 0, "step": 1}
    }


@router.get("/health")
async def tts_health():
    """TTS 서비스 상태 확인"""
    return {
        "status": "ok",
        "custom_voice_url": tts_preview_service.TTS_CUSTOM_URL,
        "clone_url": tts_preview_service.TTS_BASE_URL,
        "samples_available": len(tts_preview_service._load_samples())
    }
