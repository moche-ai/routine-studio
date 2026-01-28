#!/usr/bin/env python3
"""
마스터 런너 - 모든 자율 테스트 관리
1. 품질 테스트 (완벽 3회까지)
2. E2E 웹 UI 테스트
3. CSS/에러 수정 제안
"""

import asyncio
import json
import subprocess
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/data/routine/routine-studio-v2/autonomous")
LOG_DIR = BASE_DIR / "logs"
STATE_FILE = BASE_DIR / "master_state.json"


def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [MASTER] [{level}] {msg}"
    print(line, flush=True)


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "started_at": datetime.now().isoformat(),
        "quality_test_complete": False,
        "e2e_test_complete": False,
        "e2e_issues_found": [],
        "fixes_applied": []
    }


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


async def run_quality_test():
    """품질 테스트 실행"""
    log("품질 테스트 시작...")
    proc = await asyncio.create_subprocess_exec(
        "python3", str(BASE_DIR / "auto_improve.py"),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        print(line.decode().strip(), flush=True)
    
    await proc.wait()
    return proc.returncode == 0


async def run_e2e_test():
    """E2E 테스트 실행"""
    log("E2E 테스트 시작...")
    proc = await asyncio.create_subprocess_exec(
        "python3", str(BASE_DIR / "e2e_tester.py"),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        print(line.decode().strip(), flush=True)
    
    await proc.wait()
    
    # 결과 파일 확인
    result_files = list(LOG_DIR.glob("e2e_result_*.json"))
    if result_files:
        latest = max(result_files, key=lambda x: x.stat().st_mtime)
        with open(latest) as f:
            return json.load(f)
    return {}


async def main():
    log("="*60)
    log("마스터 런너 시작")
    log("="*60)
    
    state = load_state()
    
    # 1. 품질 테스트 (완벽 3회까지)
    if not state["quality_test_complete"]:
        log("\n[1/2] 품질 테스트 실행")
        success = await run_quality_test()
        state["quality_test_complete"] = success
        save_state(state)
        log(f"품질 테스트 완료: {'성공' if success else '실패'}")\n    
    # 2. E2E 테스트
    log("\n[2/2] E2E 테스트 실행")
    e2e_result = await run_e2e_test()
    
    if e2e_result:
        state["e2e_test_complete"] = True
        
        # 이슈 확인
        if e2e_result.get("console_errors"):
            state["e2e_issues_found"].extend(e2e_result["console_errors"])
        if e2e_result.get("css_issues"):
            state["e2e_issues_found"].extend([str(i) for i in e2e_result["css_issues"]])
        
        save_state(state)
    
    # 최종 보고
    log("\n" + "="*60)
    log("자율 테스트 완료")
    log("="*60)
    log(f"품질 테스트: {'✅ 완료' if state['quality_test_complete'] else '❌ 미완료'}")
    log(f"E2E 테스트: {'✅ 완료' if state['e2e_test_complete'] else '❌ 미완료'}")
    
    if state["e2e_issues_found"]:
        log(f"\n발견된 이슈: {len(state['e2e_issues_found'])}개")
        for issue in state["e2e_issues_found"][:10]:
            log(f"  - {issue[:100]}")
    
    log("\n상태 저장: " + str(STATE_FILE))


if __name__ == "__main__":
    asyncio.run(main())
