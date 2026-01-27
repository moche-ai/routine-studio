# 변경 이력 - 2026-01-27

## 개요
DB 구조 설계 및 긴급 버그 수정 작업 완료

---

## 긴급 버그 수정

### 1. 벤치마킹 → 캐릭터 전환 버그 수정

**문제점**
- 벤치마킹 리포트 확인 후 "다음" 또는 "확인" 입력해도 캐릭터 단계로 전환되지 않음
- `benchmark_shown` 상태 체크가 `result.data` 블록 내부에 있어서 조건을 만족하지 못함

**수정 내용**
- `orchestrator.py` 457-467라인에 조기 처리 로직 추가
- 피드백 핸들러 호출 전에 `benchmark_shown` + 확인 메시지 체크

**수정 파일**
- `/data/routine/routine-studio-v2/agents/orchestrator.py`

```python
# ========== BENCHMARKING 완료 후 "다음" 입력 시 먼저 처리 (버그 수정) ==========
if current_step == WorkflowStep.BENCHMARKING and session.context.get("benchmark_shown"):
    if self._is_confirmation(message):
        session.current_step = WorkflowStep.CHARACTER
        char_result = await self.character_agent.execute({
            "step": "character",
            **session.context
        })
        self._save(session)
        return self._format_response(session, char_result)
```

---

### 2. 스크립트 패턴 파싱 오류 수정

**문제점**
- LLM 응답이 불완전한 JSON일 경우 파싱 실패
- 스크립트 패턴 분석 결과가 "(분석 실패: LLM 응답 파싱 실패)"로 표시

**수정 내용**
- `_parse_json` 메서드 개선:
  - 이스케이프 문자 처리 개선
  - trailing comma 자동 제거
  - 줄바꿈 정규화
- `_extract_fields_fallback` 메서드 추가:
  - JSON 파싱 실패 시 정규식으로 주요 필드 추출
  - summary, hook_style, structure, color_palette 등 핵심 필드 복구

**수정 파일**
- `/data/routine/routine-studio-v2/agents/benchmarker/agent.py`

```python
def _extract_fields_fallback(self, text: str) -> Optional[Dict[str, Any]]:
    """JSON 파싱 실패 시 정규식으로 주요 필드 추출"""
    patterns = [
        (r'"summary"\s*:\s*"([^"]*)"', "summary"),
        (r'"hook_style"\s*:\s*"([^"]*)"', "hook_style"),
        # ... 기타 패턴
    ]
    # 정규식으로 필드 추출 후 dict 반환
```

---

## DB 구조 추가

### SQLite 데이터베이스 도입

**목적**
- 기존 JSON 파일 기반 저장소를 정규화된 DB로 전환
- 데이터 일관성 및 쿼리 성능 향상

**데이터베이스 위치**
```
/data/routine/routine-studio-v2/data/routine.db
```

### 테이블 구조

#### 1. users (사용자)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | TEXT PK | UUID |
| username | TEXT UNIQUE | 아이디 |
| password_hash | TEXT | bcrypt 해시 |
| name | TEXT | 이름 |
| role | TEXT | ADMIN/MANAGER/VIEWER |
| is_approved | BOOLEAN | 승인 여부 |
| created_at | TIMESTAMP | 생성일 |

#### 2. projects (프로젝트/세션)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | TEXT PK | UUID |
| user_id | TEXT FK | 사용자 ID |
| channel_name | TEXT | 채널명 |
| user_request | TEXT | 사용자 요청 |
| current_step | TEXT | 현재 단계 |
| status | TEXT | in_progress/completed/archived |
| context_json | JSON | 전체 컨텍스트 |
| created_at | TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | 수정일 |

#### 3. benchmarks (벤치마킹 결과)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 자동증가 |
| project_id | TEXT FK | 프로젝트 ID |
| channel_url | TEXT | 채널 URL (인덱스) |
| channel_name | TEXT | 채널명 |
| subscriber_count | INTEGER | 구독자 수 |
| video_count | INTEGER | 영상 수 |
| channel_concept | TEXT | 채널 컨셉 |
| unique_selling_point | TEXT | USP |
| brand_voice | TEXT | 브랜드 보이스 |
| thumbnail_pattern | JSON | 썸네일 패턴 |
| script_pattern | JSON | 스크립트 패턴 |
| content_strategy | JSON | 콘텐츠 전략 |
| audience_profile | JSON | 타겟 오디언스 |
| replication_guide | JSON | 복제 가이드 |
| analyzed_at | TIMESTAMP | 분석일 |

#### 4. characters (캐릭터)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 자동증가 |
| project_id | TEXT FK | 프로젝트 ID |
| character_type | TEXT | human/animal/fantasy |
| gender | TEXT | 성별 |
| clothing | TEXT | 의상 |
| expression | TEXT | 표정 |
| art_style | TEXT | 아트 스타일 |
| personality | TEXT | 성격 |
| image_path | TEXT | 이미지 경로 |
| image_base64 | TEXT | Base64 이미지 |
| created_at | TIMESTAMP | 생성일 |

#### 5. content_ideas (콘텐츠 아이디어)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 자동증가 |
| project_id | TEXT FK | 프로젝트 ID |
| title | TEXT | 제목 |
| hook | TEXT | 후킹 |
| summary | TEXT | 요약 |
| script | JSON | 스크립트 섹션 |
| is_selected | BOOLEAN | 선택 여부 |
| created_at | TIMESTAMP | 생성일 |

#### 6. generated_assets (생성된 에셋)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 자동증가 |
| project_id | TEXT FK | 프로젝트 ID |
| content_idea_id | INTEGER FK | 콘텐츠 아이디어 ID |
| asset_type | TEXT | image/video/audio/subtitle |
| file_path | TEXT | 파일 경로 |
| asset_metadata | JSON | 메타데이터 |
| created_at | TIMESTAMP | 생성일 |

---

## 추가/수정된 파일 목록

### 신규 파일
| 파일 | 설명 |
|------|------|
| `apps/api/database.py` | SQLite 연결, 세션 관리, 마이그레이션 |
| `apps/api/models.py` | SQLAlchemy 모델 정의 |

### 수정된 파일
| 파일 | 변경 내용 |
|------|----------|
| `agents/orchestrator.py` | 벤치마킹→캐릭터 전환 버그 수정 |
| `agents/benchmarker/agent.py` | JSON 파싱 개선 + 폴백 로직 |
| `apps/api/main.py` | DB 초기화 lifespan 추가 |
| `apps/api/routes/auth.py` | DB 기반으로 전환 |
| `apps/api/routes/admin.py` | DB 기반으로 전환 |

### 백업 파일
| 파일 | 설명 |
|------|------|
| `agents/orchestrator.py.bak` | 수정 전 백업 |
| `agents/benchmarker/agent.py.bak` | 수정 전 백업 |
| `apps/api/routes/auth.py.bak` | 수정 전 백업 |
| `apps/api/routes/admin.py.bak` | 수정 전 백업 |

---

## 마이그레이션 현황

### users.json → users 테이블
- **마이그레이션 완료**: 2명
  - admin (ADMIN, 승인됨)
  - testuser (VIEWER, 미승인)

### 기존 JSON 파일 유지
- `channels.json` - 추후 마이그레이션 예정
- `projects.json` - 추후 마이그레이션 예정
- `.sessions/*.json` - orchestrator에서 DB 저장으로 전환 예정

---

## 검증 방법

### 1. 버그 수정 검증
```bash
# 새 세션 시작 → 채널명 선택 → 벤치마킹 완료
# "다음" 입력 → 캐릭터 단계 진입 확인
```

### 2. DB 검증
```bash
# Ubuntu 서버에서
cd /data/routine/routine-studio-v2/apps/api
source venv/bin/activate
python3 -c "
from database import get_db_context
from models import User
with get_db_context() as db:
    users = db.query(User).all()
    for u in users:
        print(f'{u.username}: {u.role}')
"
```

### 3. API 테스트
```bash
# 서버 실행
cd /data/routine/routine-studio-v2/apps/api
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

# 로그인 테스트
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

---

## 다음 단계 (TODO)

- [ ] orchestrator의 세션 저장을 DB로 전환
- [ ] channels.json → benchmarks 테이블 마이그레이션
- [ ] projects.json → projects 테이블 마이그레이션
- [ ] 벤치마킹 캐시를 benchmarks 테이블로 통합
