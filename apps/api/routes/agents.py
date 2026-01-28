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

sys.path.append("/app")

from agents.orchestrator import orchestrator, SESSIONS_DIR
from apps.api.services.session_service import delete_session_from_db

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



class MessageStreamRequest(BaseModel):
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
        progress_store[_current_session_id].append({"status": status, "detail": detail})
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
        result = await orchestrator.start(
            session_id, {"user_request": request.user_request}
        )
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
            session_id, request.message, request.images
        )
        emit_progress("완료", "")
        return AgentResponse(**result)
    except Exception as e:
        emit_progress("오류", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message/stream")
async def process_message_stream_post(request: MessageStreamRequest):
    """POST version for large image payloads"""
    return await _message_stream_internal(request.session_id, request.message, request.images)


@router.get("/message/stream")
async def process_message_stream(session_id: str, message: str, images: str = ""):
    """SSE 스트리밍으로 메시지 처리 및 진행 상황 전달"""
    image_list = json.loads(images) if images else []
    return await _message_stream_internal(session_id, message, image_list)


async def _message_stream_internal(session_id: str, message: str, image_list: list):
    """Internal streaming handler"""

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
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """세션 상태 조회 (메모리 또는 디스크에서 로드)"""
    # 먼저 메모리에서 확인
    session = orchestrator.sessions.get(session_id)
    
    # 메모리에 없으면 디스크에서 로드
    if not session:
        session = orchestrator.get_or_create_session(session_id)
        # 새로 생성된 세션인지 확인 (history가 없으면 새 세션)
        if not session.history and session.current_step.value == "channel_name":
            # 새로 생성된 빈 세션이면 404 반환
            raise HTTPException(status_code=404, detail="Session not found")
    
    return session.to_dict()


@router.post("/go-to-step")
async def go_to_step_endpoint(session_id: str, step: str):
    """특정 단계로 이동"""
    from agents.orchestrator import WorkflowStep

    session = orchestrator.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        target_step = WorkflowStep(step)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid step: {step}")

    result = orchestrator.go_to_step(session, target_step)
    orchestrator._save(session)

    return {
        "success": result.status.value == "success",
        "message": result.message,
        "current_step": session.current_step.value,
        "session_id": session_id,
    }


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

    output_base = Path("/app/output")
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

    # DB에서도 삭제
    if delete_session_from_db(session_id):
        deleted_items.append("db_project")

    return {"success": True, "session_id": session_id, "deleted": deleted_items}
