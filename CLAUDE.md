# Routine Studio - LLM 코딩 규칙

**중요**: 이 파일은 LLM이 코딩할 때 **반드시 먼저 읽어야** 하는 규칙 문서입니다.

---

## 1. 프로젝트 개요

Routine Studio는 YouTube 콘텐츠 자동화 플랫폼입니다.
AI 에이전트들이 협업하여 영상 기획, 대본, 음성, 이미지, 비디오를 자동 생성합니다.

### 1.1 프로젝트 구조

```
/data/projects/routine/studio/
├── apps/
│   ├── api/          # FastAPI 백엔드 (Port 18002)
│   └── front/        # React/Vite 프론트엔드 (Port 5183)
├── agents/           # 10개 AI 에이전트 모듈
│   ├── orchestrator.py
│   ├── voiceover/    # TTS 음성 생성
│   ├── logo_generator/  # ComfyUI 로고 생성
│   ├── quality_checker/ # Vision 품질 검사
│   └── ...
├── autonomous/       # 자율 테스트/개선 스크립트
├── libs/             # 공유 라이브러리
└── output/           # 생성된 미디어 파일
```

### 1.2 기술 스택

| 영역 | 기술 |
|------|------|
| **Backend** | FastAPI, Pydantic v2, SQLite |
| **Frontend** | React 19, Vite, TailwindCSS, Zustand |
| **AI Services** | vLLM, ComfyUI, Qwen3-TTS, Qwen3-VL |
| **Infra** | Docker, Tailscale |

---

## 2. 포트 매핑 (필수 참조)

### 2.1 AI 모델 서빙 (GPU 서버)

| 포트 | 서비스 | 모델 | GPU | 환경변수 |
|------|--------|------|-----|----------|
| 8016 | Vision API | qwen3-vl-30b | GPU 3 | `VISION_API_URL` |
| 8017 | LLM API | gpt-oss-120b | GPU 2 | `LLM_API_URL` |
| 8188 | ComfyUI | Flux/SDXL | GPU 0 | `COMFYUI_URL` |
| 8310 | TTS Base | Qwen3-TTS | GPU 3 | `TTS_BASE_URL` |
| 8311 | TTS Custom | Qwen3-TTS | GPU 3 | `TTS_CUSTOM_URL` |
| 8312 | TTS VoiceDesign | Qwen3-TTS | GPU 3 | `TTS_DESIGN_URL` |
| 8400 | Whisper | whisper-large-v3 | GPU 3 | `WHISPER_URL` |
| 8601 | Music Gen | DiffRhythm2 | GPU 3 | `DIFFRHYTHM_URL` |
| 8700 | Music Gen | ACE-Step | GPU 3 | `ACESTEP_URL` |

### 2.2 애플리케이션

| 포트 | 서비스 | 설명 | 환경변수 |
|------|--------|------|----------|
| 18002 | routine-studio-api | 이 프로젝트 API | `API_PORT` |
| 5183 | routine-studio-front | 이 프로젝트 Frontend | `FRONTEND_PORT` |
| 8096 | routine-api | 레거시 API | - |
| 8090 | external-llm-api | 외부 LLM 프록시 | - |
| 8100 | moche-agents | 에이전트 서비스 | - |

### 2.3 Docker 환경 주의사항

**Docker 컨테이너에서 호스트 서비스 접근 시:**
- `localhost` → `172.17.0.1` (Docker gateway)
- 또는 `host.docker.internal` (Docker Desktop)

```python
# 올바른 패턴
url = os.environ.get("TTS_BASE_URL", "http://172.17.0.1:8310")

# 잘못된 패턴 (Docker에서 작동 안 함)
url = "http://localhost:8310"
```

---

## 3. 설정 파일

### 3.1 환경변수 로드 순서

1. `apps/api/config/settings.py` - API 서버 설정 (Pydantic)
2. `agents/config.py` - 에이전트 설정 (Pydantic)
3. `.env` 파일 - 환경별 오버라이드

### 3.2 설정 수정 시

```python
# 1. settings.py에 변수 추가
class Settings(BaseSettings):
    new_service_url: str = "http://172.17.0.1:PORT"

# 2. .env.example에 문서화
# NEW_SERVICE_URL=http://172.17.0.1:PORT

# 3. 사용처에서 import
from config.settings import settings
url = settings.new_service_url
```

---

## 4. 코드 작성 규칙

### 4.1 필수 규칙

| 규칙 | 설명 |
|------|------|
| **TypeScript strict** | Frontend는 any 타입 금지 |
| **Pydantic v2** | API 스키마는 Pydantic 모델 필수 |
| **async/await** | FastAPI 핸들러는 모두 async |
| **환경변수** | 하드코딩 URL 금지, settings import |

### 4.2 파일별 역할

| 파일 유형 | 역할 | 예시 |
|----------|------|------|
| `routes/*.py` | API 엔드포인트 | auth.py, agents.py |
| `services/*.py` | 비즈니스 로직 | tts.py, vision.py |
| `agents/*/agent.py` | 에이전트 구현 | voiceover/agent.py |
| `schemas/*.py` | Pydantic 모델 | - |

### 4.3 에이전트 수정 시 주의사항

```python
# 에이전트 파일에서 설정 사용
from agents.config import agent_settings

class VoiceoverAgent(BaseAgent):
    TTS_BASE_URL = agent_settings.tts_base_url  # settings에서 가져오기
```

---

## 5. 금지 사항

### 5.1 절대 금지

| 항목 | 이유 |
|------|------|
| `localhost` 하드코딩 | Docker 환경에서 작동 안 함 |
| API 키 코드에 직접 작성 | 보안 위험, 환경변수 사용 |
| `any` 타입 사용 | 타입 안전성 저하 |
| `console.log` 프로덕션 | 로그 라이브러리 사용 |
| 이모지 프론트엔드 코드 | 사용자 규칙 위반 |

### 5.2 수정 전 확인

- [ ] 변경할 파일이 다른 곳에서 import 되는지 확인
- [ ] 환경변수 기본값이 Docker에서 작동하는지 확인
- [ ] API 변경 시 프론트엔드 영향 확인

---

## 6. 배포 및 실행

### 6.1 로컬 개발

```bash
# API 서버
cd /data/projects/routine/studio/apps/api
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 18002 --reload

# Frontend
cd /data/projects/routine/studio/apps/front
npm run dev
```

### 6.2 프로덕션 배포

```bash
# deploy.sh 사용
./scripts/deploy.sh api    # API만
./scripts/deploy.sh front  # Frontend만
./scripts/deploy.sh all    # 전체
```

### 6.3 헬스체크

```bash
# API
curl http://100.82.192.109:18002/health
# Expected: {"status":"ok","version":"2.0.0"}

# Frontend
curl http://100.82.192.109:5183
```

---

## 7. 트러블슈팅

### 7.1 연결 오류

| 오류 | 원인 | 해결 |
|------|------|------|
| `Connection refused :8310` | TTS 서버 다운 | GPU 서버 확인 |
| `Connection refused :8188` | ComfyUI 다운 | GPU 0 확인 |
| `CORS error` | Origin 미등록 | main.py CORS 추가 |

### 7.2 Docker 관련

```bash
# Docker 내부에서 호스트 접근 확인
docker exec -it container_name curl http://172.17.0.1:8310/health
```
