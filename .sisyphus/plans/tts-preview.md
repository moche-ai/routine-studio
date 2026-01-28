# TTS Preview Feature Implementation

## Context

### Original Request
Implement full TTS Preview Feature during TTS_SETTINGS step in channel creation flow:
1. Listen to sample voices - play pre-recorded samples
2. Test prompt input - enter text, generate TTS, play back
3. Voice cloning preview - YouTube URL + time range → extract → clone → preview

### Interview Summary
**Key Discussions**:
- Voice samples: Play existing MP3 files from /data/dbs/routine/youtube-studio/voices/samples_cut/
- YouTube extraction: Max 30 seconds, AudioProcessor selects optimal 3-7s segment
- Cache strategy: Session context (session.context dict, max ~5MB)
- Default test text: "안녕하세요 {채널명} 입니다. 루틴 스튜디오로 함께 만들어보는 유튜브 영상 제작 프로세스 입니다."
- Error handling: Show error + offer sample voice as fallback
- Rate limiting: 3 requests per 10 seconds

**Research Findings**:
- Orchestrator TTS_SETTINGS at lines 620-744 handles voice selection directly
- 137 voice samples available with prompts in samples_cut_prompts.json
- VoiceServiceV2 has full YouTube extraction + TTS cloning pipeline
- TTS servers: 8311 for presets (Sohee), 8310 for cloning
- ChatMessage.tsx uses metadata.data for structured content

### Metis Review
**Identified Gaps** (addressed):
- Audio data flow clarified: Play existing MP3s for samples, generate for custom text
- Cache strategy defined: Session context with base64 audio
- Error handling defined: Show error + offer sample fallback
- Rate limiting defined: 3 per 10 seconds per user

---

## Work Objectives

### Core Objective
Enable users to preview voice options during channel setup by playing pre-recorded samples, generating custom TTS previews, and testing voice cloning from YouTube before committing to a voice setting.

### Concrete Deliverables
1. Backend TTS preview service: `apps/api/services/tts.py`
2. Backend TTS routes: `apps/api/routes/tts.py`
3. Frontend AudioPlayer component: `apps/front/src/components/AudioPlayer.tsx`
4. Updated ChatMessage for audio rendering
5. Modified orchestrator TTS_SETTINGS flow with preview support

### Definition of Done
- [ ] User can play voice samples from samples_cut/ directory
- [ ] User can generate TTS preview with custom text
- [ ] User can extract YouTube audio and preview cloned voice
- [ ] Audio plays correctly in chat interface
- [ ] Error handling shows friendly messages with fallback options
- [ ] Rate limiting prevents abuse (3 per 10 seconds)

### Must Have
- Voice sample playback (existing MP3 files)
- Custom text TTS generation (default + user input)
- YouTube voice cloning preview
- AudioPlayer component with play/pause
- Error handling with fallback to samples
- Session-based audio caching

### Must NOT Have (Guardrails)
- NO download button for audio (play only)
- NO volume control (browser default)
- NO voice sample management UI (use existing samples)
- NO search/filter for voice samples (simple list)
- NO mobile-specific optimizations (desktop focus)
- NO persistent cache across sessions
- NO changes to existing voiceover agent logic

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: NO (no test setup for this project)
- **User wants tests**: Manual QA
- **Framework**: Playwright browser + curl for API

### Manual QA Verification

Each TODO includes detailed verification procedures:

**By Deliverable Type:**
| Type | Verification Tool | Procedure |
|------|------------------|-----------|
| Backend API | curl/httpie | Send request, verify response |
| Frontend Component | Playwright browser | Navigate, interact, screenshot |
| Integration | End-to-end flow | Complete user journey |

---

## Task Flow

```
Setup:
  1 (API Service) ─┬─> 3 (Orchestrator Integration)
                   │
  2 (API Routes) ──┘
                       
  4 (AudioPlayer) ─────> 5 (ChatMessage Update)
                       
Final:
  3 + 5 ─────> 6 (Integration Testing)
```

## Parallelization

| Group | Tasks | Reason |
|-------|-------|--------|
| A | 1, 2 | Backend service and routes can be developed together |
| B | 4, 5 | Frontend components can be developed together |

| Task | Depends On | Reason |
|------|------------|--------|
| 3 | 1, 2 | Orchestrator needs API endpoints |
| 5 | 4 | ChatMessage needs AudioPlayer component |
| 6 | 3, 5 | Integration test needs all components |

---

## TODOs

### Backend Tasks

- [ ] 1. Create TTS Preview Service

  **What to do**:
  - Create `apps/api/services/tts.py` with TTSPreviewService class
  - Implement methods:
    - `get_voice_samples()`: Load samples_cut_prompts.json, return list of voice IDs with metadata
    - `get_sample_audio(voice_id: str)`: Return base64 audio from samples_cut/{filename}.mp3
    - `generate_preview(text: str, speaker: str = "Sohee")`: Call localhost:8311/tts, return base64 audio
    - `extract_youtube_audio(url: str, start_time: str, end_time: str)`: Use VoiceServiceV2 to extract audio segment
    - `clone_voice_preview(text: str, ref_audio_base64: str, ref_text: str)`: Call localhost:8310/clone
  - Implement rate limiting: RateLimiter class with 3 requests per 10 seconds per session
  - Add error handling: TTSError exception class with user-friendly messages

  **Must NOT do**:
  - Do not modify VoiceServiceV2 (use existing implementation)
  - Do not add caching logic here (orchestrator handles session cache)
  - Do not add authentication (public endpoints for now)

  **Parallelizable**: YES (with task 2)

  **References**:
  
  **Pattern References** (existing code to follow):
  - `apps/api/services/session_service.py` - Service class pattern (async methods, singleton, error handling)
  - `agents/benchmarker/voice_service.py:VoiceServiceV2` - YouTube extraction and TTS cloning patterns
  - `agents/voiceover/agent.py:30-60` - TTS server URLs and request patterns

  **API/Type References** (contracts to implement against):
  - `/data/dbs/routine/youtube-studio/voices/samples_cut_prompts.json` - Voice sample metadata structure
  - TTS API at localhost:8311/tts - Payload: {"text", "language", "speaker", "instruct"}
  - Clone API at localhost:8310/clone - Payload: {"text", "language", "ref_audio_base64", "ref_text"}

  **Acceptance Criteria**:
  
  **Manual Execution Verification:**
  - [ ] Using curl:
    - `curl http://localhost:8002/api/tts/samples` → Returns JSON list of voice samples
    - `curl http://localhost:8002/api/tts/sample/m3gJBS8OofDJfycyA2Ip_01` → Returns {"audio_base64": "..."}
    - `curl -X POST http://localhost:8002/api/tts/preview -d '{"text":"테스트"}'` → Returns {"audio_base64": "..."}
  - [ ] Rate limiting test:
    - Send 4 requests in 5 seconds → 4th request returns 429 Too Many Requests
  - [ ] Error handling test:
    - Stop TTS server, call /api/tts/preview → Returns error with fallback suggestion

  **Commit**: YES
  - Message: `feat(api): add TTS preview service with rate limiting`
  - Files: `apps/api/services/tts.py`
  - Pre-commit: Manual curl tests

---

- [ ] 2. Create TTS Preview API Routes

  **What to do**:
  - Create `apps/api/routes/tts.py` with FastAPI router
  - Implement endpoints:
    - `GET /api/tts/samples` - List available voice samples (paginated, 10 per page)
    - `GET /api/tts/sample/{voice_id}` - Get specific sample audio as base64
    - `POST /api/tts/preview` - Generate TTS preview (text, speaker optional)
    - `POST /api/tts/extract-youtube` - Extract audio from YouTube (url, start_time, end_time)
    - `POST /api/tts/clone-preview` - Clone voice and preview (text, ref_audio_base64, ref_text)
  - Add Pydantic models for request/response validation
  - Register router in apps/api/main.py

  **Must NOT do**:
  - Do not add authentication (keep public for now)
  - Do not implement caching in routes (service layer handles it)

  **Parallelizable**: YES (with task 1)

  **References**:
  
  **Pattern References** (existing code to follow):
  - `apps/api/routes/agents.py` - Route structure, error handling, response patterns
  - `apps/api/routes/studio.py` - Pydantic model patterns, query parameters
  - `apps/api/main.py` - Router registration pattern

  **API/Type References** (contracts to implement against):
  - Response models should follow existing AgentResponse pattern
  - Error responses: HTTPException with appropriate status codes

  **Acceptance Criteria**:
  
  **Manual Execution Verification:**
  - [ ] Using curl:
    - `curl http://localhost:8002/api/tts/samples?page=1` → Returns paginated list
    - `curl http://localhost:8002/api/tts/sample/invalid_id` → Returns 404 error
    - `curl -X POST http://localhost:8002/api/tts/preview -H "Content-Type: application/json" -d '{"text":"안녕하세요"}'` → Returns {"audio_base64": "...", "duration": 2.5}
  - [ ] Verify router registered:
    - `curl http://localhost:8002/docs` → Shows /api/tts/* endpoints in Swagger

  **Commit**: YES
  - Message: `feat(api): add TTS preview routes with validation`
  - Files: `apps/api/routes/tts.py`, `apps/api/main.py`
  - Pre-commit: Manual curl tests

---

- [ ] 3. Update Orchestrator TTS_SETTINGS Flow

  **What to do**:
  - Modify `agents/orchestrator.py` TTS_SETTINGS section (lines 620-744)
  - Implement new TTS_SETTINGS sub-flow:
    1. Show voice options with preview buttons:
       - "1. 기본 보이스 (Sohee) [미리듣기]"
       - "2. 보이스 클로닝 [유튜브/샘플]"
       - "3. 샘플 보이스 목록 보기"
    2. Handle "미리듣기" (preview) requests:
       - For default: Generate TTS with default text, return audio in response
       - For samples: Return sample audio base64
       - For YouTube: Extract → clone → return audio
    3. Handle custom text input for preview:
       - Accept user text up to 500 chars
       - Generate TTS with selected voice
       - Return audio for playback
    4. Cache generated audio in session.context[\'tts_preview_cache\']
  - Update response format to include audio data:
    ```python
    data = {
        "type": "tts_preview",
        "audio_base64": "...",
        "voice_name": "Sohee",
        "text": "안녕하세요..."
    }
    ```
  - Add rate limiting check before TTS generation

  **Must NOT do**:
  - Do not modify other orchestrator steps
  - Do not change existing voice option storage logic
  - Do not add new dependencies

  **Parallelizable**: NO (depends on tasks 1, 2)

  **References**:
  
  **Pattern References** (existing code to follow):
  - `agents/orchestrator.py:620-744` - Current TTS_SETTINGS implementation
  - `agents/orchestrator.py:300-400` - Selection response pattern with metadata.data
  - `agents/base.py:AgentResult` - Response structure

  **API/Type References** (contracts to implement against):
  - TTSPreviewService from apps/api/services/tts.py
  - Session context structure for caching

  **Acceptance Criteria**:
  
  **Manual Execution Verification:**
  - [ ] Using Playwright browser automation:
    - Navigate to channel creation flow
    - Reach TTS_SETTINGS step
    - Click "미리듣기" button → Audio plays in chat
    - Enter custom text → Click generate → Audio plays
    - Enter YouTube URL + time range → Audio plays
  - [ ] Session cache verification:
    - Generate preview → Close tab → Return → Same audio available (within session)
  - [ ] Rate limiting:
    - Click generate 4 times rapidly → See "잠시 후 다시 시도해주세요" message

  **Commit**: YES
  - Message: `feat(orchestrator): add TTS preview support in TTS_SETTINGS`
  - Files: `agents/orchestrator.py`
  - Pre-commit: Manual browser test

---

### Frontend Tasks

- [ ] 4. Create AudioPlayer Component

  **What to do**:
  - Create `apps/front/src/components/AudioPlayer.tsx`
  - Implement AudioPlayer component:
    ```typescript
    interface AudioPlayerProps {
      src: string;           // base64 or URL
      title?: string;        // Voice name or description
      onPlay?: () => void;
      onEnded?: () => void;
    }
    ```
  - Features:
    - Play/pause toggle button
    - Progress bar with current time / duration
    - Loading state while audio loads
    - Error state if audio fails to load
  - Styling:
    - Use Tailwind CSS matching project style
    - Dark theme compatible (zinc-700 background)
    - Max width 400px
  - Handle base64 audio: Convert to blob URL for playback

  **Must NOT do**:
  - No volume control (use browser default)
  - No download button
  - No seek by clicking (just show progress)

  **Parallelizable**: YES (with task 5)

  **References**:
  
  **Pattern References** (existing code to follow):
  - `apps/front/src/components/ChatMessage.tsx` - Component structure, Tailwind patterns
  - `apps/front/src/components/editor/VideoComposition.tsx` - Audio handling patterns

  **External References** (libraries):
  - HTML5 Audio API: https://developer.mozilla.org/en-US/docs/Web/API/HTMLAudioElement

  **Acceptance Criteria**:
  
  **Manual Execution Verification:**
  - [ ] Using Playwright browser automation:
    - Import AudioPlayer in a test page
    - Provide base64 audio → Audio plays on click
    - Click pause → Audio pauses
    - Audio ends → onEnded callback fires
    - Progress bar shows correct time
  - [ ] Error handling:
    - Provide invalid audio → Shows error state

  **Commit**: YES
  - Message: `feat(frontend): add AudioPlayer component for TTS preview`
  - Files: `apps/front/src/components/AudioPlayer.tsx`
  - Pre-commit: Manual browser test

---

- [ ] 5. Update ChatMessage for Audio Rendering

  **What to do**:
  - Modify `apps/front/src/components/ChatMessage.tsx`
  - Add audio rendering logic:
    ```typescript
    // Check for audio content in message.metadata.data
    if (message.metadata?.data?.type === 'tts_preview') {
      const { audio_base64, voice_name, text } = message.metadata.data;
      return (
        <div className="mt-2">
          <AudioPlayer 
            src={`data:audio/mp3;base64,${audio_base64}`}
            title={voice_name}
          />
          {text && <p className="text-xs text-zinc-400 mt-1">{text}</p>}
        </div>
      );
    }
    ```
  - Also handle audio in selection options:
    - If option has `preview_audio` field, show play button next to option

  **Must NOT do**:
  - Do not change existing message rendering logic
  - Do not add new state management
  - Do not modify chatStore

  **Parallelizable**: NO (depends on task 4)

  **References**:
  
  **Pattern References** (existing code to follow):
  - `apps/front/src/components/ChatMessage.tsx:50-100` - Existing conditional rendering for images, selections
  - `apps/front/src/types/chat.ts` - ChatMessage interface

  **Acceptance Criteria**:
  
  **Manual Execution Verification:**
  - [ ] Using Playwright browser automation:
    - Create message with metadata.data.type = 'tts_preview'
    - Message renders AudioPlayer component
    - Audio plays correctly
    - Voice name and text display below player
  - [ ] Integration with chat:
    - Receive TTS preview from backend → Audio renders in chat

  **Commit**: YES
  - Message: `feat(frontend): add audio rendering support in ChatMessage`
  - Files: `apps/front/src/components/ChatMessage.tsx`
  - Pre-commit: Manual browser test

---

### Integration Tasks

- [ ] 6. Integration Testing and Verification

  **What to do**:
  - Test complete user flow:
    1. Start new channel creation session
    2. Proceed to TTS_SETTINGS step
    3. Test each preview option:
       - Default voice preview
       - Sample voice list and playback
       - Custom text input and preview
       - YouTube URL extraction and clone preview
    4. Verify error handling with:
       - Invalid YouTube URL
       - TTS server down (simulate)
       - Rate limit exceeded
    5. Verify session cache works
  - Document any issues found
  - Fix integration issues

  **Must NOT do**:
  - Do not add new features during integration
  - Do not refactor working code
  - Do not skip error handling tests

  **Parallelizable**: NO (depends on all previous tasks)

  **References**:
  
  **All previous tasks** - This is integration verification

  **Acceptance Criteria**:
  
  **Manual Execution Verification:**
  - [ ] Complete user journey:
    1. `curl http://localhost:8002/api/agents/start` → Get session_id
    2. Progress through steps to TTS_SETTINGS
    3. Test preview with: `curl -X POST http://localhost:8002/api/agents/message -d '{"session_id":"...","message":"미리듣기"}'`
    4. Verify response contains audio_base64
  - [ ] Playwright end-to-end:
    - Open http://localhost:5182
    - Complete channel creation up to TTS_SETTINGS
    - Click all preview buttons
    - Verify all audio plays correctly
  - [ ] Error scenarios:
    - Test invalid inputs → Friendly error messages shown
    - Rate limit → "잠시 후 다시 시도해주세요" message

  **Commit**: YES
  - Message: `test(tts): verify TTS preview integration`
  - Files: (any integration fixes)
  - Pre-commit: Full manual test suite

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `feat(api): add TTS preview service with rate limiting` | services/tts.py | curl tests |
| 2 | `feat(api): add TTS preview routes with validation` | routes/tts.py, main.py | curl + swagger |
| 3 | `feat(orchestrator): add TTS preview support in TTS_SETTINGS` | orchestrator.py | browser test |
| 4 | `feat(frontend): add AudioPlayer component for TTS preview` | AudioPlayer.tsx | component test |
| 5 | `feat(frontend): add audio rendering support in ChatMessage` | ChatMessage.tsx | integration test |
| 6 | `test(tts): verify TTS preview integration` | any fixes | full e2e test |

---

## Success Criteria

### Verification Commands
```bash
# Backend health check
curl http://localhost:8002/api/tts/samples

# TTS preview generation
curl -X POST http://localhost:8002/api/tts/preview \
  -H "Content-Type: application/json" \
  -d '{"text": "안녕하세요 테스트입니다"}'

# YouTube extraction (30s max)
curl -X POST http://localhost:8002/api/tts/extract-youtube \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=xxx", "start_time": "0:00", "end_time": "0:30"}'

# Frontend verification
# Open http://localhost:5182 → Create channel → TTS_SETTINGS → Test all previews
```

### Final Checklist
- [ ] All "Must Have" features present and working
- [ ] All "Must NOT Have" guardrails respected
- [ ] Rate limiting works (3 per 10 seconds)
- [ ] Error handling shows friendly messages with fallback
- [ ] Audio plays correctly in all browsers (Chrome, Firefox, Safari)
- [ ] Session cache working (audio persists within session)
- [ ] No console errors in frontend
- [ ] No unhandled exceptions in backend logs
