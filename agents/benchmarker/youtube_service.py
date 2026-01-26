"""YouTube 데이터 수집 서비스 (yt-dlp 기반)"""

import asyncio
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import unquote

from .schemas import VideoMetadata, ChannelMetadata


class YouTubeService:
    """yt-dlp를 사용한 YouTube 데이터 수집"""
    
    def __init__(self):
        self.ytdlp_path = "yt-dlp"
    
    async def _run_ytdlp(self, args: List[str]) -> Tuple[str, str]:
        """yt-dlp 명령 실행"""
        cmd = [self.ytdlp_path] + args
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return stdout.decode("utf-8"), stderr.decode("utf-8")
    
    def _normalize_channel_url(self, url: str) -> str:
        """채널 URL 정규화 - /videos suffix 추가, URL 디코딩"""
        url = unquote(url)  # URL 디코딩 (%EC%9C%A0... -> 유...)
        
        # /videos suffix 추가
        if not url.endswith("/videos"):
            url = url.rstrip("/") + "/videos"
        
        return url
    
    def _extract_channel_id(self, url: str) -> Optional[str]:
        """URL에서 채널 ID 추출"""
        url = unquote(url)
        patterns = [
            r"youtube\.com/channel/([^/?]+)",
            r"youtube\.com/@([^/?]+)",
            r"youtube\.com/c/([^/?]+)",
            r"youtube\.com/user/([^/?]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """URL에서 비디오 ID 추출"""
        patterns = [
            r"youtube\.com/watch\?v=([^&]+)",
            r"youtu\.be/([^?]+)",
            r"youtube\.com/shorts/([^?]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def is_channel_url(self, url: str) -> bool:
        """채널 URL인지 확인"""
        url = unquote(url)
        return bool(re.search(r"youtube\.com/(channel/|@|c/|user/)", url))
    
    def is_video_url(self, url: str) -> bool:
        """비디오 URL인지 확인"""
        return bool(re.search(r"(youtube\.com/watch|youtu\.be/|youtube\.com/shorts/)", url))
    
    async def get_channel_info(self, channel_url: str) -> Optional[ChannelMetadata]:
        """채널 정보 가져오기"""
        url = self._normalize_channel_url(channel_url)

        # 첫 번째 영상에서 채널 정보 추출 (--flat-playlist 없이 해야 channel_follower_count 포함)
        args = [
            "--dump-json",
            "--playlist-items", "1",
            url
        ]

        try:
            stdout, stderr = await self._run_ytdlp(args)
            if not stdout.strip():
                print(f"No output for channel: {url}, stderr: {stderr}")
                return None

            data = json.loads(stdout.strip().split("\n")[0])

            # 영상 수는 별도로 가져오기 (flat-playlist로 빠르게 카운트)
            video_count = 0
            try:
                count_args = ["--flat-playlist", "--dump-json", "--playlist-items", "1:100", url]
                count_stdout, _ = await self._run_ytdlp(count_args)
                if count_stdout.strip():
                    video_count = len(count_stdout.strip().split("\n"))
            except:
                pass

            # 채널 정보 추출
            return ChannelMetadata(
                channel_id=data.get("channel_id") or data.get("uploader_id", ""),
                channel_name=data.get("channel") or data.get("uploader", ""),
                subscriber_count=data.get("channel_follower_count", 0) or 0,
                video_count=video_count,
                description=data.get("channel_description") or f"최근 영상: {data.get('title', '')}",
                thumbnail_url=data.get("thumbnail", ""),
                banner_url=data.get("channel_banner_url"),
            )
        except Exception as e:
            print(f"Failed to get channel info: {e}")
            return None
    
    async def get_channel_videos(
        self, 
        channel_url: str, 
        max_videos: int = 20
    ) -> List[VideoMetadata]:
        """채널의 최근 영상 목록 가져오기"""
        url = self._normalize_channel_url(channel_url)
        
        args = [
            "--dump-json",
            "--flat-playlist",
            "--playlist-items", f"1:{max_videos}",
            url
        ]
        
        try:
            stdout, _ = await self._run_ytdlp(args)
            if not stdout.strip():
                return []
            
            videos = []
            for line in stdout.strip().split("\n"):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    video = VideoMetadata(
                        video_id=data.get("id", ""),
                        title=data.get("title", ""),
                        description=data.get("description", ""),
                        view_count=data.get("view_count", 0) or 0,
                        like_count=data.get("like_count", 0) or 0,
                        comment_count=data.get("comment_count", 0) or 0,
                        duration=data.get("duration", 0) or 0,
                        upload_date=data.get("upload_date", ""),
                        thumbnail_url=self._get_best_thumbnail(data.get("thumbnails", [])),
                        tags=data.get("tags", []) or [],
                    )
                    videos.append(video)
                except json.JSONDecodeError:
                    continue
            
            return videos
        except Exception as e:
            print(f"Failed to get channel videos: {e}")
            return []
    
    def _get_best_thumbnail(self, thumbnails: List[Dict]) -> str:
        """가장 좋은 썸네일 URL 선택"""
        if not thumbnails:
            return ""
        
        # 가장 큰 해상도 선택
        best = max(thumbnails, key=lambda t: t.get("height", 0) * t.get("width", 0), default=None)
        return best.get("url", "") if best else ""
    
    async def get_video_info(self, video_url: str) -> Optional[VideoMetadata]:
        """단일 영상 상세 정보 가져오기"""
        args = [
            "--dump-json",
            "--no-playlist",
            video_url
        ]
        
        try:
            stdout, _ = await self._run_ytdlp(args)
            if not stdout.strip():
                return None
            
            data = json.loads(stdout.strip())
            
            return VideoMetadata(
                video_id=data.get("id", ""),
                title=data.get("title", ""),
                description=data.get("description", ""),
                view_count=data.get("view_count", 0) or 0,
                like_count=data.get("like_count", 0) or 0,
                comment_count=data.get("comment_count", 0) or 0,
                duration=data.get("duration", 0) or 0,
                upload_date=data.get("upload_date", ""),
                thumbnail_url=data.get("thumbnail", ""),
                tags=data.get("tags", []) or [],
            )
        except Exception as e:
            print(f"Failed to get video info: {e}")
            return None
    
    async def get_video_transcript(
        self, 
        video_url: str,
        lang_priority: List[str] = None
    ) -> Optional[str]:
        """영상 자막/transcript 가져오기"""
        if lang_priority is None:
            lang_priority = ["ko", "en", "en-US", "ko-KR"]
        
        lang_str = ",".join(lang_priority)
        
        args = [
            "--write-sub",
            "--write-auto-sub",
            "--sub-lang", lang_str,
            "--skip-download",
            "--sub-format", "vtt",
            "-o", "/tmp/yt_sub_%(id)s",
            video_url
        ]
        
        try:
            video_id = self._extract_video_id(video_url)
            if not video_id:
                return None
            
            await self._run_ytdlp(args)
            
            import os
            for lang in lang_priority:
                sub_path = f"/tmp/yt_sub_{video_id}.{lang}.vtt"
                if os.path.exists(sub_path):
                    with open(sub_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    os.remove(sub_path)
                    return self._parse_vtt(content)
            
            for lang in lang_priority:
                for suffix in ["", "-orig"]:
                    sub_path = f"/tmp/yt_sub_{video_id}.{lang}{suffix}.vtt"
                    if os.path.exists(sub_path):
                        with open(sub_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        os.remove(sub_path)
                        return self._parse_vtt(content)
            
            return None
        except Exception as e:
            print(f"Failed to get transcript: {e}")
            return None
    
    def _parse_vtt(self, vtt_content: str) -> str:
        """VTT 자막을 텍스트로 변환"""
        lines = []
        for line in vtt_content.split("\n"):
            if "-->" in line:
                continue
            if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
                continue
            if not line.strip():
                continue
            clean_line = re.sub(r"<[^>]+>", "", line)
            if clean_line.strip():
                lines.append(clean_line.strip())
        
        seen = set()
        unique_lines = []
        for line in lines:
            if line not in seen:
                seen.add(line)
                unique_lines.append(line)
        
        return " ".join(unique_lines)
    
    async def get_thumbnails(
        self, 
        videos: List[VideoMetadata],
        max_thumbnails: int = 10
    ) -> List[str]:
        """영상 목록에서 썸네일 URL 추출"""
        thumbnails = []
        for video in videos[:max_thumbnails]:
            if video.thumbnail_url:
                thumbnails.append(video.thumbnail_url)
        return thumbnails
    
    async def download_thumbnail(self, url: str) -> Optional[bytes]:
        """썸네일 이미지 다운로드"""
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0)
                if response.status_code == 200:
                    return response.content
        except Exception as e:
            print(f"Failed to download thumbnail: {e}")
        return None


# 싱글톤 인스턴스
youtube_service = YouTubeService()
