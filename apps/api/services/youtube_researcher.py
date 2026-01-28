"""
YouTube 채널 딥리서치 서비스
구독자, 성장세, 최근 활동 기반 스코어링 + 자막 분석
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

SCREENSHOT_DIR = Path("/app/screenshots/youtube")
LLM_URL = "http://localhost:8017/v1/chat/completions"


class YouTubeResearchService:
    def __init__(self):
        self.browser = None
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    
    async def _ensure_browser(self):
        if self.browser is None:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
        return self.browser
    
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
            # 비디오 ID 추출
            video_id = None
            if 'v=' in video_url:
                video_id = video_url.split('v=')[1].split('&')[0]
            elif 'youtu.be/' in video_url:
                video_id = video_url.split('youtu.be/')[1].split('?')[0]
            
            if not video_id:
                return None
            
            output_path = SCREENSHOT_DIR / f"transcript_{video_id}"
            
            # yt-dlp로 자막 다운로드
            cmd = [
                'yt-dlp',
                '--skip-download',
                '--write-auto-sub',
                '--sub-lang', 'ko,en',
                '--sub-format', 'vtt',
                '-o', str(output_path),
                f'https://www.youtube.com/watch?v={video_id}'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # 자막 파일 읽기
            for ext in ['.ko.vtt', '.en.vtt', '.vtt']:
                vtt_path = Path(str(output_path) + ext)
                if vtt_path.exists():
                    content = vtt_path.read_text(encoding='utf-8')
                    # VTT 포맷 정리 (타임스탬프 제거)
                    lines = []
                    for line in content.split('\n'):
                        if not re.match(r'^\d{2}:\d{2}', line) and not line.startswith('WEBVTT') and line.strip():
                            lines.append(line.strip())
                    return ' '.join(lines)[:5000]  # 최대 5000자
            
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
    
    async def research_channels(self, keyword: str, max_channels: int = 8) -> List[Dict]:
        """채널 검색 및 스코어링"""
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
                    results.append(details)
                except Exception as e:
                    ch['error'] = str(e)
                    ch['scores'] = {'total': 0}
                    results.append(ch)
            
            results.sort(key=lambda x: x.get('scores', {}).get('total', 0), reverse=True)
            return results
        except Exception as e:
            return [{'error': str(e)}]
    
    def analyze_with_llm(self, channels: List[Dict], keyword: str) -> Dict:
        """LLM으로 분석 및 선정"""
        summaries = []
        for i, ch in enumerate(channels[:8], 1):
            s = ch.get('scores', {})
            videos = [v.get('title', '')[:40] for v in ch.get('videos', [])[:3]]
            summaries.append(f"""{i}. {ch.get('name', '?')} ({ch.get('subscribers', '?')})
   점수: {s.get('total', 0)}/100 (구독{s.get('subscriber',0)} 활동{s.get('activity',0)} 참여{s.get('engagement',0)} 성장{s.get('growth',0)})
   영상: {', '.join(videos)}""")
        
        prompt = f"""'{keyword}' 검색 결과 채널들입니다. 레퍼런스로 삼기 좋은 상위 5개를 선정하고 분석해줘.

{chr(10).join(summaries)}

JSON으로 응답:
{{"top5": [{{"rank": 1, "name": "채널명", "reason": "선정 이유", "content_style": "콘텐츠 스타일", "key_learning": "배울 점"}}], "summary": "전체 요약"}}"""

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
    
    async def close(self):
        if self.browser:
            await self.browser.close()


async def main():
    import sys
    keyword = sys.argv[1] if len(sys.argv) > 1 else '재테크'
    
    service = YouTubeResearchService()
    
    print(f'=== YouTube 채널 딥리서치: {keyword} ===\n')
    print('1. 채널 검색 및 스코어링...')
    
    channels = await service.research_channels(keyword, max_channels=8)
    
    print(f'\n스코어링 결과 ({len(channels)}개):')
    for ch in channels:
        s = ch.get('scores', {})
        print(f"  {ch.get('name', '?')}: {s.get('total', 0)}점 ({ch.get('subscribers', 'N/A')})")
    
    print('\n2. LLM 분석...')
    analysis = service.analyze_with_llm(channels, keyword)
    
    if 'top5' in analysis:
        print('\n=== 선정된 레퍼런스 채널 ===')
        for ch in analysis['top5']:
            print(f"\n{ch.get('rank')}위: {ch.get('name')}")
            print(f"   이유: {ch.get('reason')}")
            print(f"   스타일: {ch.get('content_style')}")
            print(f"   배울 점: {ch.get('key_learning')}")
        print(f"\n요약: {analysis.get('summary', '')}")
    
    # 상위 채널 자막 다운로드
    print('\n3. 상위 채널 영상 자막 수집...')
    for ch in channels[:3]:
        videos = ch.get('videos', [])[:2]
        for v in videos:
            if v.get('url'):
                print(f"  자막 다운로드: {v.get('title', '')[:30]}...")
                transcript = service.download_transcript(v['url'])
                if transcript:
                    v['transcript'] = transcript[:2000]
                    print(f"    -> {len(transcript)} chars")
    
    # 결과 저장
    result = {'keyword': keyword, 'channels': channels, 'analysis': analysis, 'timestamp': datetime.now().isoformat()}
    output = SCREENSHOT_DIR / 'channel_research.json'
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'\n저장: {output}')
    
    await service.close()


if __name__ == '__main__':
    asyncio.run(main())
