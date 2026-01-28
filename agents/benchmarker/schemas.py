from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class BenchmarkPhase(Enum):
    """벤치마킹 에이전트 페이즈"""
    ASK = "ask"              # 채널 URL 요청
    CONFIRM = "confirm"      # 채널 정보 확인 대기
    COLLECT = "collect"      # URL 수집
    ANALYZE = "analyze"      # 분석 중
    REPORT = "report"        # 리포트 완료


@dataclass
class VideoMetadata:
    """영상 메타데이터"""
    video_id: str
    title: str
    description: str
    view_count: int
    like_count: int
    comment_count: int
    duration: int  # seconds
    upload_date: str
    thumbnail_url: str
    tags: List[str] = field(default_factory=list)


@dataclass
class ChannelMetadata:
    """채널 메타데이터"""
    channel_id: str
    channel_name: str
    subscriber_count: int
    video_count: int
    description: str
    thumbnail_url: str
    banner_url: Optional[str] = None


@dataclass
class ThumbnailPattern:
    """썸네일 패턴 분석 결과"""
    color_palette: List[str] = field(default_factory=list)  # 주요 색상
    text_style: str = ""  # 텍스트 스타일 설명
    face_expression: str = ""  # 얼굴/표정 패턴
    layout_style: str = ""  # 레이아웃 구조
    common_elements: List[str] = field(default_factory=list)  # 공통 시각 요소
    summary: str = ""


@dataclass
class ScriptPattern:
    """스크립트 패턴 분석 결과"""
    hook_style: str = ""  # 도입부 후킹 패턴
    structure: str = ""  # 인트로/본론/결론 구조
    tone_and_voice: str = ""  # 말투와 톤
    recurring_phrases: List[str] = field(default_factory=list)  # 반복 문구
    cta_patterns: List[str] = field(default_factory=list)  # CTA 패턴
    average_length: int = 0  # 평균 스크립트 길이 (단어)
    summary: str = ""


@dataclass
class ContentStrategy:
    """콘텐츠 전략 분석"""
    content_pillars: List[str] = field(default_factory=list)  # 콘텐츠 축
    upload_frequency: str = ""  # 업로드 빈도
    video_length_pattern: str = ""  # 영상 길이 패턴
    trending_topics: List[str] = field(default_factory=list)  # 인기 주제
    engagement_tactics: List[str] = field(default_factory=list)  # 참여 유도 전략
    summary: str = ""


@dataclass
class AudienceProfile:
    """타겟 오디언스 프로필"""
    demographics: str = ""  # 인구통계 추정
    interests: List[str] = field(default_factory=list)  # 관심사
    pain_points: List[str] = field(default_factory=list)  # 고민/니즈
    content_preferences: str = ""  # 선호 콘텐츠 유형
    summary: str = ""


@dataclass
class BenchmarkReport:
    """벤치마크 리포트"""
    # 기본 정보
    analyzed_channels: List[str] = field(default_factory=list)
    analyzed_videos_count: int = 0
    
    # 채널 컨셉
    channel_concept: str = ""
    unique_selling_point: str = ""
    brand_voice: str = ""
    
    # 패턴 분석
    thumbnail_pattern: ThumbnailPattern = field(default_factory=ThumbnailPattern)
    script_pattern: ScriptPattern = field(default_factory=ScriptPattern)
    content_strategy: ContentStrategy = field(default_factory=ContentStrategy)
    audience_profile: AudienceProfile = field(default_factory=AudienceProfile)
    
    # 복제 가이드
    replication_guide: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "analyzed_channels": self.analyzed_channels,
            "analyzed_videos_count": self.analyzed_videos_count,
            "channel_concept": self.channel_concept,
            "unique_selling_point": self.unique_selling_point,
            "brand_voice": self.brand_voice,
            "thumbnail_pattern": {
                "color_palette": self.thumbnail_pattern.color_palette,
                "text_style": self.thumbnail_pattern.text_style,
                "face_expression": self.thumbnail_pattern.face_expression,
                "layout_style": self.thumbnail_pattern.layout_style,
                "common_elements": self.thumbnail_pattern.common_elements,
                "summary": self.thumbnail_pattern.summary,
            },
            "script_pattern": {
                "hook_style": self.script_pattern.hook_style,
                "structure": self.script_pattern.structure,
                "tone_and_voice": self.script_pattern.tone_and_voice,
                "recurring_phrases": self.script_pattern.recurring_phrases,
                "cta_patterns": self.script_pattern.cta_patterns,
                "average_length": self.script_pattern.average_length,
                "summary": self.script_pattern.summary,
            },
            "content_strategy": {
                "content_pillars": self.content_strategy.content_pillars,
                "upload_frequency": self.content_strategy.upload_frequency,
                "video_length_pattern": self.content_strategy.video_length_pattern,
                "trending_topics": self.content_strategy.trending_topics,
                "engagement_tactics": self.content_strategy.engagement_tactics,
                "summary": self.content_strategy.summary,
            },
            "audience_profile": {
                "demographics": self.audience_profile.demographics,
                "interests": self.audience_profile.interests,
                "pain_points": self.audience_profile.pain_points,
                "content_preferences": self.audience_profile.content_preferences,
                "summary": self.audience_profile.summary,
            },
            "replication_guide": self.replication_guide,
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return cls()
        
        thumbnail_data = data.get('thumbnail_pattern', {})
        script_data = data.get('script_pattern', {})
        strategy_data = data.get('content_strategy', {})
        audience_data = data.get('audience_profile', {})
        
        return cls(
            analyzed_channels=data.get('analyzed_channels', []),
            analyzed_videos_count=data.get('analyzed_videos_count', 0),
            channel_concept=data.get('channel_concept', ''),
            unique_selling_point=data.get('unique_selling_point', ''),
            brand_voice=data.get('brand_voice', ''),
            thumbnail_pattern=ThumbnailPattern(
                color_palette=thumbnail_data.get('color_palette', []),
                text_style=thumbnail_data.get('text_style', ''),
                face_expression=thumbnail_data.get('face_expression', ''),
                layout_style=thumbnail_data.get('layout_style', ''),
                common_elements=thumbnail_data.get('common_elements', []),
                summary=thumbnail_data.get('summary', ''),
            ),
            script_pattern=ScriptPattern(
                hook_style=script_data.get('hook_style', ''),
                structure=script_data.get('structure', ''),
                tone_and_voice=script_data.get('tone_and_voice', ''),
                recurring_phrases=script_data.get('recurring_phrases', []),
                cta_patterns=script_data.get('cta_patterns', []),
                average_length=script_data.get('average_length', ''),
                summary=script_data.get('summary', ''),
            ),
            content_strategy=ContentStrategy(
                content_pillars=strategy_data.get('content_pillars', []),
                upload_frequency=strategy_data.get('upload_frequency', ''),
                video_length_pattern=strategy_data.get('video_length_pattern', ''),
                trending_topics=strategy_data.get('trending_topics', []),
                engagement_tactics=strategy_data.get('engagement_tactics', []),
                summary=strategy_data.get('summary', ''),
            ),
            audience_profile=AudienceProfile(
                demographics=audience_data.get('demographics', ''),
                interests=audience_data.get('interests', []),
                pain_points=audience_data.get('pain_points', []),
                content_preferences=audience_data.get('content_preferences', []),
                summary=audience_data.get('summary', ''),
            ),
            replication_guide=data.get('replication_guide', {}),
        )
