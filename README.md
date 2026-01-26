# Routine Studio v2

유튜브 콘텐츠 자동화 스튜디오

## 실행 방법

### API 서버 (포트 8003)
```bash
cd /data/routine/routine-studio-v2/apps/api
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

### 프론트엔드 (포트 5182)
```bash
cd /data/routine/routine-studio-v2/apps/front
npm run dev -- --host 0.0.0.0 --port 5182
```

## 주요 기능

### 에이전트 워크플로우 (1-4단계)
1. **채널명 생성** - LLM으로 채널명 후보 10개 생성
2. **캐릭터 생성** - ComfyUI로 캐릭터 이미지 생성 (스킵 가능)
3. **영상 아이디어** - 독창적인 영상 주제 20개 생성
4. **대본 작성** - 10-15분 분량 유튜브 대본 작성

### 프론트엔드 기능
- 좌측 사이드바: 대화 목록 (접기/펼치기)
- 다중 대화 지원: 여러 프로젝트 동시 진행
- 로컬 스토리지: 대화 기록 자동 저장
- 실시간 진행 상태: 단계별 진행률 표시

## API 엔드포인트

### 에이전트
- `POST /api/agents/start` - 워크플로우 시작
- `POST /api/agents/message` - 메시지/피드백 전송
- `GET /api/agents/session/{id}` - 세션 상태 조회

### 에셋
- `POST /api/assets/image` - 이미지 저장
- `POST /api/assets/text` - 텍스트 저장
- `GET /api/assets/list/{user}/{channel}/{project}` - 에셋 목록

## 폴더 구조

```
routine-studio-v2/
├── apps/
│   ├── api/           # FastAPI 백엔드
│   │   ├── routes/    # API 라우트
│   │   ├── services/  # LLM, ComfyUI, Storage
│   │   └── main.py
│   └── front/         # React 프론트엔드
│       └── src/
│           ├── components/  # UI 컴포넌트
│           ├── stores/      # Zustand 상태관리
│           └── services/    # API 클라이언트
├── agents/            # 에이전트 시스템
│   ├── base.py        # BaseAgent 클래스
│   ├── orchestrator.py # 워크플로우 관리
│   ├── planner/       # 기획 에이전트
│   └── character/     # 캐릭터 생성 에이전트
├── output/            # 생성된 에셋 저장
│   └── {user}/{channel}/{project}/
├── packages/
│   └── db/            # 데이터베이스 스키마
└── workflows/         # ComfyUI 워크플로우
```

## 사용 기술

- **Backend**: FastAPI, Python 3.11+
- **Frontend**: React 19, Vite 7, Tailwind CSS 4
- **State**: Zustand 5 (with persist)
- **LLM**: gpt-oss-120b-longctx (localhost:8017)
- **Image**: ComfyUI (localhost:8188)
- **Database**: PostgreSQL (port 5436)

## 접속 URL

- 프론트엔드: http://100.82.192.109:5182
- API: http://100.82.192.109:8003
- API 문서: http://100.82.192.109:8003/docs
