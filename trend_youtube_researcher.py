"""
트렌드 기반 YouTube 채널 딥리서치 서비스
채널명/분야 기반 트렌드 키워드 생성 + 채널 스코어링 + 자막 분석
"""
import asyncio
import json
import re
import requests
import subprocess
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    pass

SCREENSHOT_DIR = Path("/data/routine/routine-studio-v2/screenshots/youtube")
LLM_URL = "http://localhost:8017/v1/chat/completions"


class TrendYouTubeResearcher:
    def __init__(self):
        self.browser = None
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    async def _ensure_browser(self):
        if self.browser is None:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
        return self.browser

    def generate_trending_keywords(self, channel_name: str, field: str, count: int = 5) -> List[str]:
        """채널명과 분야 기반 트렌드 키워드 생성"""
        prompt = f"""'{channel_name}' 채널의 '{field}' 분야에서 현재 트렌드인 YouTube 검색 키워드 {count}개를 생성해줘.

요구사항:
- 실제 YouTube에서 검색량이 높을 만한 키워드
- 해당 분야의 최신 트렌드 반영
- 구체적이고 검색하기 좋은 형태
- 한국어 키워드

JSON 형식으로만 응답:
{{"keywords": ["키워드1", "키워드2", ...]}}"""

        try:
            resp = requests.post(LLM_URL, json={
                'model': 'gpt-oss-120b-longctx',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 512,
                'temperature': 0.7
            }, timeout=60)

            if resp.status_code == 200:
                content = resp.json()['choices'][0]['message']['content']
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0]
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0]
                result = json.loads(content.strip())
                return result.get('keywords', [field])
            return [field]
        except Exception as e:
            print(f"Keyword generation error: {e}")
            return [field]

    def _parse_count(self, text: str) -> int:
        if not text:
            return 0
        text = text.replace(',', '').replace(' ', '')
        multipliers = {'만': 10000, '천': 1000, 'K': 1000, 'M': 1000000}
        for suffix, mult in multipliers.items():
            if suffix in text:
                num = re.findall(r'[\d.]+', text)
                if num:
                    return int(float(num[0]) * mult)
        nums = re.findall(r'\d+', text)
        return int(nums[0]) if nums else 0

    def _parse_days_ago(self, text: str) -> Optional[int]:
        if not text:
            return None
        patterns = [
            (r'(\d+)\s*분\s*전', lambda x: 0),
            (r'(\d+)\s*시간\s*전', lambda x: 0),
            (r'(\d+)\s*일\s*전', lambda x: int(x)),
            (r'(\d+)\s*주\s*전', lambda x: int(x) * 7),
            (r'(\d+)\s*개월\s*전', lambda x: int(x) * 30),
            (r'(\d+)\s*년\s*전', lambda x: int(x) * 365),
        ]
        for pattern, converter in patterns:
            match = re.search(pattern, text)
            if match:
                return converter(match.group(1))
        return None

    def download_transcript(self, video_url: str) -> Optional[str]:
        """yt-dlp로 자막 다운로드"""
        try:
            video_id = None
            if 'v=' in video_url:
                video_id = video_url.split('v=')[1].split('&')[0]
            elif 'youtu.be/' in video_url:
                video_id = video_url.split('youtu.be/')[1].split('?')[0]

            if not video_id:
                return None

            output_path = SCREENSHOT_DIR / f"transcript_{video_id}"

            cmd = [
                'yt-dlp',
                '--skip-download',
                '--write-auto-sub',
                '--sub-lang', 'ko,en',
                '--sub-format', 'vtt',
                '-o', str(output_path),
                f'https://www.youtube.com/watch?v={video_id}'
            ]

            subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            for ext in ['.ko.vtt', '.en.vtt', '.vtt']:
                vtt_path = Path(str(output_path) + ext)
                if vtt_path.exists():
                    content = vtt_path.read_text(encoding='utf-8')
                    lines = []
                    for line in content.split('\n'):
                        if not re.match(r'^\d{2}:\d{2}', line) and not line.startswith('WEBVTT') and line.strip():
                            lines.append(line.strip())
                    return ' '.join(lines)[:5000]

            return None
        except Exception as e:
            print(f"Transcript error: {e}")
            return None

    async def get_channel_with_videos(self, channel_url: str) -> Dict:
        """채널 정보 + 최근 영상 수집"""
        browser = await self._ensure_browser()
        page = await browser.new_page()

        try:
            videos_url = channel_url.rstrip('/') + '/videos'
            await page.goto(videos_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)

            data = await page.evaluate('''
                () => {
                    const result = {
                        name: '',
                        subscribers: '',
                        videos: []
                    };

                    const nameEl = document.querySelector('#channel-name');
                    if (nameEl) result.name = nameEl.textContent.trim();

                    const subsEl = document.querySelector('#subscriber-count');
                    if (subsEl) result.subscribers = subsEl.textContent.trim();

                    const items = document.querySelectorAll('ytd-rich-item-renderer');
                    for (let i = 0; i < Math.min(items.length, 10); i++) {
                        const item = items[i];
                        const titleEl = item.querySelector('#video-title');
                        const linkEl = item.querySelector('#video-title-link');
                        const viewsEl = item.querySelector('#metadata-line span:first-child');
                        const dateEl = item.querySelector('#metadata-line span:last-child');

                        if (titleEl) {
                            result.videos.push({
                                title: titleEl.textContent.trim(),
                                url: linkEl ? linkEl.href : '',
                                views: viewsEl ? viewsEl.textContent.trim() : '',
                                date: dateEl ? dateEl.textContent.trim() : ''
                            });
                        }
                    }
                    return result;
                }
            ''')

            return {**data, 'url': channel_url}
        finally:
            await page.close()

    def calculate_score(self, channel: Dict) -> Dict:
        """채널 스코어 계산"""
        scores = {'subscriber': 0, 'activity': 0, 'engagement': 0, 'growth': 0, 'total': 0}

        subs = self._parse_count(channel.get('subscribers', ''))

        # 구독자 점수 (30점)
        if subs >= 1000000: scores['subscriber'] = 30
        elif subs >= 500000: scores['subscriber'] = 27
        elif subs >= 100000: scores['subscriber'] = 24
        elif subs >= 50000: scores['subscriber'] = 20
        elif subs >= 10000: scores['subscriber'] = 15
        else: scores['subscriber'] = 10

        # 활동성 점수 (25점)
        videos = channel.get('videos', [])
        if videos:
            days = [self._parse_days_ago(v.get('date', '')) for v in videos[:5]]
            days = [d for d in days if d is not None]
            if days:
                avg = sum(days) / len(days)
                if avg <= 7: scores['activity'] = 25
                elif avg <= 14: scores['activity'] = 20
                elif avg <= 30: scores['activity'] = 15
                else: scores['activity'] = 10

        # 참여도 점수 (25점)
        if videos and subs > 0:
            views = [self._parse_count(v.get('views', '')) for v in videos[:5]]
            views = [v for v in views if v > 0]
            if views:
                ratio = (sum(views) / len(views)) / subs
                if ratio >= 0.3: scores['engagement'] = 25
                elif ratio >= 0.1: scores['engagement'] = 20
                elif ratio >= 0.05: scores['engagement'] = 15
                else: scores['engagement'] = 10

        # 성장 점수 (20점)
        if len(videos) >= 6:
            recent = [self._parse_count(v.get('views', '')) for v in videos[:3]]
            older = [self._parse_count(v.get('views', '')) for v in videos[3:6]]
            r_avg = sum(recent) / len(recent) if recent else 0
            o_avg = sum(older) / len(older) if older else 1
            if o_avg > 0:
                growth = (r_avg - o_avg) / o_avg
                if growth >= 0.5: scores['growth'] = 20
                elif growth >= 0.2: scores['growth'] = 15
                elif growth >= 0: scores['growth'] = 10
                else: scores['growth'] = 5

        scores['total'] = scores['subscriber'] + scores['activity'] + scores['engagement'] + scores['growth']
        return scores

    async def search_channels(self, keyword: str, max_channels: int = 8) -> List[Dict]:
        """키워드로 채널 검색 및 스코어링"""
        browser = await self._ensure_browser()
        page = await browser.new_page()

        try:
            url = f'https://www.youtube.com/results?search_query={keyword}&sp=EgIQAg%253D%253D'
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)

            channels = await page.evaluate(f'''
                () => {{
                    const items = document.querySelectorAll('ytd-channel-renderer');
                    return Array.from(items).slice(0, {max_channels}).map(item => {{
                        const nameEl = item.querySelector('#text-container yt-formatted-string');
                        const linkEl = item.querySelector('#main-link');
                        const subsEl = item.querySelector('#subscribers');
                        return {{
                            name: nameEl ? nameEl.textContent.trim() : '',
                            url: linkEl ? linkEl.href : '',
                            subscribers: subsEl ? subsEl.textContent.trim() : ''
                        }};
                    }}).filter(c => c.url);
                }}
            ''')
            await page.close()

            results = []
            for ch in channels:
                try:
                    details = await self.get_channel_with_videos(ch['url'])
                    details['name'] = ch['name'] or details.get('name', '')
                    details['subscribers'] = ch['subscribers'] or details.get('subscribers', '')
                    details['scores'] = self.calculate_score(details)
                    details['keyword'] = keyword
                    results.append(details)
                except Exception as e:
                    ch['error'] = str(e)
                    ch['scores'] = {'total': 0}
                    ch['keyword'] = keyword
                    results.append(ch)

            return results
        except Exception as e:
            return [{'error': str(e), 'keyword': keyword}]

    def analyze_with_llm(self, channels: List[Dict], channel_name: str, field: str) -> Dict:
        """LLM으로 분석 및 선정"""
        summaries = []
        for i, ch in enumerate(channels[:10], 1):
            s = ch.get('scores', {})
            videos = [v.get('title', '')[:40] for v in ch.get('videos', [])[:3]]
            summaries.append(f"""{i}. {ch.get('name', '?')} ({ch.get('subscribers', '?')}) [키워드: {ch.get('keyword', '?')}]
   점수: {s.get('total', 0)}/100 (구독{s.get('subscriber',0)} 활동{s.get('activity',0)} 참여{s.get('engagement',0)} 성장{s.get('growth',0)})
   영상: {', '.join(videos)}""")

        prompt = f"""'{channel_name}' 채널의 '{field}' 분야 레퍼런스 채널을 선정해줘.

검색된 채널들:
{chr(10).join(summaries)}

요구사항:
1. 레퍼런스로 삼기 좋은 상위 5개 선정
2. 콘텐츠 스타일, 강점, 배울 점 분석
3. 채널별 특징과 차별점 설명

JSON 형식:
{{"top5": [{{"rank": 1, "name": "채널명", "reason": "선정 이유", "content_style": "콘텐츠 스타일", "key_learning": "배울 점", "differentiation": "차별점"}}], "overall_insight": "전체 인사이트", "content_strategy": "추천 콘텐츠 전략"}}"""

        try:
            resp = requests.post(LLM_URL, json={
                'model': 'gpt-oss-120b-longctx',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 2048
            }, timeout=120)

            if resp.status_code == 200:
                content = resp.json()['choices'][0]['message']['content']
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0]
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0]
                return json.loads(content.strip())
            return {'error': f'LLM {resp.status_code}'}
        except Exception as e:
            return {'error': str(e)}

    async def deep_research(self, channel_name: str, field: str, max_keywords: int = 5) -> Dict:
        """트렌드 기반 딥리서치 실행"""
        print(f'=== 트렌드 기반 YouTube 딥리서치 ===')
        print(f'채널: {channel_name} | 분야: {field}\n')

        # 1. 트렌드 키워드 생성
        print('1. 트렌드 키워드 생성 중...')
        keywords = self.generate_trending_keywords(channel_name, field, max_keywords)
        print(f'   생성된 키워드: {keywords}\n')

        # 2. 각 키워드로 채널 검색
        print('2. 채널 검색 및 스코어링...')
        all_channels = []
        for kw in keywords:
            print(f'   검색: {kw}')
            channels = await self.search_channels(kw, max_channels=5)
            all_channels.extend(channels)

        # 중복 제거 (URL 기준)
        seen_urls = set()
        unique_channels = []
        for ch in all_channels:
            url = ch.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_channels.append(ch)

        # 스코어 기준 정렬
        unique_channels.sort(key=lambda x: x.get('scores', {}).get('total', 0), reverse=True)

        print(f'\n   총 {len(unique_channels)}개 채널 발견\n')
        for ch in unique_channels[:10]:
            s = ch.get('scores', {})
            print(f"   {ch.get('name', '?')}: {s.get('total', 0)}점 ({ch.get('subscribers', 'N/A')})")

        # 3. LLM 분석
        print('\n3. LLM 분석 중...')
        analysis = self.analyze_with_llm(unique_channels[:10], channel_name, field)

        if 'top5' in analysis:
            print('\n=== 선정된 레퍼런스 채널 ===')
            for ch in analysis['top5']:
                print(f"\n{ch.get('rank')}위: {ch.get('name')}")
                print(f"   이유: {ch.get('reason')}")
                print(f"   스타일: {ch.get('content_style')}")
                print(f"   배울 점: {ch.get('key_learning')}")
            print(f"\n인사이트: {analysis.get('overall_insight', '')}")
            print(f"전략: {analysis.get('content_strategy', '')}")

        # 4. 상위 채널 자막 수집
        print('\n4. 상위 채널 영상 자막 수집...')
        for ch in unique_channels[:3]:
            videos = ch.get('videos', [])[:2]
            for v in videos:
                if v.get('url'):
                    print(f"   자막: {v.get('title', '')[:30]}...")
                    transcript = self.download_transcript(v['url'])
                    if transcript:
                        v['transcript'] = transcript[:2000]
                        print(f"      -> {len(transcript)} chars")

        # 5. 결과 저장
        result = {
            'channel_name': channel_name,
            'field': field,
            'keywords': keywords,
            'channels': unique_channels,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        }

        output = SCREENSHOT_DIR / f'trend_research_{channel_name.replace(" ", "_")}.json'
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f'\n저장: {output}')

        return result

    def generate_script_prompt(self, channel_name: str, video_idea: Dict) -> str:
        """대본 프롬프트 생성"""
        title = video_idea.get('title', '')
        hook = video_idea.get('hook', '')
        summary = video_idea.get('summary', '')

        # 아이디어 최적화 (제목 + 후킹 + 요약 결합)
        optimized_idea = f"{title}"
        if hook:
            optimized_idea += f"\n\n핵심 메시지: {hook}"
        if summary:
            optimized_idea += f"\n\n내용 방향: {summary}"

        prompt = f'''이 제목으로 {channel_name}의 독특한 금융 교육 스타일을 살려서 유튜브 대본을 써줘:
"{optimized_idea}"

대본은 {channel_name}이 쓰는 검증된 구조를 꼭 지켜야 해:

오프닝 훅: 시청자가 보자마자 "이거 내 얘긴데?"라고 생각할 만한 공감 가는 상황으로 시작해.

도입부: 이 문구를 꼭 넣어:
"내 이름은 {channel_name}야. 난 [관련 금융 주제]에 대해서 진짜 미친 듯이 고민하거든.
만약 네가 [시청자의 고민 묘사] 때문에 힘들다면, 구독 버튼 누르고 이 영상이 도움 되면 좋아요도 꼭 눌러줘."

💡 스타일 가이드
- 친구랑 말하듯이 자연스럽게 써. ("사실 말이야...", "자 봐봐", "음" 같은 표현 활용)
- 영상 초반에 사람들이 흔히 믿는 금융 상식을 깨부숴줘.
- 신뢰할 수 있는 출처의 놀라운 통계 수치를 넣어줘.
- 실제 금액을 써서 수학적으로 딱딱 계산되는 예시를 보여줘.
- 왜 그런 경제적 결정을 내리는지 심리적인 이유를 설명해줘.
- 시청자가 반박할 만한 내용에 미리 대답해줘. ("지금 이런 생각 들지?" 등)
- 어려운 개념은 쉬운 비유를 들어서 설명해.
- 뒤로 갈수록 더 놀라운 통찰력을 보여줘야 해.
- "사람들이 진짜 모르는 게 뭐냐면...", "여기서부터 진짜 재밌어진다..." 같은 표현을 써줘.

📋 콘텐츠 요구 사항
- 분량: 10~15분 정도 영상에 맞는 길이.
- 돈의 계산적인 부분과 심리적인 부분의 균형을 맞춰줘.
- 시청자가 바로 따라 할 수 있는 구체적인 단계를 알려줘.
- 중요한 포인트는 이야기 형식(스토리텔링)으로 풀어줘.
- 마지막엔 강력한 동기부여와 함께 구독/좋아요를 유도하며 끝내줘.

🎭 말투 (톤앤매너)
권위는 있지만 친근하게. 사람들이 자주 하는 실수에 대해 약간 답답해하면서도,
진심으로 시청자의 미래를 걱정해 주는 느낌을 유지해줘.'''

        return prompt

    def generate_video_ideas_with_prompts(self, channel_name: str, field: str, reference_channels: List[Dict], count: int = 20) -> Dict:
        """레퍼런스 채널 기반 영상 아이디어 + 대본 프롬프트 생성"""
        # 레퍼런스 채널 영상 제목들 수집
        ref_titles = []
        for ch in reference_channels[:5]:
            for v in ch.get('videos', [])[:3]:
                ref_titles.append(v.get('title', ''))

        prompt = f"""'{channel_name}' 채널의 '{field}' 분야 독창적인 영상 아이디어 {count}개를 만들어줘.

레퍼런스 채널 인기 영상:
{chr(10).join(['- ' + t for t in ref_titles if t])}

요구사항:
- 레퍼런스를 참고하되 차별화된 독창적인 아이디어
- 클릭을 유도하는 제목
- 강력한 후킹 문장
- 구체적인 내용 요약

JSON 형식:
{{"ideas": [{{"title": "제목", "hook": "후킹문장", "summary": "내용요약"}}]}}"""

        try:
            resp = requests.post(LLM_URL, json={
                'model': 'gpt-oss-120b-longctx',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 4096,
                'temperature': 0.8
            }, timeout=120)

            if resp.status_code == 200:
                content = resp.json()['choices'][0]['message']['content']
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0]
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0]

                ideas = json.loads(content.strip())

                # 각 아이디어에 대본 프롬프트 추가
                for idea in ideas.get('ideas', []):
                    idea['script_prompt'] = self.generate_script_prompt(channel_name, idea)

                return ideas
            return {'error': f'LLM {resp.status_code}'}
        except Exception as e:
            return {'error': str(e)}

    async def close(self):
        if self.browser:
            await self.browser.close()


async def main():
    import sys

    # 기본값 또는 인자로 받기
    channel_name = sys.argv[1] if len(sys.argv) > 1 else 'MoneyMindset'
    field = sys.argv[2] if len(sys.argv) > 2 else '재테크 투자'

    researcher = TrendYouTubeResearcher()

    try:
        # 1. 딥리서치 실행
        result = await researcher.deep_research(channel_name, field)
        print(f"\n완료! 총 {len(result.get('channels', []))}개 채널 분석")

        # 2. 영상 아이디어 + 대본 프롬프트 생성
        print('\n5. 영상 아이디어 + 대본 프롬프트 생성...')
        ideas_result = researcher.generate_video_ideas_with_prompts(
            channel_name, field, result.get('channels', []), count=20
        )

        if 'ideas' in ideas_result:
            print(f"\n=== {len(ideas_result['ideas'])}개 영상 아이디어 생성 ===")
            for i, idea in enumerate(ideas_result['ideas'][:5], 1):
                print(f"\n{i}. {idea.get('title', 'N/A')}")
                print(f"   Hook: {idea.get('hook', 'N/A')}")

            # 아이디어 저장
            ideas_output = SCREENSHOT_DIR / f'video_ideas_{channel_name.replace(" ", "_")}.json'
            with open(ideas_output, 'w', encoding='utf-8') as f:
                json.dump(ideas_result, f, ensure_ascii=False, indent=2)
            print(f'\n아이디어 저장: {ideas_output}')

            # 대본 프롬프트 샘플 출력
            if ideas_result['ideas']:
                print('\n=== 첫 번째 아이디어 대본 프롬프트 샘플 ===')
                print(ideas_result['ideas'][0].get('script_prompt', '')[:500] + '...')

    finally:
        await researcher.close()


if __name__ == '__main__':
    asyncio.run(main())
