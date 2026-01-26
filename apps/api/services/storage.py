import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import base64

BASE_OUTPUT_DIR = Path('/data/routine/routine-studio-v2/output')

class StorageService:
    """에셋 저장 서비스"""
    
    ASSET_TYPES = {
        'characters': 'characters',
        'thumbnails': 'thumbnails',
        'storyboards': 'storyboards',
        'audio': 'audio',
        'videos': 'videos',
        'scripts': 'scripts',
        'temp': 'temp'
    }
    
    def __init__(self):
        BASE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    def get_project_path(
        self,
        user_id: str,
        channel_id: str,
        project_id: str
    ) -> Path:
        """프로젝트별 경로 반환"""
        path = BASE_OUTPUT_DIR / user_id / channel_id / project_id
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_asset_path(
        self,
        user_id: str,
        channel_id: str,
        project_id: str,
        asset_type: str
    ) -> Path:
        """에셋 타입별 경로 반환"""
        project_path = self.get_project_path(user_id, channel_id, project_id)
        asset_path = project_path / self.ASSET_TYPES.get(asset_type, 'temp')
        asset_path.mkdir(parents=True, exist_ok=True)
        return asset_path
    
    def save_image(
        self,
        user_id: str,
        channel_id: str,
        project_id: str,
        asset_type: str,
        image_data: bytes,
        filename: Optional[str] = None,
        extension: str = 'png'
    ) -> str:
        """이미지 저장 및 경로 반환"""
        asset_path = self.get_asset_path(user_id, channel_id, project_id, asset_type)
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{timestamp}_{uuid.uuid4().hex[:8]}.{extension}'
        
        file_path = asset_path / filename
        file_path.write_bytes(image_data)
        
        return str(file_path)
    
    def save_image_base64(
        self,
        user_id: str,
        channel_id: str,
        project_id: str,
        asset_type: str,
        base64_data: str,
        filename: Optional[str] = None
    ) -> str:
        """Base64 이미지 저장"""
        # data:image/png;base64, 제거
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]
        
        image_data = base64.b64decode(base64_data)
        return self.save_image(
            user_id, channel_id, project_id,
            asset_type, image_data, filename
        )
    
    def save_json(
        self,
        user_id: str,
        channel_id: str,
        project_id: str,
        asset_type: str,
        data: Dict[str, Any],
        filename: Optional[str] = None
    ) -> str:
        """JSON 데이터 저장"""
        asset_path = self.get_asset_path(user_id, channel_id, project_id, asset_type)
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{timestamp}_{uuid.uuid4().hex[:8]}.json'
        
        file_path = asset_path / filename
        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        
        return str(file_path)
    
    def save_text(
        self,
        user_id: str,
        channel_id: str,
        project_id: str,
        asset_type: str,
        content: str,
        filename: Optional[str] = None,
        extension: str = 'txt'
    ) -> str:
        """텍스트 파일 저장"""
        asset_path = self.get_asset_path(user_id, channel_id, project_id, asset_type)
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{timestamp}_{uuid.uuid4().hex[:8]}.{extension}'
        
        file_path = asset_path / filename
        file_path.write_text(content, encoding='utf-8')
        
        return str(file_path)
    
    def list_assets(
        self,
        user_id: str,
        channel_id: str,
        project_id: str,
        asset_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """에셋 목록 조회"""
        if asset_type:
            asset_path = self.get_asset_path(user_id, channel_id, project_id, asset_type)
            paths = [asset_path]
        else:
            project_path = self.get_project_path(user_id, channel_id, project_id)
            paths = [p for p in project_path.iterdir() if p.is_dir()]
        
        assets = []
        for path in paths:
            for file_path in path.rglob('*'):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    assets.append({
                        'path': str(file_path),
                        'name': file_path.name,
                        'type': path.name,
                        'size': file_path.stat().st_size,
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    })
        
        return sorted(assets, key=lambda x: x['modified'], reverse=True)

# 싱글톤 인스턴스
storage_service = StorageService()
