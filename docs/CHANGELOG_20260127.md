# 변경 이력 - 2026-01-27

## 개요
JSON 파일 기반 저장소를 SQLite DB로 마이그레이션 + 어드민 대시보드 STUDIO 메뉴 연동 + 삭제 API 추가

---

## 신규 기능

### 1. DB 마이그레이션 완료
- Session Service: apps/api/services/session_service.py
- Benchmark Cache DB: agents/benchmarker/cache_service_db.py
- Orchestrator 수정: USE_DB_STORAGE 플래그 추가

### 2. 어드민 대시보드 연동
- Studio Router: apps/api/routes/studio.py
- 멤버, 세션, 채널, 캐릭터, 프로젝트, 스크립트, 미디어, 분석 API

### 3. DELETE API 추가
- 세션/프로젝트/채널/캐릭터/벤치마크/멤버 삭제
- DB cascade 삭제 + 파일 정리

### 4. 벤치마크 퀵 액션
- 캐시된 벤치마크 리포트에 선택 옵션 추가

---

## 버그 수정

### 사이드바 선택 효과 중복
- 문제점: NavLink prefix 매칭으로 여러 항목 선택됨
- 수정: NavLink에 end prop 추가

---

## 데이터베이스 현황

- Projects: 32
- Characters: 2
- Benchmarks: 1
