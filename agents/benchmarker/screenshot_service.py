"""Playwright 기반 YouTube 채널 스크린샷 서비스"""

import asyncio
import base64
import os
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ChannelScreenshot:
    """채널 스크린샷 결과"""
    channel_url: str
    channel_name: str
    # 스크린샷 (base64)
    videos_page: Optional[str] = None  # /videos 페이지 (썸네일 그리드)
    channel_page: Optional[str] = None  # 메인 채널 페이지
    about_page: Optional[str] = None  # /about 페이지
    # 개별 썸네일 스크린샷들
    thumbnail_screenshots: List[str] = None
    
    def __post_init__(self):
        if self.thumbnail_screenshots is None:
            self.thumbnail_screenshots = []


class ScreenshotService:
    """Playwright를 사용한 YouTube 스크린샷 서비스"""
    
    def __init__(self):
        self.browser = None
        self.playwright = None
    
    async def _ensure_browser(self):
        """브라우저 초기화"""
        if self.browser is None:
            from playwright.async_api import async_playwright
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
    
    async def close(self):
        """브라우저 종료"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
    
    def _normalize_channel_url(self, url: str) -> str:
        """채널 URL 정규화"""
        if not url.startswith('http'):
            url = 'https://' + url
        # www 추가
        if 'youtube.com' in url and 'www.' not in url:
            url = url.replace('youtube.com', 'www.youtube.com')
        return url
    
    def _get_videos_url(self, channel_url: str) -> str:
        """채널 URL에서 /videos 페이지 URL 생성"""
        channel_url = self._normalize_channel_url(channel_url)
        # 이미 /videos가 있으면 그대로
        if '/videos' in channel_url:
            return channel_url
        # 끝에 슬래시 제거 후 /videos 추가
        return channel_url.rstrip('/') + '/videos'
    
    async def capture_channel(
        self, 
        channel_url: str,
        capture_individual_thumbnails: bool = True,
        max_thumbnails: int = 6,
        scroll_count: int = 2
    ) -> ChannelScreenshot:
        """채널 페이지 스크린샷 캡처"""
        await self._ensure_browser()
        
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='ko-KR',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        result = ChannelScreenshot(
            channel_url=channel_url,
            channel_name=""
        )
        
        try:
            # 1. /videos 페이지 캡처 (썸네일 그리드)
            videos_url = self._get_videos_url(channel_url)
            await page.goto(videos_url, wait_until='networkidle', timeout=30000)
            
            # 쿠키 동의 팝업 처리
            try:
                accept_btn = page.locator('button:has-text("Accept all"), button:has-text("모두 동의")')
                if await accept_btn.count() > 0:
                    await accept_btn.first.click()
                    await page.wait_for_timeout(1000)
            except:
                pass
            
            # 채널명 추출
            try:
                channel_name_el = page.locator('yt-formatted-string#text.ytd-channel-name')
                if await channel_name_el.count() > 0:
                    result.channel_name = await channel_name_el.first.text_content()
            except:
                pass
            
            # 스크롤하여 더 많은 썸네일 로드
            for _ in range(scroll_count):
                await page.evaluate('window.scrollBy(0, 800)')
                await page.wait_for_timeout(1000)
            
            # 맨 위로 스크롤
            await page.evaluate('window.scrollTo(0, 0)')
            await page.wait_for_timeout(500)
            
            # /videos 페이지 전체 스크린샷
            screenshot_bytes = await page.screenshot(full_page=False)
            result.videos_page = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            # 2. 개별 썸네일 캡처
            if capture_individual_thumbnails:
                result.thumbnail_screenshots = await self._capture_thumbnails(
                    page, max_thumbnails
                )
            
            # 3. 메인 채널 페이지 캡처 (선택적)
            main_url = self._normalize_channel_url(channel_url).split('/videos')[0].split('/about')[0]
            if main_url != videos_url.replace('/videos', ''):
                await page.goto(main_url, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(1000)
                screenshot_bytes = await page.screenshot(full_page=False)
                result.channel_page = base64.b64encode(screenshot_bytes).decode('utf-8')
            
        except Exception as e:
            print(f"Screenshot capture failed: {e}")
        finally:
            await context.close()
        
        return result
    
    async def _capture_thumbnails(
        self, 
        page, 
        max_thumbnails: int = 6
    ) -> List[str]:
        """개별 썸네일 영역 캡처"""
        thumbnails = []
        
        try:
            # 썸네일 요소 찾기 (여러 선택자 시도)
            selectors = [
                'ytd-rich-item-renderer ytd-thumbnail',
                'ytd-grid-video-renderer ytd-thumbnail',
                'ytd-video-renderer ytd-thumbnail',
            ]
            
            thumbnail_elements = None
            for selector in selectors:
                elements = page.locator(selector)
                count = await elements.count()
                if count > 0:
                    thumbnail_elements = elements
                    break
            
            if thumbnail_elements is None:
                return thumbnails
            
            count = min(await thumbnail_elements.count(), max_thumbnails)
            
            for i in range(count):
                try:
                    element = thumbnail_elements.nth(i)
                    # 요소가 보이는지 확인
                    if await element.is_visible():
                        # 요소로 스크롤
                        await element.scroll_into_view_if_needed()
                        await page.wait_for_timeout(300)
                        
                        # 요소 스크린샷
                        screenshot_bytes = await element.screenshot()
                        thumbnails.append(
                            base64.b64encode(screenshot_bytes).decode('utf-8')
                        )
                except Exception as e:
                    print(f"Thumbnail {i} capture failed: {e}")
                    continue
            
        except Exception as e:
            print(f"Thumbnail capture failed: {e}")
        
        return thumbnails
    
    async def capture_multiple_channels(
        self,
        channel_urls: List[str],
        **kwargs
    ) -> List[ChannelScreenshot]:
        """여러 채널 스크린샷 캡처"""
        results = []
        for url in channel_urls:
            result = await self.capture_channel(url, **kwargs)
            results.append(result)
        return results


# 싱글톤 인스턴스
screenshot_service = ScreenshotService()
