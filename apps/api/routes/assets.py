import os
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sys

sys.path.append('/app')

from apps.api.services.storage import storage_service

router = APIRouter(prefix='/api/assets', tags=['assets'])

class SaveImageRequest(BaseModel):
    user_id: str
    channel_id: str
    project_id: str
    asset_type: str
    base64_data: str
    filename: Optional[str] = None

class SaveTextRequest(BaseModel):
    user_id: str
    channel_id: str
    project_id: str
    asset_type: str
    content: str
    filename: Optional[str] = None

@router.post('/image')
async def save_image(request: SaveImageRequest):
    """이미지 저장"""
    try:
        path = storage_service.save_image_base64(
            request.user_id,
            request.channel_id,
            request.project_id,
            request.asset_type,
            request.base64_data,
            request.filename
        )
        return {'success': True, 'path': path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/text')
async def save_text(request: SaveTextRequest):
    """텍스트 파일 저장"""
    try:
        path = storage_service.save_text(
            request.user_id,
            request.channel_id,
            request.project_id,
            request.asset_type,
            request.content,
            request.filename
        )
        return {'success': True, 'path': path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/list/{user_id}/{channel_id}/{project_id}')
async def list_assets(
    user_id: str,
    channel_id: str,
    project_id: str,
    asset_type: Optional[str] = None
):
    """에셋 목록 조회"""
    try:
        assets = storage_service.list_assets(
            user_id, channel_id, project_id, asset_type
        )
        return {'success': True, 'assets': assets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/file')
async def get_file(path: str):
    """파일 다운로드"""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail='File not found')
    
    # 보안: output 폴더 내 파일만 허용
    if '/output/' not in path:
        raise HTTPException(status_code=403, detail='Forbidden')
    
    return FileResponse(path)
