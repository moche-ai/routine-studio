import json
import random
from pathlib import Path
from typing import Dict, Any, Optional
from copy import deepcopy

WORKFLOWS_DIR = Path("/app/workflows/v2")

class WorkflowService:
    """워크플로우 로더 및 빌더 서비스"""
    
    def __init__(self):
        self.workflows: Dict[str, Dict] = {}
        self.config: Dict = {}
        self._load_config()
        self._load_workflows()
    
    def _load_config(self):
        """설정 파일 로드"""
        config_path = WORKFLOWS_DIR / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                self.config = json.load(f)
    
    def _load_workflows(self):
        """모든 워크플로우 JSON 로드"""
        for wf_file in WORKFLOWS_DIR.glob("*.json"):
            if wf_file.name == "config.json":
                continue
            try:
                with open(wf_file) as f:
                    data = json.load(f)
                    name = wf_file.stem
                    self.workflows[name] = data
            except Exception as e:
                print(f"Failed to load workflow {wf_file}: {e}")
    
    def reload(self):
        """설정 및 워크플로우 리로드"""
        self._load_config()
        self._load_workflows()
    
    def get_workflow_names(self) -> list:
        """사용 가능한 워크플로우 목록"""
        return list(self.workflows.keys())
    
    def build_workflow(
        self, 
        workflow_name: str, 
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """워크플로우 템플릿에 변수를 적용하여 실행 가능한 워크플로우 생성"""
        self.reload()
        
        if workflow_name not in self.workflows:
            raise ValueError(f"Unknown workflow: {workflow_name}")
        
        template = self.workflows[workflow_name]
        workflow = deepcopy(template.get("workflow", template.get("nodes", {})))
        
        # 기본 변수 + 오버라이드 병합
        final_vars = deepcopy(template.get("variables", template.get("parameters", {})))
        if variables:
            final_vars.update(variables)
        
        # 시드 자동 생성
        if final_vars.get("seed", -1) == -1:
            final_vars["seed"] = random.randint(0, 2**32 - 1)
        
        # 변수 치환
        workflow = self._substitute_variables(workflow, final_vars)
        
        return workflow
    
    def _substitute_variables(self, obj: Any, variables: Dict[str, Any]) -> Any:
        """재귀적으로 {{변수}} 패턴 치환"""
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if k == "_meta":
                    continue
                result[k] = self._substitute_variables(v, variables)
            return result
        elif isinstance(obj, list):
            return [self._substitute_variables(item, variables) for item in obj]
        elif isinstance(obj, str):
            if obj.startswith("{{") and obj.endswith("}}"):
                var_name = obj[2:-2]
                return variables.get(var_name, obj)
            return obj
        else:
            return obj
    
    def build_basic_sdxl(
        self,
        positive_prompt: str,
        negative_prompt: str = None,
        checkpoint: str = None,
        width: int = 1024,
        height: int = 1024,
        steps: int = None,
        cfg: float = None,
        seed: int = -1
    ) -> Dict[str, Any]:
        """기본 SDXL 워크플로우 빌드"""
        defaults = self.config.get("defaults", {}).get("sdxl", {})
        models = self.config.get("models", {})
        
        variables = {
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt or "lowres, bad anatomy, bad hands, text, error, worst quality, low quality, blurry, deformed",
            "checkpoint": checkpoint or models.get("checkpoints", {}).get("realistic", "juggernautXL_v9.safetensors"),
            "width": width,
            "height": height,
            "steps": steps or defaults.get("steps", 25),
            "cfg": cfg or defaults.get("cfg", 6.5),
            "sampler": defaults.get("sampler", "euler_ancestral"),
            "scheduler": defaults.get("scheduler", "normal"),
            "seed": seed,
            "output_prefix": "character"
        }
        
        return self.build_workflow("basic_sdxl", variables)
    
    def build_ipadapter_style_transfer(
        self,
        positive_prompt: str,
        reference_image_b64: str,
        negative_prompt: str = None,
        checkpoint: str = None,
        ipadapter_weight: float = None,
        weight_type: str = None,
        style: str = "cartoon",
        width: int = 1024,
        height: int = 1024,
        steps: int = None,
        cfg: float = None,
        seed: int = -1
    ) -> Dict[str, Any]:
        """IPAdapter 스타일 전이 워크플로우"""
        defaults_sdxl = self.config.get("defaults", {}).get("sdxl", {})
        defaults_ipa = self.config.get("defaults", {}).get("ipadapter", {})
        models = self.config.get("models", {})
        style_presets = self.config.get("style_presets", {})
        
        preset = style_presets.get(style, style_presets.get("cartoon", {}))
        positive_suffix = preset.get("positive_suffix", "")
        negative_suffix = preset.get("negative_suffix", "")
        
        final_positive = f"{positive_prompt}, {positive_suffix}" if positive_suffix else positive_prompt
        final_negative = negative_prompt or f"lowres, bad anatomy, bad hands, text, error, worst quality, {negative_suffix}"
        
        variables = {
            "positive_prompt": final_positive,
            "negative_prompt": final_negative,
            "checkpoint": checkpoint or preset.get("checkpoint", "animagineXL_v31.safetensors"),
            "clip_vision": models.get("clip_vision", {}).get("ipadapter", "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"),
            "ipadapter_model": models.get("ipadapter", {}).get("sdxl_plus", "ip-adapter-plus_sdxl_vit-h.safetensors"),
            "reference_image_b64": reference_image_b64,
            "width": width,
            "height": height,
            "steps": steps or defaults_ipa.get("steps", 30),
            "cfg": cfg or defaults_ipa.get("cfg", 7.0),
            "sampler": "euler",
            "scheduler": defaults_sdxl.get("scheduler", "normal"),
            "ipadapter_weight": ipadapter_weight or preset.get("weight", 0.8),
            "weight_type": weight_type or preset.get("weight_type", "style transfer"),
            "start_at": defaults_ipa.get("start_at", 0.0),
            "end_at": defaults_ipa.get("end_at", 0.9),
            "seed": seed,
            "output_prefix": "character_styled"
        }
        
        return self.build_workflow("ipadapter_style_transfer", variables)
    
    def build_remove_background(
        self,
        input_image_b64: str,
        output_prefix: str = "nobg"
    ) -> Dict[str, Any]:
        """배경 제거 워크플로우"""
        variables = {
            "input_image_b64": input_image_b64,
            "output_prefix": output_prefix
        }
        return self.build_workflow("remove_background", variables)
    
    def build_qwen_image_edit(
        self,
        input_image_b64: str,
        edit_instruction: str,
        denoise: float = 0.75,
        seed: int = -1,
        output_prefix: str = "edited"
    ) -> Dict[str, Any]:
        """Qwen 이미지 편집 워크플로우 (안경 제거, 헤어스타일 변경 등)"""
        variables = {
            "input_image_b64": input_image_b64,
            "edit_instruction": edit_instruction,
            "denoise": denoise,
            "seed": seed,
            "output_prefix": output_prefix
        }
        return self.build_workflow("qwen_image_edit", variables)
    
    def build_qwen_layered_edit(
        self,
        input_image_b64: str,
        edit_instruction: str,
        layers: int = 3,
        seed: int = -1,
        output_prefix: str = "layered"
    ) -> Dict[str, Any]:
        """Qwen 레이어 기반 편집 워크플로우 (배경 분리 등)"""
        variables = {
            "input_image_b64": input_image_b64,
            "edit_instruction": edit_instruction,
            "layers": layers,
            "seed": seed,
            "output_prefix": output_prefix
        }
        return self.build_workflow("qwen_layered_edit", variables)


    def build_qwen_edit_with_lora(
        self,
        input_image_b64: str,
        edit_instruction: str,
        denoise: float = 0.75,
        lora_strength: float = 0.9,
        steps: int = 30,
        cfg: float = 5.0,
        seed: int = -1,
        output_prefix: str = "qwen_lora_edit"
    ) -> Dict[str, Any]:
        """Qwen 이미지 편집 + LoRA 워크플로우"""
        workflow = self.build_workflow("qwen_edit_with_lora", {})
        
        # 플레이스홀더 교체
        workflow["1"]["inputs"]["image"] = input_image_b64
        workflow["6"]["inputs"]["prompt"] = edit_instruction
        
        # 파라미터 설정
        workflow["5"]["inputs"]["strength_model"] = lora_strength
        workflow["8"]["inputs"]["denoise"] = denoise
        workflow["8"]["inputs"]["steps"] = steps
        workflow["8"]["inputs"]["cfg"] = cfg
        workflow["8"]["inputs"]["seed"] = seed if seed != -1 else random.randint(0, 2**32-1)
        workflow["10"]["inputs"]["filename_prefix"] = output_prefix
        
        return workflow

    def build_character_consistent(
        self,
        positive_prompt: str,
        reference_image_b64: str,
        negative_prompt: str = None,
        checkpoint: str = None,
        style: str = "cartoon",
        faceid_weight: float = 0.85,
        faceid_v2_weight: float = 1.0,
        lora_strength: float = 0.75,
        width: int = 1024,
        height: int = 1024,
        steps: int = 30,
        cfg: float = 5.0,
        seed: int = -1
    ) -> Dict[str, Any]:
        """캐릭터 일관성 워크플로우 - IPAdapter FaceID Plus v2 + FaceDetailer"""
        style_checkpoints = {
            "cartoon": "NovaCartoonXL_v6.safetensors",
            "anime": "animagineXL_v31.safetensors",
            "realistic": "juggernautXL_v9.safetensors",
        }
        
        variables = {
            "positive_prompt": f"solo, 1person, {positive_prompt}, masterpiece, best quality, highly detailed face, sharp focus",
            "negative_prompt": negative_prompt or "lowres, bad anatomy, bad hands, text, error, cropped, worst quality, low quality, blurry, deformed, multiple people, 2girls, 2boys, ugly face, disfigured face",
            "checkpoint": checkpoint or style_checkpoints.get(style, "NovaCartoonXL_v6.safetensors"),
            "clip_vision": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors",
            "ipadapter_model": "ip-adapter-faceid-plusv2_sdxl.bin",
            "faceid_lora": "ip-adapter-faceid-plusv2_sdxl_lora.safetensors",
            "face_detector": "bbox/face_yolov8m.pt",
            "reference_image_b64": reference_image_b64,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg": cfg,
            "sampler": "euler_ancestral",
            "scheduler": "normal",
            "faceid_weight": faceid_weight,
            "faceid_v2_weight": faceid_v2_weight,
            "lora_strength": lora_strength,
            "weight_type": "linear",
            "seed": seed,
            "output_prefix": "character_consistent"
        }
        
        return self.build_workflow("character_consistent", variables)

    def build_character_instantid(
        self,
        positive_prompt: str,
        reference_image_b64: str,
        negative_prompt: str = None,
        checkpoint: str = None,
        style: str = "cartoon",
        instantid_weight: float = 0.8,
        controlnet_strength: float = 0.8,
        width: int = 1016,
        height: int = 1016,
        steps: int = 28,
        cfg: float = 4.5,
        seed: int = -1
    ) -> Dict[str, Any]:
        """최고 품질 캐릭터 일관성 - InstantID + FaceDetailer"""
        style_checkpoints = {
            "cartoon": "NovaCartoonXL_v6.safetensors",
            "anime": "animagineXL_v31.safetensors",
            "realistic": "juggernautXL_v9.safetensors",
        }
        
        variables = {
            "positive_prompt": f"solo, 1person, {positive_prompt}, masterpiece, best quality, highly detailed, sharp focus, clear face",
            "negative_prompt": negative_prompt or "lowres, bad anatomy, bad hands, text, error, cropped, worst quality, low quality, blurry, deformed, multiple people, ugly, disfigured",
            "checkpoint": checkpoint or style_checkpoints.get(style, "NovaCartoonXL_v6.safetensors"),
            "instantid_model": "ip-adapter.bin",
            "instantid_controlnet": "instantid_controlnet.safetensors",
            "clip_vision": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors",
            "face_detector": "bbox/face_yolov8m.pt",
            "reference_image_b64": reference_image_b64,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg": cfg,
            "sampler": "euler",
            "scheduler": "normal",
            "instantid_weight": instantid_weight,
            "controlnet_strength": controlnet_strength,
            "seed": seed,
            "output_prefix": "character_instantid"
        }
        
        return self.build_workflow("character_instantid", variables)

# 싱글톤 인스턴스
workflow_service = WorkflowService()
