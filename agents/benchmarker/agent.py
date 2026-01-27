"""벤치마킹 에이전트 - YouTube 채널 분석 및 복제 가이드 생성"""

import sys
import json
import re
import base64
from typing import Dict, Any, List, Optional

sys.path.append("/data/routine/routine-studio-v2")

from agents.base import BaseAgent, AgentResult, AgentStatus
from apps.api.services.llm import llm_service
from apps.api.services.vision import vision_service

from .schemas import (
    BenchmarkPhase,
    VideoMetadata,
    ChannelMetadata,
    ThumbnailPattern,
    ScriptPattern,
    ContentStrategy,
    AudienceProfile,
    BenchmarkReport,
)
from .youtube_service import youtube_service
from .prompts import (
    REPLICATION_CHANNEL_SETUP_PROMPT,
    REPLICATION_CONTENT_PLANNING_PROMPT,
    REPLICATION_THUMBNAIL_GUIDE_PROMPT,
    REPLICATION_SCRIPT_TEMPLATE_PROMPT,
    REPLICATION_ENGAGEMENT_PROMPT,
    REPLICATION_FIRST_VIDEOS_PROMPT,
    THUMBNAIL_ANALYSIS_PROMPT,
    SCRIPT_ANALYSIS_PROMPT,
    CONTENT_STRATEGY_PROMPT,
    AUDIENCE_PROFILE_PROMPT,
    CHANNEL_CONCEPT_PROMPT,
    REPLICATION_GUIDE_PROMPT,
    THUMBNAIL_GRID_ANALYSIS_PROMPT,
    INDIVIDUAL_THUMBNAIL_ANALYSIS_PROMPT,
)
from .screenshot_service import screenshot_service, ChannelScreenshot
from .cache_service import find_benchmark, save_benchmark, get_cache_summary, delete_benchmark

def emit_progress(status: str, detail: str = ""):
    """진행 상황 발생"""
    try:
        import builtins
        if hasattr(builtins, "emit_agent_progress"):
            builtins.emit_agent_progress(status, detail)
    except:
        pass


class BenchmarkerAgent(BaseAgent):
    """YouTube 채널 벤치마킹 에이전트"""

    MAX_VIDEOS_PER_CHANNEL = 20
    MAX_TRANSCRIPTS = 5
    MAX_THUMBNAILS_FOR_ANALYSIS = 8

    def __init__(self):
        super().__init__("BenchmarkerAgent")
        self.phase = BenchmarkPhase.ASK
        self.channel_urls: List[str] = []
        self.channels_data: List[Dict[str, Any]] = []
        self.report: Optional[BenchmarkReport] = None
        self.channel_screenshots: List[ChannelScreenshot] = []
        self.pending_url: Optional[str] = None
        self.pending_channel_info: Optional[ChannelMetadata] = None
        self.cached_report: Optional[Dict[str, Any]] = None
        self.use_cached: bool = False
        self.cached_report_shown: bool = False  # 캐시 리포트를 보여줬는지 여부

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """에이전트 실행 시작 - 초기 질문"""
        self.status = AgentStatus.RUNNING
        self.phase = BenchmarkPhase.ASK

        message = (
            "**벤치마킹할 유튜브 채널이 있나요?**\n\n"
            "분석하고 싶은 채널의 URL을 입력해주세요.\n"
            "- 채널 URL: youtube.com/@채널명 또는 youtube.com/channel/...\n"
            "- 여러 채널을 분석하려면 하나씩 입력 후 \"추가\"\n"
            "- 채널 분석이 필요 없으면 \"없어\" 또는 \"스킵\""
        )

        self.status = AgentStatus.WAITING_FEEDBACK

        return AgentResult(
            success=True,
            step="benchmark_ask",
            message=message,
            needs_feedback=True,
            data={"phase": self.phase.value}
        )

    async def handle_feedback(self, feedback: str, images: List[str] = None) -> AgentResult:
        """피드백 처리 - 페이즈별 분기"""
        feedback_lower = feedback.lower().strip()

        # 스킵 처리
        if self._is_skip_command(feedback_lower):
            self.status = AgentStatus.COMPLETED
            return AgentResult(
                success=True,
                step="benchmark_skipped",
                message="벤치마킹을 건너뛰었습니다.",
                needs_feedback=False,
                data={"skipped": True}
            )

        # 페이즈별 처리
        if self.phase == BenchmarkPhase.ASK:
            return await self._handle_ask_phase(feedback)
        elif self.phase == BenchmarkPhase.CONFIRM:
            return await self._handle_confirm_phase(feedback)
        elif self.phase == BenchmarkPhase.COLLECT:
            return await self._handle_collect_phase(feedback)
        elif self.phase == BenchmarkPhase.ANALYZE:
            return await self._handle_analyze_phase(feedback)
        elif self.phase == BenchmarkPhase.REPORT:
            return await self._handle_report_phase(feedback)

        return AgentResult(
            success=False,
            step="error",
            message="알 수 없는 상태입니다.",
            needs_feedback=True
        )

    def _is_skip_command(self, feedback: str) -> bool:
        """스킵 명령어인지 확인"""
        skip_keywords = ["없어", "스킵", "skip", "패스", "pass", "넘어가", "건너뛰"]
        return any(kw in feedback for kw in skip_keywords)

    def _extract_youtube_url(self, text: str) -> Optional[str]:
        """텍스트에서 YouTube URL 추출"""
        patterns = [
            r'(https?://)?(?:www\.)?youtube\.com/@[^\s]+',
            r'(https?://)?(?:www\.)?youtube\.com/channel/[^\s]+',
            r'(https?://)?(?:www\.)?youtube\.com/c/[^\s]+',
            r'(https?://)?(?:www\.)?youtube\.com/user/[^\s]+',
            r'(https?://)?(?:www\.)?youtube\.com/watch\?v=[^\s]+',
            r'(https?://)?youtu\.be/[^\s]+',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                url = match.group(0)
                if not url.startswith('http'):
                    url = 'https://' + url
                return url
        return None

    async def _handle_ask_phase(self, feedback: str) -> AgentResult:
        """ASK 페이즈 처리 - 첫 URL 입력 및 채널 정보 확인"""
        url = self._extract_youtube_url(feedback)

        if url:
            # 캐시된 벤치마크 확인
            emit_progress("캐시 확인 중", url[:50])
            cached = find_benchmark(url)
            
            if cached:
                self.cached_report = cached
                self.pending_url = url
                self.phase = BenchmarkPhase.CONFIRM
                self.use_cached = True
                
                summary = get_cache_summary(cached)
                
                self.status = AgentStatus.WAITING_FEEDBACK
                return AgentResult(
                    success=True,
                    step="benchmark_cached",
                    message=summary,
                    needs_feedback=True,
                    data={
                        "phase": "cached",
                        "cached": True,
                        "report": cached.get("report", {})
                    }
                )
            
            # 캐시 없으면 채널 정보 가져오기
            emit_progress("채널 확인 중", url[:50])

            try:
                channel_info = await youtube_service.get_channel_info(url)

                if channel_info:
                    self.pending_url = url
                    self.pending_channel_info = channel_info
                    self.phase = BenchmarkPhase.CONFIRM

                    # 채널 정보 표시
                    subs = f"{channel_info.subscriber_count:,}" if channel_info.subscriber_count else "비공개"
                    videos = f"{channel_info.video_count:,}" if channel_info.video_count else "알 수 없음"
                    desc = channel_info.description[:150] + "..." if channel_info.description and len(channel_info.description) > 150 else (channel_info.description or "설명 없음")

                    message = (
                        f"**{channel_info.channel_name}**\n\n"
                        f"구독자: **{subs}명**\n\n"
                        f"영상 수: **{videos}개**\n\n"
                        f"설명: {desc}\n\n"
                        "이 채널이 맞나요?\n"
                        "- 맞으면 **확인** 또는 **맞아**\n"
                        "- 다른 채널이면 URL을 다시 입력해주세요"
                    )

                    self.status = AgentStatus.WAITING_FEEDBACK
                    return AgentResult(
                        success=True,
                        step="benchmark_confirm",
                        message=message,
                        needs_feedback=True,
                        data={
                            "phase": self.phase.value,
                            "channel_preview": {
                                "url": url,
                                "name": channel_info.channel_name,
                                "subscribers": channel_info.subscriber_count,
                                "videos": channel_info.video_count
                            }
                        }
                    )
                else:
                    return AgentResult(
                        success=True,
                        step="benchmark_ask",
                        message=f"채널 정보를 가져올 수 없습니다.\nURL을 확인해주세요: {url}\n\n다른 URL을 입력하거나 \"스킵\"을 입력하세요.",
                        needs_feedback=True,
                        data={"phase": self.phase.value}
                    )
            except Exception as e:
                print(f"Channel info fetch failed: {e}")
                return AgentResult(
                    success=True,
                    step="benchmark_ask",
                    message=f"채널 정보를 가져오는 중 오류가 발생했습니다.\n다른 URL을 입력하거나 \"스킵\"을 입력하세요.",
                    needs_feedback=True,
                    data={"phase": self.phase.value, "error": str(e)}
                )

        return AgentResult(
            success=True,
            step="benchmark_ask",
            message="YouTube 채널 URL을 입력해주세요.\n예: youtube.com/@채널명",
            needs_feedback=True,
            data={"phase": self.phase.value}
        )

    async def _handle_confirm_phase(self, feedback: str) -> AgentResult:
        """CONFIRM 페이즈 처리 - 채널 확인"""
        feedback_lower = feedback.lower().strip()

        # 다시 분석 요청 (캐시된 결과가 있을 때)
        reanalyze_keywords = ["다시 분석", "다시분석", "재분석", "업데이트", "새로 분석", "update", "refresh"]
        if self.use_cached and any(kw in feedback_lower for kw in reanalyze_keywords):
            # 캐시 삭제
            if self.pending_url:
                delete_benchmark(self.pending_url)
            
            # 상태 초기화
            self.use_cached = False
            self.cached_report = None
            url = self.pending_url
            self.pending_url = None
            self.pending_channel_info = None
            self.phase = BenchmarkPhase.ASK
            
            # 다시 ASK 페이즈로 (캐시 없이)
            return await self._handle_ask_phase(url)

        # 확인 명령
        confirm_keywords = ["확인", "맞아", "맞음", "네", "응", "yes", "ok", "ㅇㅇ", "추가", "맞습니다", "ㅇ", "다음"]
        if any(kw in feedback_lower for kw in confirm_keywords):
            # 캐시된 결과가 있는 경우
            if self.use_cached and self.cached_report:
                # 이미 리포트를 보여줬으면 완료 처리
                if self.cached_report_shown:
                    self.status = AgentStatus.COMPLETED
                    return AgentResult(
                        success=True,
                        step="benchmark_complete",
                        message="벤치마크 리포트 확인 완료! 다음 단계로 진행합니다.",
                        needs_feedback=False,
                        data={
                            "report": self.report.to_dict() if self.report else {},
                            "phase": BenchmarkPhase.REPORT.value,
                            "cached": True
                        }
                    )

                # 캐시된 리포트를 처음 보여주는 경우
                channel_name = self.pending_channel_info.channel_name if self.pending_channel_info else self.pending_url
                emit_progress("캐시 사용", f"기존 분석 결과를 불러옵니다: {channel_name}")

                # 캐시된 리포트 로드
                cached_report_data = self.cached_report.get("report", {})
                self.report = BenchmarkReport.from_dict(cached_report_data)
                self.channel_urls = self.cached_report.get("channel_urls", [self.pending_url])

                self.pending_url = None
                self.pending_channel_info = None
                self.phase = BenchmarkPhase.REPORT
                self.cached_report_shown = True

                # 리포트 보여주고 확인 대기
                return await self._show_cached_report()
            
            if self.pending_url:
                self.channel_urls.append(self.pending_url)
                channel_name = self.pending_channel_info.channel_name if self.pending_channel_info else self.pending_url

                self.pending_url = None
                self.pending_channel_info = None
                self.phase = BenchmarkPhase.COLLECT

                message = (
                    f"**[완료] {channel_name} 추가 완료!**\n\n"
                    "**추가로 분석할 채널이 있나요?**\n"
                    "- 더 추가하려면 URL 입력\n"
                    "- 분석을 시작하려면 \"분석 시작\" 또는 \"시작\""
                )

                self.status = AgentStatus.WAITING_FEEDBACK
                return AgentResult(
                    success=True,
                    step="benchmark_collect",
                    message=message,
                    needs_feedback=True,
                    data={
                        "phase": self.phase.value,
                        "channels": self.channel_urls
                    }
                )

        # 다른 URL 입력 시
        url = self._extract_youtube_url(feedback)
        if url:
            self.pending_url = None
            self.pending_channel_info = None
            self.phase = BenchmarkPhase.ASK
            return await self._handle_ask_phase(feedback)

        # 그 외
        return AgentResult(
            success=True,
            step="benchmark_confirm",
            message="\"확인\"을 입력하거나 다른 채널 URL을 입력해주세요.",
            needs_feedback=True,
            data={"phase": self.phase.value}
        )

    async def _handle_collect_phase(self, feedback: str) -> AgentResult:
        """COLLECT 페이즈 처리 - 추가 URL 수집 또는 분석 시작"""
        feedback_lower = feedback.lower().strip()

        # 분석 시작 명령
        start_keywords = ["시작", "start", "분석", "analyze", "고", "go", "ㄱ"]
        if any(kw in feedback_lower for kw in start_keywords):
            if not self.channel_urls:
                return AgentResult(
                    success=True,
                    step="benchmark_collect",
                    message="분석할 채널이 없습니다. URL을 먼저 입력해주세요.",
                    needs_feedback=True,
                    data={"phase": self.phase.value}
                )

            self.phase = BenchmarkPhase.ANALYZE
            return await self._start_analysis()

        # URL 추가 시 채널 정보 확인
        url = self._extract_youtube_url(feedback)
        if url:
            if url in self.channel_urls:
                return AgentResult(
                    success=True,
                    step="benchmark_collect",
                    message="이미 추가된 채널입니다. 다른 URL을 입력하거나 \"시작\"을 입력해주세요.",
                    needs_feedback=True,
                    data={"phase": self.phase.value, "channels": self.channel_urls}
                )

            # 채널 정보 미리 가져오기
            emit_progress("채널 확인 중", url[:50])

            try:
                channel_info = await youtube_service.get_channel_info(url)

                if channel_info:
                    self.pending_url = url
                    self.pending_channel_info = channel_info
                    self.phase = BenchmarkPhase.CONFIRM

                    subs = f"{channel_info.subscriber_count:,}" if channel_info.subscriber_count else "비공개"
                    videos = f"{channel_info.video_count:,}" if channel_info.video_count else "알 수 없음"
                    desc = channel_info.description[:150] + "..." if channel_info.description and len(channel_info.description) > 150 else (channel_info.description or "설명 없음")

                    current_list = "\n".join(f"  - {u}" for u in self.channel_urls)
                    message = (
                        f"**{channel_info.channel_name}**\n\n"
                        f"구독자: **{subs}명**\n\n"
                        f"영상 수: **{videos}개**\n\n"
                        f"설명: {desc}\n\n"
                        "현재 추가된 채널:\n"
                        f"{current_list}\n\n"
                        "이 채널을 추가할까요?\n"
                        "- 추가하려면 **확인** 또는 **추가**\n"
                        "- 다른 채널이면 URL을 다시 입력해주세요"
                    )

                    return AgentResult(
                        success=True,
                        step="benchmark_confirm",
                        message=message,
                        needs_feedback=True,
                        data={
                            "phase": self.phase.value,
                            "channels": self.channel_urls,
                            "channel_preview": {
                                "url": url,
                                "name": channel_info.channel_name,
                                "subscribers": channel_info.subscriber_count,
                                "videos": channel_info.video_count
                            }
                        }
                    )
                else:
                    channels_list = "\n".join(f"- {u}" for u in self.channel_urls)
                    return AgentResult(
                        success=True,
                        step="benchmark_collect",
                        message=f"채널 정보를 가져올 수 없습니다: {url}\n\n**현재 채널 목록:**\n{channels_list}\n\n다른 URL을 입력하거나 \"시작\"을 입력하세요.",
                        needs_feedback=True,
                        data={"phase": self.phase.value, "channels": self.channel_urls}
                    )
            except Exception as e:
                channels_list = "\n".join(f"- {u}" for u in self.channel_urls)
                return AgentResult(
                    success=True,
                    step="benchmark_collect",
                    message=f"채널 정보를 가져오는 중 오류가 발생했습니다.\n\n**현재 채널 목록:**\n{channels_list}\n\n다른 URL을 입력하거나 \"시작\"을 입력하세요.",
                    needs_feedback=True,
                    data={"phase": self.phase.value, "channels": self.channel_urls}
                )

        return AgentResult(
            success=True,
            step="benchmark_collect",
            message="URL을 입력하거나 \"시작\"을 입력해주세요.",
            needs_feedback=True,
            data={"phase": self.phase.value}
        )

    async def _start_analysis(self) -> AgentResult:
        emit_progress("분석 시작", f"총 {len(self.channel_urls)}개 채널 분석 예정")
        """분석 시작"""
        self.status = AgentStatus.RUNNING

        channels_list = "\n".join(f"- {u}" for u in self.channel_urls)
        progress_msg = (
            "**분석을 시작합니다...**\n\n"
            f"분석 채널: {len(self.channel_urls)}개\n"
            f"{channels_list}\n\n"
            "잠시만 기다려주세요..."
        )

        # 실제 분석 수행
        try:
            await self._analyze_channels()
            self.phase = BenchmarkPhase.REPORT
            return await self._generate_report()
        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentResult(
                success=False,
                step="benchmark_error",
                message=f"분석 중 오류 발생: {str(e)}",
                needs_feedback=True,
                data={"error": str(e)}
            )

    async def _analyze_channels(self):
        """채널들 분석"""
        for idx, url in enumerate(self.channel_urls, 1):
            emit_progress(f"채널 분석 중 ({idx}/{len(self.channel_urls)})", url[:50])
            channel_data = await self._analyze_single_channel(url)
            if channel_data:
                self.channels_data.append(channel_data)

    async def _analyze_single_channel(self, url: str) -> Optional[Dict[str, Any]]:
        """단일 채널 분석"""
        emit_progress("채널 정보 수집", "메타데이터 가져오는 중...")
        data = {
            "url": url,
            "channel_info": None,
            "videos": [],
            "transcripts": [],
            "thumbnail_urls": [],
        }

        # 채널 정보 가져오기
        if youtube_service.is_channel_url(url):
            data["channel_info"] = await youtube_service.get_channel_info(url)
            videos = await youtube_service.get_channel_videos(url, self.MAX_VIDEOS_PER_CHANNEL)
            data["videos"] = videos
        elif youtube_service.is_video_url(url):
            # 단일 영상 URL인 경우
            video_info = await youtube_service.get_video_info(url)
            if video_info:
                data["videos"] = [video_info]

        # 썸네일 URL 수집
        data["thumbnail_urls"] = await youtube_service.get_thumbnails(
            data["videos"],
            self.MAX_THUMBNAILS_FOR_ANALYSIS
        )

        # 자막 수집 (상위 영상들)
        for video in data["videos"][:self.MAX_TRANSCRIPTS]:
            video_url = f"https://youtube.com/watch?v={video.video_id}"
            transcript = await youtube_service.get_video_transcript(video_url)
            if transcript:
                data["transcripts"].append({
                    "video_id": video.video_id,
                    "title": video.title,
                    "transcript": transcript[:5000]  # 토큰 제한
                })

        return data

    async def _generate_report(self) -> AgentResult:
        emit_progress("리포트 생성", "복제 가이드 작성 중...")
        """종합 리포트 생성"""
        self.report = BenchmarkReport()
        # 채널 URL과 이름 모두 저장
        self.report.analyzed_channels = self.channel_urls
        self.report.channel_names = {}  # {url: channel_name}
        for ch in self.channels_data:
            if ch.get("channel_info") and ch.get("url"):
                self.report.channel_names[ch["url"]] = ch["channel_info"].channel_name
        self.report.analyzed_videos_count = sum(
            len(ch.get("videos", [])) for ch in self.channels_data
        )

        # 1. 썸네일 패턴 분석
        await self._analyze_thumbnail_patterns()

        # 2. 스크립트 패턴 분석
        await self._analyze_script_patterns()

        # 3. 콘텐츠 전략 분석
        await self._analyze_content_strategy()

        # 4. 채널 컨셉 분석
        await self._analyze_channel_concept()

        # 5. 타겟 오디언스 분석
        await self._analyze_audience()

        # 6. 복제 가이드 생성
        await self._generate_replication_guide()

        # 리포트 출력
        report_message = self._format_report()

        # 벤치마크 결과 캐시에 저장
        try:
            cache_key = save_benchmark(self.channel_urls, self.report.to_dict())
            emit_progress("캐시 저장", f"벤치마크 결과 저장 완료 (key: {cache_key})")
        except Exception as e:
            print(f"[BenchmarkerAgent] Failed to save cache: {e}")

        self.status = AgentStatus.COMPLETED

        return AgentResult(
            success=True,
            step="benchmark_complete",
            message=report_message,
            needs_feedback=False,
            data={
                "report": self.report.to_dict(),
                "phase": BenchmarkPhase.REPORT.value,
                "cached": True
            }
        )

    async def _show_cached_report(self) -> AgentResult:
        """캐시된 리포트를 보여주고 확인 대기"""
        report_message = self._format_report()

        # 확인 요청 메시지 추가
        report_message += "\n\n---\n\n**캐시된 벤치마크 리포트입니다.**\n\n"
        report_message += "• 이 리포트로 진행하려면 **'확인'** 또는 **'다음'**\n"
        report_message += "• 새로 분석하려면 **'다시 분석'**"

        self.status = AgentStatus.WAITING_FEEDBACK

        return AgentResult(
            success=True,
            step="benchmark_cached_report",
            message=report_message,
            needs_feedback=True,
            data={
                "report": self.report.to_dict() if self.report else {},
                "phase": BenchmarkPhase.REPORT.value,
                "cached": True,
                "type": "selection",
                "options": [
                    {"id": 1, "label": "확인 (이 리포트로 진행)"},
                    {"id": 2, "label": "다시 분석"}
                ]
            }
        )

    async def _analyze_thumbnail_patterns(self):
        emit_progress("썸네일 분석", "채널 스크린샷 캡처 중...")
        """Playwright 스크린샷으로 썸네일 패턴 분석"""

        # 1. 채널 스크린샷 캡처
        print("Capturing channel screenshots with Playwright...")

        try:
            for url in self.channel_urls:
                screenshot = await screenshot_service.capture_channel(
                    url,
                    capture_individual_thumbnails=True,
                    max_thumbnails=6,
                    scroll_count=2
                )
                self.channel_screenshots.append(screenshot)
                print(f"Captured screenshots for: {screenshot.channel_name or url}")
        except Exception as e:
            print(f"Screenshot capture failed: {e}")
            # 폴백: 기존 방식으로 썸네일 분석
            return await self._analyze_thumbnail_patterns_fallback()
        finally:
            try:
                await screenshot_service.close()
            except:
                pass

        if not self.channel_screenshots:
            return

        # 2. /videos 페이지 스크린샷으로 전체 패턴 분석
        try:
            grid_analyses = []

            for screenshot in self.channel_screenshots:
                if screenshot.videos_page:
                    result = await vision_service.analyze_image_with_thinking(
                        screenshot.videos_page,
                        THUMBNAIL_GRID_ANALYSIS_PROMPT
                    )
                    thinking = result.get("thinking", "")
                    analysis = result.get("answer", "")
                    
                    # thinking 과정 표시
                    if thinking:
                        thinking_preview = thinking[:200] + "..." if len(thinking) > 200 else thinking
                        emit_progress("AI 분석 중", f"[{screenshot.channel_name or 'Channel'}] {thinking_preview}")
                    
                    grid_analyses.append({
                        "channel": screenshot.channel_name or screenshot.channel_url,
                        "analysis": analysis,
                        "thinking": thinking
                    })

            # 개별 썸네일도 분석 (더 상세한 패턴 파악)
            individual_analyses = []
            for screenshot in self.channel_screenshots:
                for i, thumb in enumerate(screenshot.thumbnail_screenshots[:4]):
                    analysis = await vision_service.analyze_image(
                        thumb,
                        INDIVIDUAL_THUMBNAIL_ANALYSIS_PROMPT
                    )
                    individual_analyses.append(analysis)

            # LLM으로 패턴 종합
            if grid_analyses:
                combined = "\n\n".join([
                    f"Channel: {a['channel']}\nGrid Analysis: {a['analysis']}"
                    for a in grid_analyses
                ])

                if individual_analyses:
                    combined += "\n\n--- Individual Thumbnail Details ---\n"
                    combined += "\n\n".join([
                        f"Thumbnail {i+1}: {a}"
                        for i, a in enumerate(individual_analyses[:4])
                    ])

                prompt = f"""Based on these thumbnail analyses from YouTube channel screenshots:

{combined}

Synthesize the patterns and return JSON:
{{
    "color_palette": ["color1", "color2", "color3"],
    "text_style": "description of text styling patterns",
    "face_expression": "description of face/expression patterns",
    "layout_style": "description of layout patterns",
    "common_elements": ["element1", "element2"],
    "consistency_score": 8,
    "replication_tips": ["tip1", "tip2", "tip3"],
    "summary": "2-3 sentence summary of thumbnail style"
}}"""

                response = await llm_service.generate(prompt, temperature=0.5)
                pattern_data = self._parse_json(response)

                if pattern_data:
                    self.report.thumbnail_pattern = ThumbnailPattern(
                        color_palette=pattern_data.get("color_palette", []),
                        text_style=pattern_data.get("text_style", ""),
                        face_expression=pattern_data.get("face_expression", ""),
                        layout_style=pattern_data.get("layout_style", ""),
                        common_elements=pattern_data.get("common_elements", []),
                        summary=pattern_data.get("summary", ""),
                    )

        except Exception as e:
            print(f"Thumbnail pattern analysis failed: {e}")
            await self._analyze_thumbnail_patterns_fallback()

    async def _analyze_thumbnail_patterns_fallback(self):
        """기존 방식의 썸네일 분석 (폴백)"""
        all_thumbnails = []
        for ch in self.channels_data:
            all_thumbnails.extend(ch.get("thumbnail_urls", []))

        if not all_thumbnails:
            return

        thumbnails_to_analyze = all_thumbnails[:4]

        try:
            analyses = []
            for thumb_url in thumbnails_to_analyze:
                thumb_data = await youtube_service.download_thumbnail(thumb_url)
                if thumb_data:
                    b64_data = base64.b64encode(thumb_data).decode("utf-8")
                    analysis = await vision_service.analyze_image(
                        b64_data,
                        "Analyze this YouTube thumbnail. Describe: colors, text style, face/expression if any, layout, visual elements."
                    )
                    analyses.append(analysis)

            if analyses:
                combined_analysis = "\n\n".join([f"Thumbnail {i+1}: {a}" for i, a in enumerate(analyses)])

                prompt = f"""Based on these thumbnail analyses, identify common patterns:

{combined_analysis}

{THUMBNAIL_ANALYSIS_PROMPT}"""

                response = await llm_service.generate(prompt, temperature=0.5)
                pattern_data = self._parse_json(response)

                if pattern_data:
                    self.report.thumbnail_pattern = ThumbnailPattern(
                        color_palette=pattern_data.get("color_palette", []),
                        text_style=pattern_data.get("text_style", ""),
                        face_expression=pattern_data.get("face_expression", ""),
                        layout_style=pattern_data.get("layout_style", ""),
                        common_elements=pattern_data.get("common_elements", []),
                        summary=pattern_data.get("summary", ""),
                    )
        except Exception as e:
            print(f"Fallback thumbnail analysis failed: {e}")

    async def _analyze_script_patterns(self):
        emit_progress("스크립트 분석", "영상 자막 추출 중...")
        """스크립트 패턴 분석"""
        all_transcripts = []
        channel_name = ""

        for ch in self.channels_data:
            all_transcripts.extend(ch.get("transcripts", []))
            if ch.get("channel_info"):
                channel_name = ch["channel_info"].channel_name

        if not all_transcripts:
            self.report.script_pattern = ScriptPattern(summary="(분석 실패: 자막 데이터 없음)")
            return

        try:
            transcripts_text = "\n\n---\n\n".join([
                f"Title: {t['title']}\nTranscript: {t['transcript'][:2000]}"
                for t in all_transcripts[:3]
            ])

            prompt = SCRIPT_ANALYSIS_PROMPT.format(
                channel_name=channel_name,
                transcripts=transcripts_text
            )

            response = await llm_service.generate(prompt, temperature=0.5, max_tokens=2048)
            pattern_data = self._parse_json(response)

            if pattern_data:
                self.report.script_pattern = ScriptPattern(
                    hook_style=pattern_data.get("hook_style", ""),
                    structure=pattern_data.get("structure", ""),
                    tone_and_voice=pattern_data.get("tone_and_voice", ""),
                    recurring_phrases=pattern_data.get("recurring_phrases", []),
                    cta_patterns=pattern_data.get("cta_patterns", []),
                    average_length=pattern_data.get("average_length_words", 0),
                    summary=pattern_data.get("summary", ""),
                )
            else:
                self.report.script_pattern = ScriptPattern(summary="(분석 실패: LLM 응답 파싱 실패)")
        except Exception as e:
            print(f"Script analysis failed: {e}")
            self.report.script_pattern = ScriptPattern(summary=f"(분석 실패: {str(e)[:150]})")

    async def _analyze_content_strategy(self):
        emit_progress("콘텐츠 전략 분석", "영상 메타데이터 분석 중...")
        """콘텐츠 전략 분석"""
        all_videos = []
        channel_name = ""
        channel_description = ""

        for ch in self.channels_data:
            all_videos.extend(ch.get("videos", []))
            if ch.get("channel_info"):
                channel_name = ch["channel_info"].channel_name
                channel_description = ch["channel_info"].description

        if not all_videos:
            self.report.content_strategy = ContentStrategy(summary="(분석 실패: 영상 데이터 없음)")
            return

        try:
            video_data = "\n".join([
                f"- {v.title} | Views: {v.view_count} | Date: {v.upload_date} | Duration: {v.duration}s"
                for v in all_videos[:15]
            ])

            prompt = CONTENT_STRATEGY_PROMPT.format(
                channel_name=channel_name,
                channel_description=channel_description[:500],
                video_data=video_data
            )

            response = await llm_service.generate(prompt, temperature=0.5, max_tokens=2048)
            strategy_data = self._parse_json(response)

            if strategy_data:
                self.report.content_strategy = ContentStrategy(
                    content_pillars=strategy_data.get("content_pillars", []),
                    upload_frequency=strategy_data.get("upload_frequency", ""),
                    video_length_pattern=strategy_data.get("video_length_pattern", ""),
                    trending_topics=strategy_data.get("trending_topics", []),
                    engagement_tactics=strategy_data.get("engagement_tactics", []),
                    summary=strategy_data.get("summary", ""),
                )
            else:
                self.report.content_strategy = ContentStrategy(summary="(분석 실패: LLM 응답 파싱 실패)")
        except Exception as e:
            print(f"Content strategy analysis failed: {e}")
            self.report.content_strategy = ContentStrategy(summary=f"(분석 실패: {str(e)[:150]})")

    async def _analyze_channel_concept(self):
        emit_progress("채널 컨셉 분석", "USP 도출 중...")
        """채널 컨셉 분석"""
        channel_name = ""
        channel_description = ""
        subscriber_count = 0
        top_videos = []

        for ch in self.channels_data:
            if ch.get("channel_info"):
                channel_name = ch["channel_info"].channel_name
                channel_description = ch["channel_info"].description
                subscriber_count = ch["channel_info"].subscriber_count

            videos = ch.get("videos", [])
            sorted_videos = sorted(videos, key=lambda v: v.view_count, reverse=True)
            top_videos.extend(sorted_videos[:5])

        if not channel_name:
            self.report.channel_concept = "(분석 실패: 채널 정보 없음)"
            self.report.unique_selling_point = "(분석 실패: 채널 정보 없음)"
            self.report.brand_voice = "(분석 실패: 채널 정보 없음)"
            return

        try:
            top_videos_text = "\n".join([
                f"- {v.title} (Views: {v.view_count:,})"
                for v in top_videos[:10]
            ])

            content_patterns = self.report.content_strategy.summary if self.report.content_strategy else ""

            prompt = CHANNEL_CONCEPT_PROMPT.format(
                channel_name=channel_name,
                channel_description=channel_description[:500],
                subscriber_count=subscriber_count,
                top_videos=top_videos_text,
                content_patterns=content_patterns
            )

            response = await llm_service.generate(prompt, temperature=0.5, max_tokens=1024)
            concept_data = self._parse_json(response)

            if concept_data:
                self.report.channel_concept = concept_data.get("channel_concept", "")
                self.report.unique_selling_point = concept_data.get("unique_selling_point", "")
                self.report.brand_voice = concept_data.get("brand_voice", "")
            else:
                self.report.channel_concept = "(분석 실패: LLM 응답 파싱 실패)"
                self.report.unique_selling_point = "(분석 실패: LLM 응답 파싱 실패)"
                self.report.brand_voice = "(분석 실패: LLM 응답 파싱 실패)"
        except Exception as e:
            error_msg = f"(분석 실패: {str(e)[:150]})"
            print(f"Channel concept analysis failed: {e}")
            self.report.channel_concept = error_msg
            self.report.unique_selling_point = error_msg
            self.report.brand_voice = error_msg

    async def _analyze_audience(self):
        emit_progress("타겟 오디언스 분석", "시청자 프로필 추론 중...")
        """타겟 오디언스 분석"""
        channel_name = ""
        video_titles = []

        for ch in self.channels_data:
            if ch.get("channel_info"):
                channel_name = ch["channel_info"].channel_name
            for v in ch.get("videos", []):
                video_titles.append(v.title)

        if not video_titles:
            self.report.audience_profile = AudienceProfile(summary="(분석 실패: 영상 데이터 없음)")
            return

        try:
            content_pillars = ", ".join(self.report.content_strategy.content_pillars) if self.report.content_strategy else ""
            titles_text = "\n".join([f"- {t}" for t in video_titles[:15]])

            prompt = AUDIENCE_PROFILE_PROMPT.format(
                channel_name=channel_name,
                content_pillars=content_pillars,
                video_titles=titles_text,
                engagement_data="(Comment analysis not available)"
            )

            response = await llm_service.generate(prompt, temperature=0.5, max_tokens=1024)
            audience_data = self._parse_json(response)

            if audience_data:
                self.report.audience_profile = AudienceProfile(
                    demographics=audience_data.get("demographics", ""),
                    interests=audience_data.get("interests", []),
                    pain_points=audience_data.get("pain_points", []),
                    content_preferences=audience_data.get("content_preferences", ""),
                    summary=audience_data.get("summary", ""),
                )
            else:
                self.report.audience_profile = AudienceProfile(summary="(분석 실패: LLM 응답 파싱 실패)")
        except Exception as e:
            print(f"Audience analysis failed: {e}")
            self.report.audience_profile = AudienceProfile(summary=f"(분석 실패: {str(e)[:150]})")

    async def _generate_replication_guide(self):
        """복제 가이드 생성 - 분리된 호출로 각 섹션 개별 생성"""
        guide = {}
        
        # 공통 컨텍스트
        channel_concept = self.report.channel_concept or ""
        usp = self.report.unique_selling_point or ""
        brand_voice = self.report.brand_voice or ""
        thumbnail_pattern = self.report.thumbnail_pattern.summary if self.report.thumbnail_pattern else ""
        script_pattern = self.report.script_pattern.summary if self.report.script_pattern else ""
        content_strategy = self.report.content_strategy.summary if self.report.content_strategy else ""
        audience_profile = self.report.audience_profile.summary if self.report.audience_profile else ""
        
        # 1. 채널 셋업
        emit_progress("복제 가이드", "채널 셋업 생성 중...")
        try:
            prompt = REPLICATION_CHANNEL_SETUP_PROMPT.format(
                channel_concept=channel_concept,
                usp=usp,
                brand_voice=brand_voice
            )
            response = await llm_service.generate(prompt, temperature=0.7, max_tokens=1024)
            data = self._parse_json(response)
            if data:
                guide["channel_setup"] = data
            else:
                guide["channel_setup"] = {"error": "생성 실패"}
        except Exception as e:
            print(f"Channel setup generation failed: {e}")
            guide["channel_setup"] = {"error": str(e)[:150]}
        
        # 2. 콘텐츠 기획
        emit_progress("복제 가이드", "콘텐츠 기획 생성 중...")
        try:
            prompt = REPLICATION_CONTENT_PLANNING_PROMPT.format(
                channel_concept=channel_concept,
                content_strategy=content_strategy,
                audience_profile=audience_profile
            )
            response = await llm_service.generate(prompt, temperature=0.7, max_tokens=1024)
            data = self._parse_json(response)
            if data:
                guide["content_planning"] = data
            else:
                guide["content_planning"] = {"error": "생성 실패"}
        except Exception as e:
            print(f"Content planning generation failed: {e}")
            guide["content_planning"] = {"error": str(e)[:150]}
        
        # 3. 썸네일 가이드
        emit_progress("복제 가이드", "썸네일 가이드 생성 중...")
        try:
            prompt = REPLICATION_THUMBNAIL_GUIDE_PROMPT.format(
                thumbnail_pattern=thumbnail_pattern,
                brand_voice=brand_voice
            )
            response = await llm_service.generate(prompt, temperature=0.7, max_tokens=1024)
            data = self._parse_json(response)
            if data:
                guide["thumbnail_guide"] = data
            else:
                guide["thumbnail_guide"] = {"error": "생성 실패"}
        except Exception as e:
            print(f"Thumbnail guide generation failed: {e}")
            guide["thumbnail_guide"] = {"error": str(e)[:150]}
        
        # 4. 스크립트 템플릿
        emit_progress("복제 가이드", "스크립트 템플릿 생성 중...")
        try:
            prompt = REPLICATION_SCRIPT_TEMPLATE_PROMPT.format(
                script_pattern=script_pattern,
                brand_voice=brand_voice,
                audience_profile=audience_profile
            )
            response = await llm_service.generate(prompt, temperature=0.7, max_tokens=1024)
            data = self._parse_json(response)
            if data:
                guide["script_template"] = data
            else:
                guide["script_template"] = {"error": "생성 실패"}
        except Exception as e:
            print(f"Script template generation failed: {e}")
            guide["script_template"] = {"error": str(e)[:150]}
        
        # 5. 참여 전략
        emit_progress("복제 가이드", "참여 전략 생성 중...")
        try:
            prompt = REPLICATION_ENGAGEMENT_PROMPT.format(
                content_strategy=content_strategy,
                audience_profile=audience_profile
            )
            response = await llm_service.generate(prompt, temperature=0.7, max_tokens=1024)
            data = self._parse_json(response)
            if data:
                guide["engagement_strategy"] = data
            else:
                guide["engagement_strategy"] = {"error": "생성 실패"}
        except Exception as e:
            print(f"Engagement strategy generation failed: {e}")
            guide["engagement_strategy"] = {"error": str(e)[:150]}
        
        # 6. 첫 영상 아이디어
        emit_progress("복제 가이드", "첫 영상 아이디어 생성 중...")
        try:
            topic_ideas = guide.get("content_planning", {}).get("topic_ideas", [])
            prompt = REPLICATION_FIRST_VIDEOS_PROMPT.format(
                channel_concept=channel_concept,
                content_strategy=content_strategy,
                topic_ideas=", ".join(topic_ideas) if topic_ideas else "일반 주제"
            )
            response = await llm_service.generate(prompt, temperature=0.7, max_tokens=1024)
            data = self._parse_json(response)
            if data and "videos" in data:
                guide["first_10_videos"] = data["videos"]
            elif data:
                guide["first_10_videos"] = data
            else:
                guide["first_10_videos"] = [{"error": "생성 실패"}]
        except Exception as e:
            print(f"First videos generation failed: {e}")
            guide["first_10_videos"] = [{"error": str(e)[:150]}]
        
        self.report.replication_guide = guide

    def _parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """텍스트에서 JSON 추출"""
        if not text:
            return None
        try:
            # 마크다운 코드 블록 제거
            import re
            text = re.sub(r"```json", "", text)
            text = re.sub(r"```", "", text)
            text = text.strip()
            
            # 직접 JSON 파싱 시도
            if text.startswith("{"):
                try:
                    return json.loads(text)
                except:
                    pass
            
            # JSON 블록 찾기
            if "{" in text:
                start = text.find("{")
                depth = 0
                end = start
                for i, char in enumerate(text[start:], start):
                    if char == "{":
                        depth += 1
                    elif char == "}":
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                json_str = text[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"[_parse_json] JSON 파싱 실패: {str(e)[:100]}")
        except Exception as e:
            print(f"[_parse_json] 오류: {str(e)[:100]}")
        return None

    def _format_report(self) -> str:
        """리포트를 마크다운으로 포맷"""
        r = self.report

        sections = []

        # 채널 링크 포맷 (채널명으로 표시, 클릭 시 링크 이동)
        channel_links = []
        channel_names = getattr(r, 'channel_names', {})
        for url in r.analyzed_channels:
            name = channel_names.get(url, url)
            channel_links.append(f"[{name}]({url})")
        channels_display = ', '.join(channel_links) if channel_links else "(채널 정보 없음)"

        # 빈 값 처리 함수
        def val_or_none(v, label=""):
            if not v or v.strip() == "":
                return f"(분석 결과 없음{': ' + label if label else ''})"
            return v

        # 헤더
        header = (
            "# 채널 벤치마킹 리포트\n\n"
            f"**분석 채널:** {channels_display}\n"
            f"**분석 영상 수:** {r.analyzed_videos_count}개\n\n"
            "---\n\n"
            "## 채널 컨셉\n\n"
            f"**핵심 컨셉:** {val_or_none(r.channel_concept)}\n\n"
            f"**차별화 포인트 (USP):** {val_or_none(r.unique_selling_point)}\n\n"
            f"**브랜드 보이스:** {val_or_none(r.brand_voice)}"
        )
        sections.append(header)

        # 썸네일 패턴
        if r.thumbnail_pattern and r.thumbnail_pattern.summary:
            thumb_section = (
                "\n---\n\n"
                "## 썸네일 패턴\n\n"
                f"{r.thumbnail_pattern.summary}\n\n"
                f"- **색상:** {', '.join(r.thumbnail_pattern.color_palette)}\n"
                f"- **텍스트 스타일:** {r.thumbnail_pattern.text_style}\n"
                f"- **레이아웃:** {r.thumbnail_pattern.layout_style}\n"
                f"- **공통 요소:** {', '.join(r.thumbnail_pattern.common_elements)}"
            )
            sections.append(thumb_section)

        # 스크립트 패턴
        if r.script_pattern and r.script_pattern.summary:
            script_section = (
                "\n---\n\n"
                "## 스크립트 패턴\n\n"
                f"{r.script_pattern.summary}\n\n"
                f"- **후킹 스타일:** {r.script_pattern.hook_style}\n"
                f"- **구조:** {r.script_pattern.structure}\n"
                f"- **톤 & 보이스:** {r.script_pattern.tone_and_voice}\n"
                f"- **자주 쓰는 문구:** {', '.join(r.script_pattern.recurring_phrases[:5])}\n"
                f"- **CTA 패턴:** {', '.join(r.script_pattern.cta_patterns[:3])}"
            )
            sections.append(script_section)

        # 콘텐츠 전략
        if r.content_strategy and r.content_strategy.summary:
            strategy_section = (
                "\n---\n\n"
                "## 콘텐츠 전략\n\n"
                f"{r.content_strategy.summary}\n\n"
                f"- **콘텐츠 축:** {', '.join(r.content_strategy.content_pillars)}\n"
                f"- **업로드 빈도:** {r.content_strategy.upload_frequency}\n"
                f"- **영상 길이 패턴:** {r.content_strategy.video_length_pattern}\n"
                f"- **인기 주제:** {', '.join(r.content_strategy.trending_topics[:5])}"
            )
            sections.append(strategy_section)

        # 타겟 오디언스
        if r.audience_profile and r.audience_profile.summary:
            audience_section = (
                "\n---\n\n"
                "## 타겟 오디언스\n\n"
                f"{r.audience_profile.summary}\n\n"
                f"- **인구통계:** {r.audience_profile.demographics}\n"
                f"- **관심사:** {', '.join(r.audience_profile.interests[:5])}\n"
                f"- **니즈/고민:** {', '.join(r.audience_profile.pain_points[:3])}"
            )
            sections.append(audience_section)

        # 복제 가이드
        if r.replication_guide:
            guide = r.replication_guide

            # 에러가 있으면 에러 메시지 표시
            if guide.get("error"):
                guide_section = (
                    "\n---\n\n"
                    "## 복제 가이드\n\n"
                    f"**{guide.get('error')}**\n\n"
                    "복제 가이드 생성에 실패했습니다. 위의 분석 결과를 참고하여 직접 전략을 수립해주세요."
                )
                sections.append(guide_section)
            else:
                first_videos = guide.get("first_10_videos", [])[:5]
                videos_text = "\n".join([
                    f"  {i+1}. **{v.get('title', '')}** - {v.get('concept', '')}"
                    for i, v in enumerate(first_videos)
                ]) if first_videos else "(영상 아이디어 생성 실패)"

                # 빈 값 처리 함수
                def guide_val(section, key, default="(분석 결과 없음)"):
                    return guide.get(section, {}).get(key, '') or default

                guide_section = (
                    "\n---\n\n"
                    "## 복제 가이드\n\n"
                    "### 채널 셋업\n"
                    f"- **네이밍:** {guide_val('channel_setup', 'naming_style')}\n"
                    f"- **브랜딩:** {guide_val('channel_setup', 'branding_guidelines')}\n\n"
                    "### 콘텐츠 계획\n"
                    f"- **주제 아이디어:** {', '.join(guide.get('content_planning', {}).get('topic_ideas', [])[:5]) or '(분석 결과 없음)'}\n"
                    f"- **업로드 일정:** {guide_val('content_planning', 'upload_schedule')}\n\n"
                    "### 썸네일 가이드\n"
                    f"- **템플릿:** {guide_val('thumbnail_guide', 'template_description')}\n"
                    f"- **색상:** {guide_val('thumbnail_guide', 'color_scheme')}\n\n"
                    "### 스크립트 템플릿\n"
                    f"- **후킹:** {guide_val('script_template', 'hook_template')}\n"
                    f"- **구조:** {guide_val('script_template', 'structure_outline')}\n\n"
                    "### 첫 5개 영상 아이디어\n"
                    f"{videos_text}"
                )
                sections.append(guide_section)

        return "\n".join(sections)

    async def _handle_analyze_phase(self, feedback: str) -> AgentResult:
        """분석 중 피드백 (진행 상황 등)"""
        return AgentResult(
            success=True,
            step="benchmark_analyzing",
            message="분석이 진행 중입니다. 잠시만 기다려주세요...",
            needs_feedback=True,
            data={"phase": self.phase.value}
        )

    async def _handle_report_phase(self, feedback: str) -> AgentResult:
        """리포트 완료 후 피드백"""
        self.status = AgentStatus.COMPLETED
        return AgentResult(
            success=True,
            step="benchmark_complete",
            message="벤치마킹이 완료되었습니다.",
            needs_feedback=False,
            data={"report": self.report.to_dict() if self.report else None}
        )
