#!/usr/bin/env python3
nimport sys
sys.path.insert(0, "/data/projects/routine/studio")
from agents.config import agent_settings
"""
자율 개선 시스템 v2 - Claude 검수 + 자동 수정
- 생성: gpt-oss-120b-longctx
- 검수 & 피드백 & 수정: Claude Code
"""

import asyncio
import httpx
import json
import subprocess
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
import random

LLM_BASE_URL = agent_settings.llm_api_url
LLM_MODEL = "gpt-oss-120b-longctx"
BASE_DIR = Path("/data/routine/routine-studio-v2/autonomous")
LOG_DIR = BASE_DIR / "logs"
RESULTS_DIR = BASE_DIR / "results"
STATE_FILE = BASE_DIR / "state.json"
PROMPTS_FILE = BASE_DIR / "current_prompts.json"

PERFECT_THRESHOLD = 9.5
REQUIRED_PERFECT_COUNT = 3

DEFAULT_PROMPTS = {
    "video_ideas": {
        "template": """당신은 100만 구독자 금융 유튜버의 기획자입니다.

채널명: {channel_name}
컨셉: {concept}

다음 기준으로 영상 아이디어 10개를 만들어주세요:
1. 독창성: 다른 채널에서 본 적 없는 신선한 각도
2. 후킹력: 스크롤을 멈추게 하는 제목과 첫 문장
3. 실용성: 시청자가 바로 적용할 수 있는 내용
4. 감정 유발: 궁금증, 분노, 희망 등 강한 감정

JSON 형식으로만 응답 (다른 텍스트 없이):
{{"ideas": [{{"title": "클릭을 부르는 제목", "hook": "첫 5초 대사", "summary": "2-3줄 요약", "target_emotion": "궁금증/분노/희망 등"}}]}}""",
        "temperature": 0.85
    },
    "script": {
        "template": """당신은 조회수 100만을 찍는 금융 유튜버 {character_name}입니다.

제목: "{video_title}"

다음 구조로 10-15분 대본을 작성하세요:

[오프닝 - 30초] 시청자가 "어? 이거 나한테 하는 말이야?"라고 느낄 상황
[인트로 - 1분] 자기소개 + 구독 유도
[본론1 - 3분] 충격적 사실, 통계
[본론2 - 3분] 해결책, 실제 금액 계산
[본론3 - 3분] 심화 + 심리학적 분석
[결론 - 1분] 핵심 요약 + CTA

스타일: 친구에게 말하듯, 약간의 분노와 진심

JSON 형식으로만 응답 (다른 텍스트 없이):
{{"script": {{"opening": "...", "intro": "...", "body1": "...", "body2": "...", "body3": "...", "conclusion": "..."}}, "word_count": 숫자, "estimated_minutes": 숫자}}""",
        "temperature": 0.75
    }
}


class AutoImprover:
    def __init__(self):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        self.log_file = LOG_DIR / f"claude_v2_{self.session_id}.log"
        self.state = self.load_state()
        self.prompts = self.load_prompts()

    def load_state(self) -> Dict:
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)
        return {
            "perfect_count": 0,
            "total_iterations": 0,
            "best_scores": {"video_ideas": 0, "script": 0},
            "improvements": {"video_ideas": [], "script": []},
            "history": []
        }

    def save_state(self):
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def load_prompts(self) -> Dict:
        if PROMPTS_FILE.exists():
            with open(PROMPTS_FILE) as f:
                return json.load(f)
        return DEFAULT_PROMPTS.copy()

    def save_prompts(self):
        with open(PROMPTS_FILE, "w") as f:
            json.dump(self.prompts, f, ensure_ascii=False, indent=2)

    def log(self, msg: str, level: str = "INFO"):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [{level}] {msg}"
        print(line, flush=True)
        with open(self.log_file, "a") as f:
            f.write(line + "\n")

    async def call_llm(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4096) -> str:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{LLM_BASE_URL}/chat/completions",
                json={
                    "model": LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def call_claude(self, prompt: str, timeout: int = 180) -> str:
        """Claude Code 호출 (--dangerously-skip-permissions)"""
        try:
            result = subprocess.run(
                [
                    "npx", "@anthropic-ai/claude-code",
                    "--print",
                    "--dangerously-skip-permissions",
                    "-p", prompt
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd="/tmp",
                env={**os.environ, "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "")}
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            self.log("Claude 타임아웃", "WARN")
            return ""
        except Exception as e:
            self.log(f"Claude 오류: {e}", "ERROR")
            return ""

    def extract_json(self, text: str, required_keys: List[str] = None) -> Optional[Dict]:
        """여러 방법으로 JSON 추출 시도"""
        if not text:
            return None

        # 방법 1: 코드 블록에서 JSON 추출
        code_block_patterns = [
            r"```json\s*([\s\S]*?)```",
            r"```\s*([\s\S]*?)```",
        ]
        for pattern in code_block_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    data = json.loads(match.strip())
                    if required_keys is None or any(k in data for k in required_keys):
                        return data
                except:
                    continue

        # 방법 2: 중첩 괄호를 고려한 JSON 추출
        candidates = []
        i = 0
        while i < len(text):
            if text[i] == '{':
                depth = 0
                start = i
                for j in range(i, len(text)):
                    if text[j] == '{':
                        depth += 1
                    elif text[j] == '}':
                        depth -= 1
                        if depth == 0:
                            candidates.append(text[start:j+1])
                            break
                i = j + 1 if 'j' in dir() else i + 1
            else:
                i += 1

        # 후보 중 유효한 JSON 찾기 (큰 것부터)
        candidates.sort(key=len, reverse=True)
        for candidate in candidates:
            try:
                data = json.loads(candidate)
                if required_keys is None or any(k in data for k in required_keys):
                    return data
            except:
                continue

        # 방법 3: 단순 추출 (fallback)
        try:
            if "{" in text:
                start = text.find("{")
                end = text.rfind("}") + 1
                if end > start:
                    data = json.loads(text[start:end])
                    return data
        except:
            pass

        return None

    def claude_review_and_improve(self, task: str, content: Dict, current_prompt: str) -> Dict:
        """Claude가 검수하고 프롬프트 개선안 제시"""
        self.log(f"Claude 검수 중... ({task})")

        content_str = json.dumps(content, ensure_ascii=False, indent=2)[:5000]
        prompt_str = current_prompt[:2000]

        review_prompt = f'''당신은 최고급 유튜브 콘텐츠 전문가입니다.

## 검수할 콘텐츠 ({task})
```json
{content_str}
```

## 현재 사용 중인 프롬프트
```
{prompt_str}
```

## 평가 기준 (각 1-10점)
1. 독창성: Gemini/ChatGPT/Grok 수준의 퀄리티인가?
2. 후킹력: 실제 100만 조회수 영상 수준인가?
3. 실용성: 시청자가 바로 행동할 수 있는가?
4. 구조: 전문 PD가 만든 수준인가?
5. 감정: 시청자 감정을 강하게 자극하는가?

9.5점 이상 = 완벽 (워크플로우 통과)

## 응답 형식 (JSON만, 다른 텍스트 없이)
```json
{{
    "scores": {{"독창성": 점수, "후킹력": 점수, "실용성": 점수, "구조": 점수, "감정": 점수}},
    "average": 평균점수,
    "is_perfect": true또는false,
    "problems": ["현재 콘텐츠의 문제점들"],
    "improved_prompt": "9.5점을 받을 수 있도록 개선된 전체 프롬프트"
}}
```'''

        response = self.call_claude(review_prompt)
        result = self.extract_json(response, required_keys=["scores", "average"])

        if result:
            avg = result.get("average", 0)
            is_perfect = result.get("is_perfect", False) or avg >= PERFECT_THRESHOLD
            self.log(f"Claude 평가: {avg}/10 ({'완벽' if is_perfect else '개선 필요'})")

            # 문제점 저장
            problems = result.get("problems", [])
            if problems:
                if "improvements" not in self.state:
                    self.state["improvements"] = {"video_ideas": [], "script": []}
                if task not in self.state["improvements"]:
                    self.state["improvements"][task] = []
                for p in problems[:2]:  # 최대 2개
                    if p not in self.state["improvements"][task]:
                        self.state["improvements"][task].append(p)
                        if len(self.state["improvements"][task]) > 5:
                            self.state["improvements"][task] = self.state["improvements"][task][-5:]

            # 프롬프트 개선안이 있으면 저장
            if result.get("improved_prompt") and not is_perfect:
                self.prompts[task]["template"] = result["improved_prompt"]
                self.save_prompts()
                self.log(f"프롬프트 업데이트됨: {task}")

            return {
                "score": avg,
                "is_perfect": is_perfect,
                "evaluation": result
            }

        self.log(f"Claude 응답 파싱 실패 - 응답 길이: {len(response)}", "WARN")
        if response:
            self.log(f"응답 미리보기: {response[:200]}...", "DEBUG")
        return {"score": 5.0, "is_perfect": False}

    def safe_format(self, template: str, params: Dict) -> str:
        """안전한 템플릿 치환 - .format() 대신 사용"""
        result = template
        for key, value in params.items():
            # {key} 패턴만 치환 ({{key}}는 무시)
            result = re.sub(
                r'(?<!\{)\{' + re.escape(key) + r'\}(?!\})',
                str(value),
                result
            )
        return result

    async def generate_and_evaluate(self, task: str, params: Dict) -> Dict:
        prompt_config = self.prompts[task]
        template = prompt_config["template"]

        # 안전한 템플릿 치환 시도
        try:
            prompt = self.safe_format(template, params)
        except Exception as e:
            self.log(f"템플릿 치환 실패, 기본 프롬프트로 복구: {e}", "WARN")
            # 손상된 프롬프트를 기본값으로 복구
            self.prompts[task] = DEFAULT_PROMPTS[task].copy()
            self.save_prompts()
            prompt = self.safe_format(self.prompts[task]["template"], params)

        temperature = prompt_config.get("temperature", 0.8)

        # gpt-oss로 생성
        self.log(f"{task} 생성 중 (gpt-oss, temp={temperature})...")

        try:
            content = await self.call_llm(prompt, temperature=temperature, max_tokens=8192)
        except Exception as e:
            self.log(f"LLM 호출 실패: {e}", "ERROR")
            return {"content": None, "score": 0, "is_perfect": False, "error": str(e)}

        required_keys = ["ideas"] if task == "video_ideas" else ["script"]
        data = self.extract_json(content, required_keys=required_keys)

        if not data:
            self.log(f"생성 실패 (JSON 파싱) - 응답 길이: {len(content)}", "WARN")
            if content:
                self.log(f"응답 미리보기: {content[:300]}...", "DEBUG")
            return {"content": content, "score": 0, "is_perfect": False, "parse_error": True}

        # Claude 검수 + 프롬프트 개선
        review = self.claude_review_and_improve(task, data, prompt)

        return {
            "content": data,
            "score": review.get("score", 0),
            "is_perfect": review.get("is_perfect", False),
            "evaluation": review.get("evaluation")
        }

    async def run_iteration(self) -> bool:
        self.state["total_iterations"] += 1
        iteration = self.state["total_iterations"]

        self.log("=" * 60)
        self.log(f"반복 #{iteration} (완벽: {self.state['perfect_count']}/{REQUIRED_PERFECT_COUNT})")
        self.log(f"목표: Claude 검수 {PERFECT_THRESHOLD}점 이상")
        self.log("=" * 60)

        is_perfect = True

        # 영상 아이디어
        ideas_result = await self.generate_and_evaluate("video_ideas", {
            "channel_name": random.choice(["머니브레인", "투자연구소", "부의 공식"]),
            "concept": "경제/투자/재테크 교육"
        })

        if ideas_result.get("parse_error"):
            self.log("아이디어 생성 파싱 실패, 다음 반복에서 재시도", "WARN")
            return False

        if not ideas_result.get("is_perfect"):
            is_perfect = False

        # 대본
        video_title = "가짜 부자의 심리학"
        content = ideas_result.get("content", {})
        if isinstance(content, dict) and content.get("ideas"):
            video_title = content["ideas"][0].get("title", video_title)

        script_result = await self.generate_and_evaluate("script", {
            "video_title": video_title,
            "character_name": random.choice(["닉", "민수", "제이"])
        })

        if script_result.get("parse_error"):
            self.log("대본 생성 파싱 실패, 다음 반복에서 재시도", "WARN")
            return False

        if not script_result.get("is_perfect"):
            is_perfect = False

        # 결과 처리
        if is_perfect:
            self.state["perfect_count"] += 1
            self.log(f"완벽! ({self.state['perfect_count']}/{REQUIRED_PERFECT_COUNT})")
        else:
            self.log(f"개선 중 - 아이디어: {ideas_result.get('score', 0):.1f}, 대본: {script_result.get('score', 0):.1f}")

        # 최고 점수 갱신
        for task, result in [("video_ideas", ideas_result), ("script", script_result)]:
            score = result.get("score", 0)
            if score > self.state["best_scores"].get(task, 0):
                self.state["best_scores"][task] = score
                self.log(f"최고 {task}: {score:.1f}")

        # 저장
        self.state["history"].append({
            "iteration": iteration,
            "timestamp": datetime.now().isoformat(),
            "ideas_score": ideas_result.get("score", 0),
            "script_score": script_result.get("score", 0),
            "is_perfect": is_perfect
        })

        result_file = RESULTS_DIR / f"iter_{iteration}_{self.session_id}.json"
        with open(result_file, "w") as f:
            json.dump({
                "iteration": iteration,
                "ideas": ideas_result,
                "script": script_result
            }, f, ensure_ascii=False, indent=2, default=str)

        self.save_state()
        return self.state["perfect_count"] >= REQUIRED_PERFECT_COUNT

    async def run(self):
        self.log("#" * 60)
        self.log("자율 개선 시스템 v2 (개선된 JSON 파싱)")
        self.log("생성: gpt-oss-120b | 검수+개선: Claude")
        self.log(f"목표: {PERFECT_THRESHOLD}점 이상 {REQUIRED_PERFECT_COUNT}회")
        self.log("#" * 60)

        consecutive_errors = 0
        max_consecutive_errors = 5

        while True:
            try:
                done = await self.run_iteration()
                consecutive_errors = 0  # 성공하면 리셋

                if done:
                    self.log("\n" + "=" * 60)
                    self.log("목표 달성!")
                    self.log(f"총 {self.state['total_iterations']}회 반복")
                    self.log(f"최고 - 아이디어: {self.state['best_scores']['video_ideas']:.1f}")
                    self.log(f"최고 - 대본: {self.state['best_scores']['script']:.1f}")
                    self.log("=" * 60)
                    break

                self.log("\n60초 후 다음 반복...\n")
                await asyncio.sleep(60)

            except Exception as e:
                consecutive_errors += 1
                self.log(f"오류 ({consecutive_errors}/{max_consecutive_errors}): {e}", "ERROR")

                if consecutive_errors >= max_consecutive_errors:
                    self.log(f"연속 {max_consecutive_errors}회 오류, 5분 대기 후 계속", "WARN")
                    await asyncio.sleep(300)
                    consecutive_errors = 0
                else:
                    self.log("60초 후 재시도...")
                    await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(AutoImprover().run())
