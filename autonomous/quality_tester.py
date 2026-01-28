#!/usr/bin/env python3
nimport sys
sys.path.insert(0, "/data/projects/routine/studio")
from agents.config import agent_settings
"""
자율 퀄리티 테스트 시스템
gpt-oss-120b-longctx를 사용하여 영상 아이디어 및 대본 생성 품질 테스트
"""

import asyncio
import httpx
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# 설정
LLM_BASE_URL = agent_settings.llm_api_url
LLM_MODEL = "gpt-oss-120b-longctx"
LOG_DIR = Path("/data/routine/routine-studio-v2/autonomous/logs")
RESULTS_DIR = Path("/data/routine/routine-studio-v2/autonomous/results")

# 품질 평가 기준
QUALITY_CRITERIA = {
    "video_ideas": {
        "uniqueness": "아이디어가 독창적이고 흔하지 않은가?",
        "hook_power": "후킹 문장이 클릭을 유도하는가?",
        "feasibility": "실제 영상으로 만들기 적합한가?",
        "audience_fit": "대중이 관심 가질 주제인가?"
    },
    "script": {
        "opening_hook": "오프닝이 시청자를 즉시 끌어들이는가?",
        "structure": "대본 구조가 논리적인가?",
        "storytelling": "스토리텔링이 흥미로운가?",
        "actionable": "시청자가 따라할 수 있는 조언이 있는가?",
        "emotional": "감정적 연결이 있는가?",
        "length": "10-15분 분량에 적합한가?"
    }
}

# 프롬프트
PROMPTS = {
    "video_ideas": """금융이랑 돈 관련 채널에 올릴 독창적인 영상 아이디어 10개를 만들어줘.
대중들이 좋아할 만하면서도, 흔하지 않고 사람들이 잘 모르는 흥미로운 주제여야 해.

채널명: {channel_name}
채널 컨셉: {concept}

참고할 인기 주제들:
- 가짜 부자 vs 진짜 부자의 심리
- 월급 관리의 숨겨진 비밀
- 부자들이 절대 말 안 하는 것들
- 경제 위기에서 살아남는 법
- 투자 심리학의 함정

각 아이디어에 대해:
1. 제목 (클릭을 유도하는 형태)
2. 후킹 문장 (영상 시작 5초)
3. 핵심 내용 요약 (2-3문장)

JSON 형식으로만 응답해:
{{"ideas": [{{"title": "제목", "hook": "후킹 문장", "summary": "요약", "target_emotion": "노리는 감정"}}]}}""",

    "script": """이 제목으로 {character_name}의 독특한 금융 교육 스타일을 살려서 유튜브 대본을 써줘:
"{video_title}"

대본 구조:
1. **오프닝 훅** (30초): 시청자가 "이거 내 얘긴데?"라고 생각할 상황
2. **인트로** (1분): 자기소개 + 구독 유도
3. **본론1** (3분): 문제 정의 + 충격적 통계
4. **본론2** (3분): 핵심 해결책 + 실제 사례
5. **본론3** (3분): 심화 내용 + 심리학적 분석
6. **결론** (1분): 액션 아이템 + CTA

스타일:
- 친구처럼 자연스럽게
- 통계와 수치 포함
- 실제 금액 예시
- 심리학적 설명
- "사람들이 진짜 모르는 게..." 같은 표현

JSON 형식으로 응답:
{{"script": {{"opening": "...", "intro": "...", "body1": "...", "body2": "...", "body3": "...", "conclusion": "..."}}, "word_count": 숫자, "estimated_minutes": 숫자}}""",

    "evaluate": """다음 {content_type}의 품질을 평가해줘:

{content}

평가 기준:
{criteria}

각 기준에 대해 1-10점으로 평가하고, 개선 제안을 해줘.

JSON 형식으로 응답:
{{"scores": {{"기준1": 점수, ...}}, "average": 평균점수, "strengths": ["강점들"], "improvements": ["개선점들"], "overall_grade": "A/B/C/D/F"}}"""
}


class QualityTester:
    def __init__(self):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = LOG_DIR / f"session_{self.session_id}.log"
        self.results_file = RESULTS_DIR / f"results_{self.session_id}.json"
        self.results = {
            "session_id": self.session_id,
            "started_at": datetime.now().isoformat(),
            "tests": [],
            "summary": {}
        }
        
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}"
        print(log_line, flush=True)
        with open(self.log_file, "a") as f:
            f.write(log_line + "\n")
    
    async def call_llm(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4096) -> str:
        """LLM 호출"""
        async with httpx.AsyncClient(timeout=180.0) as client:
            try:
                response = await client.post(
                    f"{LLM_BASE_URL}/chat/completions",
                    json={
                        "model": LLM_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                self.log(f"LLM 호출 실패: {e}", "ERROR")
                raise
    
    def extract_json(self, text: str) -> Optional[Dict]:
        """JSON 추출"""
        try:
            if "{" in text:
                start = text.find("{")
                end = text.rfind("}") + 1
                return json.loads(text[start:end])
        except:
            pass
        return None
    
    async def generate_video_ideas(self, channel_name: str = "머니브레인", concept: str = "경제/투자 교육") -> Dict:
        """영상 아이디어 생성"""
        self.log(f"영상 아이디어 생성 시작 - 채널: {channel_name}")
        
        prompt = PROMPTS["video_ideas"].format(
            channel_name=channel_name,
            concept=concept
        )
        
        response = await self.call_llm(prompt, temperature=0.85, max_tokens=4096)
        data = self.extract_json(response)
        
        if data and "ideas" in data:
            self.log(f"아이디어 {len(data['ideas'])}개 생성 완료")
            return data
        else:
            self.log("JSON 파싱 실패, raw 응답 저장", "WARN")
            return {"raw": response, "ideas": []}
    
    async def generate_script(self, video_title: str, character_name: str = "닉") -> Dict:
        """대본 생성"""
        self.log(f"대본 생성 시작 - 제목: {video_title}")
        
        prompt = PROMPTS["script"].format(
            video_title=video_title,
            character_name=character_name
        )
        
        response = await self.call_llm(prompt, temperature=0.7, max_tokens=8192)
        data = self.extract_json(response)
        
        if data and "script" in data:
            self.log(f"대본 생성 완료 - 예상 {data.get('estimated_minutes', '?')}분")
            return data
        else:
            self.log("JSON 파싱 실패, raw 응답 저장", "WARN")
            return {"raw": response, "script": {}}
    
    async def evaluate_quality(self, content: Any, content_type: str) -> Dict:
        """품질 평가"""
        self.log(f"{content_type} 품질 평가 시작")
        
        criteria = QUALITY_CRITERIA.get(content_type, {})
        criteria_text = "\n".join([f"- {k}: {v}" for k, v in criteria.items()])
        
        content_str = json.dumps(content, ensure_ascii=False, indent=2) if isinstance(content, dict) else str(content)
        
        prompt = PROMPTS["evaluate"].format(
            content_type=content_type,
            content=content_str[:3000],  # 길이 제한
            criteria=criteria_text
        )
        
        response = await self.call_llm(prompt, temperature=0.3, max_tokens=2048)
        data = self.extract_json(response)
        
        if data and "scores" in data:
            avg = data.get("average", sum(data["scores"].values()) / len(data["scores"]))
            self.log(f"평가 완료 - 평균: {avg:.1f}/10, 등급: {data.get('overall_grade', '?')}")
            return data
        else:
            return {"raw": response, "average": 0}
    
    async def run_full_test(self, iterations: int = 3):
        """전체 테스트 실행"""
        self.log("="*60)
        self.log(f"자율 퀄리티 테스트 시작 - {iterations}회 반복")
        self.log("="*60)
        
        all_scores = {"video_ideas": [], "script": []}
        
        for i in range(iterations):
            self.log(f"\n--- 반복 {i+1}/{iterations} ---")
            
            test_result = {
                "iteration": i + 1,
                "timestamp": datetime.now().isoformat()
            }
            
            # 1. 영상 아이디어 생성 및 평가
            ideas_data = await self.generate_video_ideas()
            ideas_eval = await self.evaluate_quality(ideas_data, "video_ideas")
            
            test_result["video_ideas"] = {
                "content": ideas_data,
                "evaluation": ideas_eval
            }
            all_scores["video_ideas"].append(ideas_eval.get("average", 0))
            
            # 2. 첫 번째 아이디어로 대본 생성
            if ideas_data.get("ideas"):
                first_idea = ideas_data["ideas"][0]
                script_data = await self.generate_script(first_idea.get("title", "테스트 제목"))
                script_eval = await self.evaluate_quality(script_data, "script")
                
                test_result["script"] = {
                    "content": script_data,
                    "evaluation": script_eval
                }
                all_scores["script"].append(script_eval.get("average", 0))
            
            self.results["tests"].append(test_result)
            
            # 중간 저장
            self.save_results()
            
            # 간격
            if i < iterations - 1:
                self.log("다음 반복까지 10초 대기...")
                await asyncio.sleep(10)
        
        # 최종 요약
        self.results["summary"] = {
            "video_ideas_avg": sum(all_scores["video_ideas"]) / len(all_scores["video_ideas"]) if all_scores["video_ideas"] else 0,
            "script_avg": sum(all_scores["script"]) / len(all_scores["script"]) if all_scores["script"] else 0,
            "total_tests": iterations,
            "completed_at": datetime.now().isoformat()
        }
        
        self.save_results()
        
        self.log("\n" + "="*60)
        self.log("테스트 완료!")
        self.log(f"영상 아이디어 평균: {self.results['summary']['video_ideas_avg']:.1f}/10")
        self.log(f"대본 평균: {self.results['summary']['script_avg']:.1f}/10")
        self.log(f"결과 저장: {self.results_file}")
        self.log("="*60)
        
        return self.results
    
    def save_results(self):
        with open(self.results_file, "w") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="자율 퀄리티 테스트")
    parser.add_argument("--iterations", "-i", type=int, default=3, help="반복 횟수")
    parser.add_argument("--continuous", "-c", action="store_true", help="연속 실행 모드")
    args = parser.parse_args()
    
    tester = QualityTester()
    
    if args.continuous:
        while True:
            try:
                await tester.run_full_test(iterations=args.iterations)
                tester.log("\n1시간 후 다시 실행...")
                await asyncio.sleep(3600)
                tester = QualityTester()  # 새 세션
            except KeyboardInterrupt:
                tester.log("중단됨")
                break
            except Exception as e:
                tester.log(f"오류 발생: {e}", "ERROR")
                await asyncio.sleep(60)
    else:
        await tester.run_full_test(iterations=args.iterations)


if __name__ == "__main__":
    asyncio.run(main())
