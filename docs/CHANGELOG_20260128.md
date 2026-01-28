# 변경 이력 - 2026-01-28

## 개요
Go-Back 네비게이션 기능 구현 - 사용자가 이전 단계로 돌아가거나 특정 단계로 직접 이동 가능

---

## 신규 기능

### 1. Go-Back 네비게이션 시스템
- **기능**: 사용자가 "이전", "뒤로가기", "채널명 다시" 등의 명령어로 이전 단계로 이동 가능
- **동작**:
  - 이전 단계로 한 칸 뒤로: "이전", "뒤로", "back", "go back", "previous"
  - 특정 단계로 직접 이동: "채널명", "캐릭터 다시", "음성 설정", "영상 합성" 등
  - 이동 시 해당 단계 이후의 모든 context 데이터 자동 초기화

### 2. STEP_CONTEXT_KEYS 확장
- VIDEO_IDEAS, SCRIPT, IMAGE_PROMPT, IMAGE_GENERATE, VOICEOVER, COMPOSE 단계 추가
- 각 단계별 초기화할 context 키 정의

### 3. 새로운 메서드

#### `go_to_step(session, target_step) -> AgentResult`
- 특정 단계로 이동하고 해당 단계 이후의 context 초기화
- 이전 단계로만 이동 가능 (앞으로 이동 불가)
- 성공 시 단계명을 포함한 메시지 반환

#### `_parse_go_back_command(message) -> Optional[WorkflowStep]`
- 사용자 메시지에서 go-back 명령어 파싱
- "previous" 또는 WorkflowStep 반환
- 지원하는 키워드:
  - 이전 단계: "이전", "뒤로", "back", "go back", "previous"
  - 특정 단계: "채널명", "캐릭터", "음성", "로고", "아이디어", "대본", "프롬프트", "이미지", "보이스오버", "합성" 등

---

## 수정된 파일

| 파일 | 변경 내용 |
|------|---------|
| `agents/orchestrator.py` | STEP_CONTEXT_KEYS 확장, go_to_step() 메서드 추가, _parse_go_back_command() 메서드 추가, process_message()에 go-back 처리 로직 추가 |
| `apps/api/routes/agents.py` | POST /api/agents/go-to-step 엔드포인트 추가 |

---

## 사용 예시

### 1. 메시지 기반 Go-Back (자동)
```
사용자: "이전 단계로 가고 싶어"
→ orchestrator가 자동으로 감지하여 이전 단계로 이동
```

### 2. API 기반 Go-Back (명시적)
```bash
POST /api/agents/go-to-step?session_id=xxx&step=channel_name
```

### 3. 특정 단계로 직접 이동
```
사용자: "채널명 다시 설정하고 싶어"
→ CHANNEL_NAME 단계로 이동, 그 이후 모든 context 초기화
```

---

## 검증 방법

### 단위 테스트
```bash
cd /data/routine/routine-studio-v2
python3 /tmp/test_go_back.py
```

### API 테스트
```bash
# 세션 없을 때 (404 예상)
curl -X POST "http://localhost:8002/api/agents/go-to-step?session_id=test&step=channel_name"

# 응답: {"detail":"Session not found"}
```

---

## 기술 상세

### Context 초기화 로직
- target_step부터 current_step까지의 모든 단계에 대해 STEP_CONTEXT_KEYS에 정의된 키 삭제
- 예: IMAGE_GENERATE → CHANNEL_NAME로 이동 시, 그 사이의 모든 단계 context 초기화

### 키워드 매칭
- 대소문자 무시 (lower())
- 부분 문자열 매칭 (예: "채널명"이 포함되면 CHANNEL_NAME으로 인식)
- 우선순위: "다시" 키워드가 포함된 경우 특정 단계 감지

---

## 다음 단계 (TODO)
- [ ] 프론트엔드에서 go-back 버튼 UI 추가
- [ ] 단계별 go-back 가능 여부 검증 강화
- [ ] 사용자 피드백 기반 키워드 추가
