# Draft: TTS Inline Keyboard Implementation

## Requirements (confirmed)
- TTS 설정을 텔레그램 봇의 인라인 키보드처럼 구현
- 채팅 말풍선 내에서 버튼으로 선택
- 선택에 따라 같은 말풍선의 버튼이 변경됨 (새 메시지 생성 X)
- 되돌아가기/확정 가능
- 전체 TTS 플로우가 하나의 메시지 내에서 처리

## Technical Decisions (확정됨)
- InlineKeyboard 컴포넌트를 새로 생성 (재사용 가능하게 설계)
- chatStore에 메시지 업데이트 메서드 추가
- 백엔드에 inline_action 엔드포인트 추가
- orchestrator.py의 TTS 플로우를 inline keyboard 데이터 구조로 리팩토링

## Research Findings

### 1. 현재 프론트엔드 구조 (ChatMessage.tsx)
- 현재 selection 타입은 버튼 클릭 시 sendMessage()로 새 메시지 생성
- metadata.data.type === "selection"으로 렌더링 트리거
- AudioPlayer 컴포넌트 존재 (base64 오디오 재생)
- Lucide 아이콘 사용 (Download, X, Volume2, Headphones, RefreshCw, Check)
- Tailwind CSS 사용 (zinc, emerald 컬러 팔레트)

### 2. 현재 chatStore 구조 (Zustand)
- conversations: Conversation[] (세션 관리)
- sendMessage: 새 메시지 추가만 지원
- 메시지 수정 메서드 없음 → 추가 필요
- SSE 스트리밍 지원됨

### 3. 현재 TTS 백엔드 흐름 (orchestrator.py)
- TTS_SETTINGS 진입 시 기본 보이스 미리듣기 생성
- 선택: 1(기본 보이스) / 2(보이스 클로닝)
- 클로닝: YouTube URL → 시간대 입력 → 오디오 추출 → 확인
- 각 단계마다 새 AgentResult 반환 (새 메시지 생성됨)

### 4. 변경 필요 사항
- 프론트: InlineKeyboard 컴포넌트, updateMessage 메서드
- 백엔드: inline_action 엔드포인트, TTS 플로우 inline keyboard 구조로 변환
- 데이터: view 기반 상태 관리 (navigation stack)

## Open Questions (사용자 확인 필요)
1. URL 입력을 인라인 모달로 처리할지, 채팅 입력창 사용할지?
2. 오디오 미리듣기가 각 view마다 필요한지?
3. 동시에 여러 인라인 키보드가 활성화될 수 있는지?
4. 채팅 히스토리 복원 시 인라인 키보드 상태를 어떻게 처리할지?

## Scope Boundaries
- INCLUDE: 인라인 키보드 컴포넌트, TTS 플로우 리팩토링, API 엔드포인트
- EXCLUDE: 다른 설정 플로우 (logo, BGM 등) - TTS만 우선 적용

## Proposed Data Structure
```typescript
interface InlineKeyboardMessage {
  type: "inline_keyboard"
  keyboardId: string
  currentView: string
  navigationStack: string[]  // 뒤로가기용
  views: Record<string, InlineView>
  context: Record<string, unknown>  // URL, 시간대 등 저장
}

interface InlineView {
  title: string
  content?: string
  audio?: AudioData
  inputMode?: "url" | "time" | "text"
  buttons: InlineButton[][]
}

interface InlineButton {
  id: string
  label: string
  action: "select" | "navigate" | "back" | "confirm" | "input"
  target?: string
  data?: Record<string, unknown>
}
```
