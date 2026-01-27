# 변경 이력 - 2026-01-27

## 개요
JSON 파일 기반 저장소를 SQLite DB로 전환하는 마이그레이션 완료

---

## 신규 파일

### 1. Session Service (apps/api/services/session_service.py)
- **기능**: Session dict와 Project 모델 간 변환, DB 저장/로드
- **주요 함수**:
  - `session_to_project()`: Session dict → Project 모델
  - `project_to_session_dict()`: Project 모델 → Session dict
  - `save_session_to_db()`: DB에 세션 저장
  - `load_session_from_db()`: DB에서 세션 로드
  - `_save_character_if_present()`: context에서 캐릭터 정보 추출 저장

### 2. Benchmark Cache DB Service (agents/benchmarker/cache_service_db.py)
- **기능**: cache_service.py와 동일 인터페이스로 DB 캐시 제공
- **주요 함수**:
  - `normalize_channel_url()`: URL 정규화
  - `find_benchmark()`: DB에서 벤치마크 조회
  - `save_benchmark()`: DB에 벤치마크 저장
  - `get_cache_summary()`: 캐시 요약 생성
  - `delete_benchmark()`: DB에서 벤치마크 삭제

### 3. 마이그레이션 스크립트
- **scripts/migrate_sessions.py**: JSON 세션 → projects 테이블
- **scripts/migrate_benchmarks.py**: benchmark_cache/*.json → benchmarks 테이블
- **scripts/verify_migration.py**: 마이그레이션 검증

---

## 수정된 파일

### 1. agents/orchestrator.py
- **변경 내용**:
  - `USE_DB_STORAGE` 플래그 추가 (DB 서비스 import 성공 시 True)
  - `save_session()`: DB 저장 → JSON 백업 (폴백 지원)
  - `load_session()`: DB 로드 → JSON 폴백
  - `_save_session_json()`, `_load_session_json()`: 레거시 함수 분리

### 2. agents/benchmarker/agent.py
- **변경 내용**:
  - import를 `cache_service_db`로 변경 (폴백: `cache_service`)

---

## 마이그레이션 결과

| 항목 | Before | After |
|------|--------|-------|
| 세션 파일 | 30개 JSON 파일 | projects 테이블 30개 |
| 벤치마크 캐시 | 1개 JSON 파일 | benchmarks 테이블 1개 |
| 캐릭터 정보 | context 내 저장 | characters 테이블 2개 |

---

## 검증 명령어

```bash
# DB 상태 확인
cd /data/routine/routine-studio-v2
python3 scripts/verify_migration.py

# Python으로 직접 확인
python3 << 'EOF'
import sys
sys.path.insert(0, '/data/routine/routine-studio-v2/apps/api')
from database import get_db_context
from models import Project, Character, Benchmark
with get_db_context() as db:
    print(f'Projects: {db.query(Project).count()}')
    print(f'Characters: {db.query(Character).count()}')
    print(f'Benchmarks: {db.query(Benchmark).count()}')
EOF
```

---

## 롤백 방법

문제 발생 시:
1. orchestrator.py: `USE_DB_STORAGE = False` 직접 설정 (import 실패 시 자동 폴백)
2. benchmarker/agent.py: import를 `cache_service`로 변경
3. JSON 파일은 그대로 유지되어 있음 (output/.sessions/, output/benchmark_cache/)

---

## 다음 단계 (TODO)

- [ ] API 서버에서 DB 연동 테스트
- [ ] 오래된 JSON 파일 정리 (선택사항)
- [ ] 추가 테이블 마이그레이션 (ContentIdea, GeneratedAsset)


---

## 추가 작업 - Studio Admin API 연동

### 추가된 엔드포인트 (admin.py)

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| /api/admin/studio/overview | GET | Studio 대시보드 통계 |
| /api/admin/studio/sessions | GET | 세션 목록 조회 |
| /api/admin/studio/sessions/{id} | GET | 세션 상세 조회 |
| /api/admin/studio/sessions/{id} | DELETE | 세션 삭제 |
| /api/admin/studio/benchmarks | GET | 벤치마크 목록 조회 |
| /api/admin/studio/benchmarks/{id} | GET | 벤치마크 상세 조회 |
| /api/admin/studio/benchmarks/{id} | DELETE | 벤치마크 삭제 |
| /api/admin/studio/characters | GET | 캐릭터 목록 조회 |
| /api/admin/studio/characters/{id} | GET | 캐릭터 상세 (이미지 포함) |

### 사용 예시

```bash
# 토큰 획득
TOKEN=$(curl -s -X POST http://localhost:8003/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}' | jq -r '.access_token')

# Studio 개요
curl -s http://localhost:8003/api/admin/studio/overview \
  -H "Authorization: Bearer $TOKEN"

# 세션 목록
curl -s "http://localhost:8003/api/admin/studio/sessions?limit=10" \
  -H "Authorization: Bearer $TOKEN"

# 벤치마크 목록
curl -s http://localhost:8003/api/admin/studio/benchmarks \
  -H "Authorization: Bearer $TOKEN"

# 캐릭터 목록
curl -s http://localhost:8003/api/admin/studio/characters \
  -H "Authorization: Bearer $TOKEN"
```

### 응답 예시 (Studio Overview)

```json
{
  "total_sessions": 32,
  "active_sessions": 32,
  "completed_sessions": 0,
  "total_benchmarks": 1,
  "total_characters": 2,
  "step_distribution": {
    "benchmarking": 6,
    "channel_name": 16,
    "character": 7,
    "video_ideas": 2
  },
  "recent_sessions": [...]
}
```
