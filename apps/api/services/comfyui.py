import httpx
import json
import uuid
import asyncio
import base64
from typing import Dict, Any, List, Optional

class ComfyUIService:
    """ComfyUI API 서비스"""
    
    def __init__(self, base_url: str = "http://localhost:8188"):
        self.base_url = base_url
        self.client_id = str(uuid.uuid4())
    
    async def queue_prompt(self, workflow: Dict[str, Any]) -> str:
        """워크플로우 실행 요청"""
        print(f"[ComfyUI] Queuing workflow with {len(workflow)} nodes")
        print(f"[ComfyUI] Node types: {[n.get('class_type') for n in workflow.values()]}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/prompt",
                json={
                    "prompt": workflow,
                    "client_id": self.client_id
                }
            )
            
            if response.status_code != 200:
                error_text = response.text
                print(f"[ComfyUI] Error response: {error_text}")
                raise Exception(f"ComfyUI error: {error_text}")
            
            data = response.json()
            prompt_id = data.get("prompt_id")
            
            if "error" in data:
                print(f"[ComfyUI] Workflow error: {data[error]}")
                raise Exception(f"ComfyUI workflow error: {data[error]}")
            
            if "node_errors" in data and data["node_errors"]:
                print(f"[ComfyUI] Node errors: {data[node_errors]}")
                raise Exception(f"ComfyUI node errors: {data[node_errors]}")
            
            print(f"[ComfyUI] Queued with prompt_id: {prompt_id}")
            return prompt_id
    
    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """실행 결과 조회"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/history/{prompt_id}")
            response.raise_for_status()
            return response.json()
    
    async def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        """생성된 이미지 가져오기"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/view",
                params={"filename": filename, "subfolder": subfolder, "type": folder_type}
            )
            response.raise_for_status()
            return response.content
    
    async def delete_output_file(self, filename: str, subfolder: str = ""):
        """ComfyUI output 폴더에서 파일 삭제"""
        import os
        output_base = "/data/comfyui/output"
        if subfolder:
            file_path = os.path.join(output_base, subfolder, filename)
        else:
            file_path = os.path.join(output_base, filename)
        
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"[ComfyUI] Deleted: {file_path}")
        except Exception as e:
            print(f"[ComfyUI] Failed to delete {file_path}: {e}")
    
    async def execute_workflow(
        self,
        workflow: Dict[str, Any],
        timeout: int = 300,
        poll_interval: float = 2.0
    ) -> List[str]:
        """워크플로우 실행 후 결과 이미지 URL 반환"""
        
        prompt_id = await self.queue_prompt(workflow)
        
        elapsed = 0
        while elapsed < timeout:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            
            history = await self.get_history(prompt_id)
            if prompt_id in history:
                status = history[prompt_id].get("status", {})
                if status.get("status_str") == "error":
                    error_msg = status.get("messages", [])
                    print(f"[ComfyUI] Execution error: {error_msg}")
                    raise Exception(f"ComfyUI execution error: {error_msg}")
                
                outputs = history[prompt_id].get("outputs", {})
                images = []
                
                for node_id, node_output in outputs.items():
                    if "images" in node_output:
                        for img in node_output["images"]:
                            filename = img.get("filename", "")
                            subfolder = img.get("subfolder", "")
                            img_type = img.get("type", "output")
                            
                            img_data = await self.get_image(filename, subfolder, img_type)
                            b64 = base64.b64encode(img_data).decode("utf-8")
                            images.append(f"data:image/png;base64,{b64}")
                            
                            # 이미지 가져온 후 ComfyUI output에서 삭제
                            await self.delete_output_file(filename, subfolder)
                
                print(f"[ComfyUI] Generated {len(images)} images")
                return images
        
        raise TimeoutError(f"Workflow execution timed out after {timeout}s")

comfyui_service = ComfyUIService()
