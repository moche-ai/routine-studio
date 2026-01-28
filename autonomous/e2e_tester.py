#!/usr/bin/env python3
nimport sys
sys.path.insert(0, "/data/projects/routine/studio")
from agents.config import agent_settings
"""
E2E 테스터 - Playwright로 웹 UI 전체 테스트
http://100.82.192.109:5182/ 테스트
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser

BASE_URL = agent_settings.frontend_url
LOG_DIR = Path("/data/routine/routine-studio-v2/autonomous/logs")
SCREENSHOT_DIR = Path("/data/routine/routine-studio-v2/autonomous/screenshots")

class E2ETester:
    def __init__(self):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        self.log_file = LOG_DIR / f"e2e_{self.session_id}.log"
        self.errors = []
        self.warnings = []
        self.css_issues = []
        
    def log(self, msg: str, level: str = "INFO"):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [{level}] {msg}"
        print(line, flush=True)
        with open(self.log_file, "a") as f:
            f.write(line + "\n")
    
    async def capture_console_errors(self, page: Page):
        """콘솔 에러 캡처"""
        page.on("console", lambda msg: self.handle_console(msg))
        page.on("pageerror", lambda err: self.errors.append(f"Page Error: {err}"))
    
    def handle_console(self, msg):
        if msg.type == "error":
            self.errors.append(f"Console Error: {msg.text}")
        elif msg.type == "warning":
            self.warnings.append(f"Console Warning: {msg.text}")
    
    async def check_css_issues(self, page: Page) -> list:
        """CSS 문제 확인"""
        issues = []
        
        # 오버플로우 체크
        overflow_elements = await page.evaluate('''() => {
            const issues = [];
            document.querySelectorAll('*').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > window.innerWidth) {
                    issues.push({type: 'overflow-x', selector: el.tagName + (el.className ? '.' + el.className.split(' ')[0] : ''), width: rect.width});
                }
            });
            return issues.slice(0, 10);
        }''')
        issues.extend(overflow_elements)
        
        # 겹침 체크
        overlap_check = await page.evaluate('''() => {
            const issues = [];
            const buttons = document.querySelectorAll('button, a, input');
            buttons.forEach((btn, i) => {
                const rect1 = btn.getBoundingClientRect();
                buttons.forEach((btn2, j) => {
                    if (i >= j) return;
                    const rect2 = btn2.getBoundingClientRect();
                    if (rect1.right > rect2.left && rect1.left < rect2.right &&
                        rect1.bottom > rect2.top && rect1.top < rect2.bottom) {
                        issues.push({type: 'overlap', el1: btn.tagName, el2: btn2.tagName});
                    }
                });
            });
            return issues.slice(0, 5);
        }''')
        issues.extend(overlap_check)
        
        return issues
    
    async def test_page_load(self, page: Page) -> dict:
        """페이지 로드 테스트"""
        self.log("페이지 로드 테스트 시작")
        result = {"passed": False, "load_time": 0, "errors": []}
        
        try:
            start = datetime.now()
            response = await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
            result["load_time"] = (datetime.now() - start).total_seconds()
            
            if response and response.status == 200:
                result["passed"] = True
                self.log(f"페이지 로드 성공 ({result['load_time']:.2f}초)")
            else:
                result["errors"].append(f"HTTP {response.status if response else 'No response'}")
                self.log(f"페이지 로드 실패", "ERROR")
        except Exception as e:
            result["errors"].append(str(e))
            self.log(f"페이지 로드 오류: {e}", "ERROR")
        
        return result
    
    async def test_ui_elements(self, page: Page) -> dict:
        """UI 요소 테스트"""
        self.log("UI 요소 테스트 시작")
        result = {"passed": True, "elements": {}, "missing": []}
        
        # 주요 요소 확인
        selectors = {
            "header": "header, .header, nav",
            "main_content": "main, .main, #app, #root",
            "buttons": "button",
            "inputs": "input, textarea",
            "links": "a[href]"
        }
        
        for name, selector in selectors.items():
            try:
                elements = await page.query_selector_all(selector)
                count = len(elements)
                result["elements"][name] = count
                self.log(f"  {name}: {count}개")
            except:
                result["elements"][name] = 0
        
        return result
    
    async def test_workflow(self, page: Page) -> dict:
        """워크플로우 테스트"""
        self.log("워크플로우 테스트 시작")
        result = {"passed": False, "steps": [], "errors": []}
        
        try:
            # 1. 채팅 입력 찾기
            chat_input = await page.query_selector('input[type="text"], textarea, [contenteditable="true"]')
            if chat_input:
                result["steps"].append("채팅 입력 발견")
                
                # 2. 테스트 메시지 입력
                await chat_input.fill("테스트: 금융 채널 영상 아이디어 3개 추천해줘")
                result["steps"].append("메시지 입력 완료")
                
                # 3. 전송 버튼 찾기
                send_btn = await page.query_selector('button[type="submit"], button:has-text("전송"), button:has-text("Send")')
                if send_btn:
                    await send_btn.click()
                    result["steps"].append("전송 버튼 클릭")
                    
                    # 4. 응답 대기
                    await page.wait_for_timeout(5000)
                    
                    # 5. 응답 확인
                    messages = await page.query_selector_all('.message, .chat-message, [class*="message"]')
                    if len(messages) > 0:
                        result["steps"].append(f"응답 수신 ({len(messages)}개 메시지)")
                        result["passed"] = True
                else:
                    result["errors"].append("전송 버튼 없음")
            else:
                result["errors"].append("채팅 입력 없음")
                
        except Exception as e:
            result["errors"].append(str(e))
            self.log(f"워크플로우 오류: {e}", "ERROR")
        
        return result
    
    async def run_all_tests(self):
        """모든 테스트 실행"""
        self.log("="*60)
        self.log("E2E 테스트 시작")
        self.log(f"URL: {BASE_URL}")
        self.log("="*60)
        
        results = {
            "session_id": self.session_id,
            "url": BASE_URL,
            "timestamp": datetime.now().isoformat(),
            "tests": {}
        }
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1920, "height": 1080})
            page = await context.new_page()
            
            await self.capture_console_errors(page)
            
            # 1. 페이지 로드 테스트
            results["tests"]["page_load"] = await self.test_page_load(page)
            
            if results["tests"]["page_load"]["passed"]:
                # 스크린샷
                await page.screenshot(path=str(SCREENSHOT_DIR / f"load_{self.session_id}.png"))
                
                # 2. UI 요소 테스트
                results["tests"]["ui_elements"] = await self.test_ui_elements(page)
                
                # 3. CSS 이슈 체크
                self.css_issues = await self.check_css_issues(page)
                results["css_issues"] = self.css_issues
                if self.css_issues:
                    self.log(f"CSS 이슈 {len(self.css_issues)}개 발견", "WARN")
                
                # 4. 워크플로우 테스트
                results["tests"]["workflow"] = await self.test_workflow(page)
                
                # 최종 스크린샷
                await page.screenshot(path=str(SCREENSHOT_DIR / f"final_{self.session_id}.png"))
            
            await browser.close()
        
        # 에러/경고 수집
        results["console_errors"] = self.errors
        results["console_warnings"] = self.warnings
        
        # 결과 저장
        result_file = LOG_DIR / f"e2e_result_{self.session_id}.json"
        with open(result_file, "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # 요약
        self.log("\n" + "="*60)
        self.log("테스트 요약")
        self.log("="*60)
        
        all_passed = True
        for test_name, test_result in results["tests"].items():
            status = "✅" if test_result.get("passed") else "❌"
            self.log(f"{status} {test_name}")
            if not test_result.get("passed"):
                all_passed = False
        
        if self.errors:
            self.log(f"\n❌ 콘솔 에러: {len(self.errors)}개")
            for err in self.errors[:5]:
                self.log(f"  - {err[:100]}")
        
        if self.css_issues:
            self.log(f"\n⚠️ CSS 이슈: {len(self.css_issues)}개")
        
        self.log(f"\n결과 저장: {result_file}")
        self.log(f"스크린샷: {SCREENSHOT_DIR}")
        
        return results


async def main():
    tester = E2ETester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
