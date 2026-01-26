import json
import sys
sys.path.append("/data/routine/routine-studio-v2")

from typing import Dict, Any, List, Optional, Tuple
from agents.base import BaseAgent, AgentResult, AgentStatus
from apps.api.services.llm import llm_service
from apps.api.services.comfyui import comfyui_service
from apps.api.services.vision import vision_service
from apps.api.services.workflow import workflow_service
def emit_progress(status: str, detail: str = ""):
    try:
        import builtins
        if hasattr(builtins, "emit_agent_progress"):
            builtins.emit_agent_progress(status, detail)
    except:
        pass




class CharacterAgent(BaseAgent):
    """캐릭터 생성 에이전트 - VL 스타일 분석 + 이미지 편집 지원"""
    
    DEFAULT_NEGATIVE = "lowres, bad anatomy, bad hands, text, error, cropped, worst quality, low quality, blurry, deformed, multiple people, 2girls, 2boys, two people, crowd, group, duo, couple"
    
    PHASE_CONCEPT = "concept"
    PHASE_GENERATION = "generation"
    
    # 편집 요청 키워드 맵핑
    EDIT_KEYWORDS = {
        "background_removal": [
            "배경 제거", "배경 없", "배경 삭제", "투명 배경", "투명하게", 
            "remove background", "transparent", "no background", "배경 지워"
        ],
        "remove_item": [
            "안경 제거", "안경 없", "안경 벗", "remove glasses", "no glasses",
            "모자 제거", "모자 없", "remove hat", "수염 제거", "수염 없",
            "귀걸이 제거", "목걸이 제거", "액세서리 제거"
        ],
        "hair_change": [
            "대머리", "머리 없", "삭발", "bald", "make bald",
            "머리 색", "머리 스타일", "hair color", "hairstyle",
            "금발", "은발", "흑발", "갈색 머리", "파란 머리", "분홍 머리"
        ],
        "face_edit": [
            "표정", "눈 색", "피부", "얼굴", "expression", "eye color",
            "웃는", "화난", "슬픈", "smiling", "angry", "sad"
        ],
        "general_edit": [
            "수정해", "바꿔줘", "변경해", "edit", "change", "modify"
        ]
    }
    
    def __init__(self):
        super().__init__("CharacterAgent")
        self.current_prompt = {"positive": "", "negative": self.DEFAULT_NEGATIVE}
        self.reference_image: Optional[str] = None
        self.character_concept: Optional[str] = None
        self.detected_style: str = "cartoon"
        self.style_info: Dict[str, Any] = {}
        self.phase = self.PHASE_CONCEPT
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        self.status = AgentStatus.RUNNING
        self.phase = self.PHASE_CONCEPT
        
        channel_name = input_data.get("selected_channel_name", "")
        self.set_context("channel_name", channel_name)
        
        message = f"""채널 "{channel_name}"의 캐릭터를 만들어볼게요!

**레퍼런스 이미지**가 있다면 첨부해주세요 (AI가 스타일 자동 분석)
**텍스트로 설명**해주셔도 됩니다
**"추천해줘"**라고 하시면 AI가 추천해드려요!"""

        self.status = AgentStatus.WAITING_FEEDBACK
        return AgentResult(
            success=True, step="character", message=message,
            images=[], needs_feedback=True, data={"phase": self.PHASE_CONCEPT}
        )
    
    async def handle_feedback(self, feedback: str, images: List[str] = None) -> AgentResult:
        # 확정 처리
        if "확정" in feedback or "좋아" in feedback or "이걸로" in feedback:
            if self.phase == self.PHASE_GENERATION:
                self.status = AgentStatus.COMPLETED
                return AgentResult(
                    success=True, step="character_confirmed",
                    message="캐릭터가 확정되었습니다!",
                    images=self.get_context("generated_images", []),
                    data={"detected_style": self.detected_style}
                )
        
        # 편집 요청 확인
        edit_type, edit_instruction = self._detect_edit_request(feedback)
        if edit_type:
            generated = self.get_context("generated_images", [])
            if generated:
                return await self._handle_edit_request(edit_type, feedback, generated[0])
            return AgentResult(
                success=True, step="character",
                message="먼저 캐릭터를 생성해주세요!",
                needs_feedback=True, data={"phase": self.phase}
            )
        
        if self.phase == self.PHASE_CONCEPT:
            return await self._handle_concept_input(feedback, images)
        return await self._handle_generation_feedback(feedback, images)
    
    def _detect_edit_request(self, feedback: str) -> Tuple[Optional[str], Optional[str]]:
        """편집 요청 감지 및 유형 반환"""
        feedback_lower = feedback.lower()
        
        for edit_type, keywords in self.EDIT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in feedback_lower:
                    return edit_type, feedback
        
        return None, None
    
    async def _handle_edit_request(self, edit_type: str, feedback: str, image_data: str) -> AgentResult:
        emit_progress("이미지 편집", f"{edit_type} 처리 중...")
        """편집 요청 처리"""
        img = image_data
        if img and img.startswith("data:"):
            img = img.split(",", 1)[1]
        
        if edit_type == "background_removal":
            return await self._remove_background(image_data)
        
        # Qwen 이미지 편집 사용
        edit_instruction = await self._generate_edit_instruction(edit_type, feedback)
        
        try:
            print(f"[CharacterAgent] Edit type: {edit_type}, instruction: {edit_instruction}")
            
            workflow = workflow_service.build_qwen_image_edit(
                input_image_b64=img,
                edit_instruction=edit_instruction,
                denoise=self._get_denoise_for_edit(edit_type)
            )
            
            images = await comfyui_service.execute_workflow(workflow, timeout=180)
            self.set_context("generated_images", images)
            self.status = AgentStatus.WAITING_FEEDBACK
            
            return AgentResult(
                success=True, step="character",
                message=f"편집 완료! ({edit_type})\n\n추가 수정/확정 입력해주세요.",
                images=images, needs_feedback=True,
                data={"edit_type": edit_type, "phase": self.PHASE_GENERATION}
            )
        except Exception as e:
            print(f"Edit failed: {e}")
            return AgentResult(
                success=True, step="character",
                message=f"편집 실패: {e}\n\n다시 시도하시겠어요?",
                images=self.get_context("generated_images", []),
                needs_feedback=True, data={"error": str(e)}
            )
    
    async def _generate_edit_instruction(self, edit_type: str, feedback: str) -> str:
        """편집 유형에 맞는 영어 지시 생성"""
        type_prompts = {
            "remove_item": "remove the specified item from the image",
            "hair_change": "modify the hairstyle or hair color as specified",
            "face_edit": "edit the facial features as specified",
            "general_edit": "apply the requested modification"
        }
        
        base = type_prompts.get(edit_type, "edit the image")
        
        prompt = f"""User request: {feedback}
Edit type: {edit_type}
Base instruction: {base}

Generate a concise English instruction for Qwen Image Edit model.
Return ONLY the instruction, no explanation.
Example: "remove glasses from the face" or "change hair color to blonde" or "make the person bald"
"""
        
        try:
            result = await llm_service.generate(prompt, temperature=0.3)
            return result.strip().strip('"').strip()
        except:
            # 폴백
            feedback_map = {
                "안경 제거": "remove glasses from the face",
                "대머리": "make the person completely bald, remove all hair",
                "금발": "change hair color to blonde",
                "은발": "change hair color to silver/white",
                "모자 제거": "remove the hat",
                "웃는 표정": "change expression to smiling",
            }
            for k, v in feedback_map.items():
                if k in feedback:
                    return v
            return f"edit the image: {feedback}"
    
    def _get_denoise_for_edit(self, edit_type: str) -> float:
        """편집 유형에 따른 denoise 값"""
        denoise_map = {
            "remove_item": 0.65,
            "hair_change": 0.75,
            "face_edit": 0.60,
            "general_edit": 0.70
        }
        return denoise_map.get(edit_type, 0.70)
    
    async def _remove_background(self, image_data: str) -> AgentResult:
        emit_progress("배경 제거", "RemBG 처리 중...")
        img = image_data
        if img and img.startswith("data:"):
            img = img.split(",", 1)[1]
        
        workflow = workflow_service.build_remove_background(input_image_b64=img)
        
        try:
            images = await comfyui_service.execute_workflow(workflow, timeout=120)
            self.set_context("generated_images", images)
            self.status = AgentStatus.WAITING_FEEDBACK
            
            return AgentResult(
                success=True, step="character",
                message="배경을 제거했어요! (투명 PNG)\n\n확정하시려면 \"확정\"",
                images=images, needs_feedback=True,
                data={"background_removed": True, "phase": self.PHASE_GENERATION}
            )
        except Exception as e:
            return AgentResult(
                success=True, step="character",
                message=f"배경 제거 실패: {e}",
                images=self.get_context("generated_images", []),
                needs_feedback=True, data={"error": str(e)}
            )
    
    async def _handle_concept_input(self, feedback: str, images: List[str] = None) -> AgentResult:
        channel_name = self.get_context("channel_name", "")
        
        if images and len(images) > 0:
            self.reference_image = images[0]
            self.character_concept = feedback if feedback.strip() else "레퍼런스 스타일"
            
            await self._analyze_reference_style(images[0])
            await self._generate_prompt_from_concept(channel_name, feedback, is_style_transfer=True)
            
            self.phase = self.PHASE_GENERATION
            return await self._generate_image_with_style()
        
        if any(w in feedback for w in ["추천", "없어", "몰라", "알아서"]):
            self.detected_style = "cartoon"
            prompt = f"""YouTube channel: {channel_name}
Recommend a character. Return ONLY JSON:
{{"concept": "Korean description", "style": "cartoon/anime/realistic", "positive": "english SDXL prompt"}}"""
            
            try:
                resp = await llm_service.generate(prompt, temperature=0.8)
                if "{" in resp:
                    data = json.loads(resp[resp.find("{"):resp.rfind("}")+1])
                    self.character_concept = data.get("concept", "")
                    self.detected_style = data.get("style", "cartoon")
                    self.current_prompt["positive"] = data.get("positive", "")
                    self.phase = self.PHASE_GENERATION
                    result = await self._generate_image()
                    result.message = f"**추천:** {self.character_concept}\n**스타일:** {self.detected_style}\n\n{result.message}"
                    return result
            except Exception as e:
                print("Recommend failed:", e)
            
            self.current_prompt["positive"] = f"solo, 1person, masterpiece, cartoon character for {channel_name}"
            self.phase = self.PHASE_GENERATION
            return await self._generate_image()
        
        if feedback.strip():
            self.character_concept = feedback
            self.detected_style = self._detect_style_from_text(feedback)
            await self._generate_prompt_from_concept(channel_name, feedback, is_style_transfer=False)
            self.phase = self.PHASE_GENERATION
            return await self._generate_image()
        
        return AgentResult(
            success=True, step="character",
            message="캐릭터 컨셉을 입력해주세요!",
            needs_feedback=True, data={"phase": self.PHASE_CONCEPT}
        )
    
    async def _analyze_reference_style(self, image_data: str) -> Dict[str, Any]:
        emit_progress("스타일 분석", "이미지 스타일 감지 중...")
        try:
            print("[CharacterAgent] Analyzing style...")
            result = await vision_service.analyze_style(image_data)
            self.detected_style = result.get("style", "cartoon")
            self.style_info = result
            print(f"[CharacterAgent] Detected: {self.detected_style}")
            
            char_info = await vision_service.describe_character(image_data)
            self.set_context("character_info", char_info)
            return result
        except Exception as e:
            print(f"Style analysis error: {e}")
            self.detected_style = "cartoon"
            return {"style": "cartoon"}
    
    def _detect_style_from_text(self, text: str) -> str:
        t = text.lower()
        if any(k in t for k in ["패밀리가이", "family guy", "심슨", "카툰", "cartoon"]):
            return "cartoon"
        if any(k in t for k in ["애니", "anime", "manga", "일본"]):
            return "anime"
        if any(k in t for k in ["리얼", "real", "실사", "photo"]):
            return "realistic"
        if any(k in t for k in ["3d", "픽사", "pixar"]):
            return "3d"
        return "cartoon"
    
    async def _handle_generation_feedback(self, feedback: str, images: List[str] = None) -> AgentResult:
        if images and len(images) > 0:
            self.reference_image = images[0]
            await self._analyze_reference_style(images[0])
            channel_name = self.get_context("channel_name", "")
            await self._generate_prompt_from_concept(channel_name, feedback, is_style_transfer=True)
            return await self._generate_image_with_style()
        
        if feedback.strip():
            prompt = f"""Current: {self.current_prompt.get("positive", "")}
Feedback: {feedback}
Style: {self.detected_style}

Modify prompt. Return ONLY JSON: {{"positive": "modified prompt", "negative": "negative"}}"""
            
            try:
                resp = await llm_service.generate(prompt, temperature=0.7)
                if "{" in resp:
                    self.current_prompt = json.loads(resp[resp.find("{"):resp.rfind("}")+1])
            except:
                pass
            
            if self.reference_image:
                return await self._generate_image_with_style()
            return await self._generate_image()
        
        return AgentResult(
            success=True, step="character",
            message="수정 사항을 말씀해주세요. 확정은 \"확정\"",
            images=self.get_context("generated_images", []),
            needs_feedback=True, data={"phase": self.PHASE_GENERATION}
        )
    
    async def _generate_prompt_from_concept(self, channel_name: str, concept: str, is_style_transfer: bool = False):
        char_info = self.get_context("character_info", {})
        
        if is_style_transfer:
            req = f"""Channel: {channel_name}
Concept: {concept}
Character info: {json.dumps(char_info, ensure_ascii=False) if char_info else "N/A"}
Style: {self.detected_style}

Create a SINGLE CHARACTER description (only one person). Style via IPAdapter, no style words. Must include: solo, 1person.
Return ONLY JSON: {{"positive": "english description", "negative": "negative"}}"""
        else:
            req = f"""Channel: {channel_name}
Concept: {concept}
Style: {self.detected_style}

Create SDXL prompt for a SINGLE CHARACTER (only one person). Include solo, 1person. Use {self.detected_style} style keywords.
Return ONLY JSON: {{"positive": "english prompt", "negative": "negative"}}"""
        
        try:
            resp = await llm_service.generate(req, temperature=0.7)
            if "{" in resp:
                self.current_prompt = json.loads(resp[resp.find("{"):resp.rfind("}")+1])
        except Exception as e:
            print("Prompt gen failed:", e)
            self.current_prompt["positive"] = f"solo, 1person, masterpiece, {concept}"
    
    async def _generate_image(self) -> AgentResult:
        emit_progress("이미지 생성", "캐릭터 생성 중...")
        positive = "solo, 1person, " + self.current_prompt.get("positive", "")
        negative = self.current_prompt.get("negative", self.DEFAULT_NEGATIVE)
        
        ckpt_map = {
            "cartoon": "animagineXL_v31.safetensors",
            "anime": "animagineXL_v31.safetensors",
            "realistic": "juggernautXL_v9.safetensors",
            "3d": "juggernautXL_v9.safetensors",
        }
        checkpoint = ckpt_map.get(self.detected_style, "animagineXL_v31.safetensors")
        
        workflow = workflow_service.build_basic_sdxl(
            positive_prompt=positive, negative_prompt=negative, checkpoint=checkpoint
        )
        
        try:
            images = await comfyui_service.execute_workflow(workflow, timeout=180)
            self.set_context("generated_images", images)
            self.status = AgentStatus.WAITING_FEEDBACK
            
            return AgentResult(
                success=True, step="character",
                message=f"캐릭터 생성 완료! (스타일: **{self.detected_style}**)\n\n수정 가능: 안경제거, 대머리, 머리색 변경, 배경제거 등",
                images=images, needs_feedback=True,
                data={"phase": self.PHASE_GENERATION, "detected_style": self.detected_style}
            )
        except Exception as e:
            return AgentResult(
                success=True, step="character",
                message=f"생성 실패: {e}",
                needs_feedback=True, data={"error": str(e)}
            )
    
    async def _generate_image_with_style(self) -> AgentResult:
        emit_progress("스타일 전이", "IPAdapter 적용 중...")
        positive = "solo, 1person, " + self.current_prompt.get("positive", "")
        negative = self.current_prompt.get("negative", self.DEFAULT_NEGATIVE)
        
        ref = self.reference_image
        if ref and ref.startswith("data:"):
            ref = ref.split(",", 1)[1]
        
        style_params = {
            "cartoon": {"weight": 0.75, "weight_type": "style transfer precise"},
            "anime": {"weight": 0.85, "weight_type": "style transfer precise"},
            "realistic": {"weight": 1.0, "weight_type": "strong style transfer"},
            "3d": {"weight": 0.9, "weight_type": "style transfer precise"},
        }
        params = style_params.get(self.detected_style, style_params["cartoon"])
        
        print(f"[CharacterAgent] Style: {self.detected_style}, params: {params}")
        
        workflow = workflow_service.build_ipadapter_style_transfer(
            positive_prompt=positive, reference_image_b64=ref, negative_prompt=negative,
            style=self.detected_style, ipadapter_weight=params["weight"], weight_type=params["weight_type"]
        )
        
        try:
            images = await comfyui_service.execute_workflow(workflow, timeout=300)
            self.set_context("generated_images", images)
            self.status = AgentStatus.WAITING_FEEDBACK
            
            details = self.style_info.get("style_details", "")
            
            return AgentResult(
                success=True, step="character",
                message=f"스타일 적용 완료!\n**스타일:** {self.detected_style}\n**상세:** {details}\n\n수정 가능: 안경제거, 대머리, 머리색 변경, 배경제거 등",
                images=images, needs_feedback=True,
                data={"style_transfer": True, "phase": self.PHASE_GENERATION, "detected_style": self.detected_style}
            )
        except Exception as e:
            return AgentResult(
                success=True, step="character",
                message=f"스타일 전이 실패: {e}",
                needs_feedback=True, data={"error": str(e)}
            )
