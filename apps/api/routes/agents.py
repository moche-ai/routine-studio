import uuid
import shutil
import asyncio
import json
from pathlib import Path
from typing import List, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import sys

sys.path.append("/data/routine/routine-studio-v2")

from agents.orchestrator import orchestrator, SESSIONS_DIR

router = APIRouter(prefix="/api/agents", tags=["agents"])

# 진행 상황 저장소 (세션별)
progress_store: dict = {}

# 현재 세션 ID
_current_session_id: str = ""

class StartRequest(BaseModel):
    user_request: str
    session_id: Optional[str] = None

class MessageRequest(BaseModel):
    session_id: str
    message: str
    images: List[str] = []

class AgentResponse(BaseModel):
    session_id: str
    current_step: str
    message: str
    images: List[str] = []
    needs_feedback: bool = False
    data: Optional[dict] = None
    success: bool = True

def emit_progress(status: str, detail: str = ""):
    """진행 상황 이벤트 발생"""
    global _current_session_id
    if _current_session_id and _current_session_id in progress_store:
        progress_store[_current_session_id].append({
            "status": status,
            "detail": detail
        })
        print(f"[Progress] {status}: {detail}")

def set_current_session(session_id: str):
    """현재 세션 ID 설정"""
    global _current_session_id
    _current_session_id = session_id
    if session_id not in progress_store:
        progress_store[session_id] = []

# 글로벌 진행 상황 발생 함수
import builtins
builtins.emit_agent_progress = emit_progress

@router.post("/start", response_model=AgentResponse)
async def start_workflow(request: StartRequest):
    """워크플로우 시작"""
    session_id = request.session_id or str(uuid.uuid4())
    set_current_session(session_id)
    
    try:
        emit_progress("시작", "워크플로우를 초기화하는 중...")
        result = await orchestrator.start(session_id, {
            "user_request": request.user_request
        })
        emit_progress("완료", "")
        return AgentResponse(**result)
    except Exception as e:
        emit_progress("오류", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/message", response_model=AgentResponse)
async def process_message(request: MessageRequest):
    """사용자 메시지 처리"""
    session_id = request.session_id
    set_current_session(session_id)
    
    try:
        result = await orchestrator.process_message(
            session_id,
            request.message,
            request.images
        )
        emit_progress("완료", "")
        return AgentResponse(**result)
    except Exception as e:
        emit_progress("오류", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/message/stream")
async def process_message_stream(session_id: str, message: str, images: str = ""):
    """SSE 스트리밍으로 메시지 처리 및 진행 상황 전달"""
    image_list = json.loads(images) if images else []
    
    async def event_generator() -> AsyncGenerator[str, None]:
        set_current_session(session_id)
        progress_store[session_id] = []
        
        yield f"data: {json.dumps({'type': 'progress', 'status': '처리 시작', 'detail': ''})}\n\n"
        
        try:
            task = asyncio.create_task(
                orchestrator.process_message(session_id, message, image_list)
            )
            
            last_idx = 0
            while not task.done():
                await asyncio.sleep(0.2)
                
                if session_id in progress_store:
                    for i in range(last_idx, len(progress_store[session_id])):
                        prog = progress_store[session_id][i]
                        yield f"data: {json.dumps({'type': 'progress', 'status': prog['status'], 'detail': prog['detail']})}\n\n"
                    last_idx = len(progress_store[session_id])
            
            result = await task
            yield f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """세션 상태 조회"""
    session = orchestrator.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """세션 및 관련 에셋 삭제"""
    deleted_items = []
    
    if session_id in orchestrator.sessions:
        del orchestrator.sessions[session_id]
        deleted_items.append("memory_session")
    
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if session_file.exists():
        session_file.unlink()
        deleted_items.append("session_file")
    
    output_base = Path("/data/routine/routine-studio-v2/output")
    for item in output_base.rglob("*"):
        if item.is_dir() and session_id in item.name:
            try:
                shutil.rmtree(item)
                deleted_items.append(f"asset_dir:{item}")
            except Exception as e:
                print(f"Failed to delete {item}: {e}")
    
    if session_id in progress_store:
        del progress_store[session_id]
    
    # 벤치마커 에이전트 정리
    if session_id in orchestrator.benchmarker_agents:
        del orchestrator.benchmarker_agents[session_id]
        deleted_items.append("benchmarker_agent")
    
    return {
        "success": True,
        "session_id": session_id,
        "deleted": deleted_items
    }
