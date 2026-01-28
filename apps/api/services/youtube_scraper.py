"""
YouTube 채널 스크린샷 서비스
Playwright를 사용하여 유튜브 채널의 영상 목록 스크린샷 캡처
"""
import asyncio
import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Playwright는 async로 동작
try:
    from playwright.async_api import async_playwright, Browser, Page
except ImportError:
    print("Warning: playwright not installed. Run: pip install playwright && playwright install chromium")

SCREENSHOT_DIR = Path("/app/screenshots/youtube")


class YouTubeScraperService:
    """YouTube 채널 스크린샷 서비스"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    
    async def _ensure_browser(self):
        """브라우저 인스턴스 확인"""
        if self.browser is None:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
        return self.browser
    
    async def search_channels(self, keyword: str, max_channels: int = 5) -> List[Dict]:
        """
        키워드로 YouTube 채널 검색
        
        Args:
            keyword: 검색 키워드
            max_channels: 최대 채널 수
            
        Returns:
            채널 정보 리스트
        """
        browser = await self._ensure_browser()
        page = await browser.new_page()
        
        try:
            # YouTube 검색 (채널 필터)
            search_url = f"https://www.youtube.com/results?search_query={keyword}&sp=EgIQAg%253D%253D"
            await page.goto(search_url, wait_until="networkidle", timeout=30000)
            
            # 쿠키 동의 팝업 처리 (있는 경우)
            try:
                await page.click('button[aria-label*="Accept"]', timeout=3000)
            except:
                pass
            
            await asyncio.sleep(2)  # 로딩 대기
            
            # 채널 정보 추출
            channels = await page.evaluate(f'''
                () => {{
                    const items = document.querySelectorAll('ytd-channel-renderer');
                    const results = [];
                    for (let i = 0; i < Math.min(items.length, {max_channels}); i++) {{
                        const item = items[i];
                        const titleEl = item.querySelector('#text-container yt-formatted-string');
                        const linkEl = item.querySelector('#main-link');
                        const subsEl = item.querySelector('#subscribers');
                        
                        if (titleEl && linkEl) {{
                            results.push({{
                                name: titleEl.textContent.trim(),
                                url: linkEl.href,
                                subscribers: subsEl ? subsEl.textContent.trim() : 'N/A',
                                channel_id: linkEl.href.split('/').pop()
                            }});
                        }}
                    }}
                    return results;
                }}
            ''')
            
            return channels
            
        finally:
            await page.close()
    
    async def capture_channel_videos(
        self, 
        channel_url: str,
        channel_name: str = "channel",
        scroll_count: int = 2
    ) -> Dict:
        """
        채널의 영상 목록 스크린샷 캡처
        
        Args:
            channel_url: 채널 URL
            channel_name: 채널명 (파일명용)
            scroll_count: 스크롤 횟수
            
        Returns:
            스크린샷 정보
        """
        browser = await self._ensure_browser()
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            # 채널 동영상 탭으로 이동
            videos_url = channel_url.rstrip('/') + '/videos'
            await page.goto(videos_url, wait_until="networkidle", timeout=30000)
            
            # 쿠키 동의 처리
            try:
                await page.click('button[aria-label*="Accept"]', timeout=3000)
            except:
                pass
            
            await asyncio.sleep(2)
            
            # 스크롤해서 더 많은 영상 로드
            for _ in range(scroll_count):
                await page.evaluate('window.scrollBy(0, 800)')
                await asyncio.sleep(1)
            
            # 전체 페이지 스크린샷
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_name = ''.join(c for c in channel_name if c.isalnum() or c in '_ -')[:30]
            screenshot_path = SCREENSHOT_DIR / f"{safe_name}_{timestamp}.png"
            
            await page.screenshot(path=str(screenshot_path), full_page=False)
            
            # 영상 제목 추출
            video_titles = await page.evaluate('''
                () => {
                    const videos = document.querySelectorAll('#video-title');
                    return Array.from(videos).slice(0, 20).map(v => v.textContent.trim());
                }
            ''')
            
            # Base64로 인코딩
            with open(screenshot_path, 'rb') as f:
                screenshot_b64 = base64.b64encode(f.read()).decode()
            
            return {
                'channel_name': channel_name,
                'channel_url': channel_url,
                'screenshot_path': str(screenshot_path),
                'screenshot_b64': screenshot_b64,
                'video_titles': video_titles,
                'captured_at': timestamp
            }
            
        finally:
            await page.close()
    
    async def search_and_capture(
        self,
        keyword: str,
        max_channels: int = 3,
        scroll_count: int = 2
    ) -> Dict:
        """
        키워드로 채널 검색 후 각 채널의 영상 목록 스크린샷 캡처
        
        Args:
            keyword: 검색 키워드
            max_channels: 최대 채널 수
            scroll_count: 각 채널당 스크롤 횟수
            
        Returns:
            전체 결과
        """
        # 채널 검색
        channels = await self.search_channels(keyword, max_channels)
        
        if not channels:
            return {
                'keyword': keyword,
                'channels': [],
                'error': 'No channels found'
            }
        
        # 각 채널 스크린샷 캡처
        results = []
        for channel in channels:
            try:
                capture = await self.capture_channel_videos(
                    channel['url'],
                    channel['name'],
                    scroll_count
                )
                capture['subscribers'] = channel.get('subscribers', 'N/A')
                results.append(capture)
            except Exception as e:
                results.append({
                    'channel_name': channel['name'],
                    'channel_url': channel['url'],
                    'error': str(e)
                })
        
        return {
            'keyword': keyword,
            'channels': results,
            'total_captured': len([r for r in results if 'screenshot_path' in r])
        }
    
    async def close(self):
        """브라우저 종료"""
        if self.browser:
            await self.browser.close()
            self.browser = None


# 싱글톤 인스턴스
youtube_scraper = YouTubeScraperService()


# 테스트용 CLI
if __name__ == '__main__':
    import sys
    
    async def main():
        keyword = sys.argv[1] if len(sys.argv) > 1 else '재테크'
        print(f"Searching for: {keyword}")
        
        result = await youtube_scraper.search_and_capture(keyword, max_channels=3)
        
        print(f"\nFound {result['total_captured']} channels:")
        for ch in result['channels']:
            print(f"  - {ch.get('channel_name', 'Unknown')}")
            if 'video_titles' in ch:
                print(f"    Top videos: {ch['video_titles'][:3]}")
            if 'screenshot_path' in ch:
                print(f"    Screenshot: {ch['screenshot_path']}")
        
        await youtube_scraper.close()
    
    asyncio.run(main())
