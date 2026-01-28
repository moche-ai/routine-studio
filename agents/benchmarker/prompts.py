"""벤치마킹 에이전트 프롬프트 템플릿"""


THUMBNAIL_ANALYSIS_PROMPT = """Analyze these YouTube thumbnails from the same channel.

Identify patterns:
1. Color palette (dominant colors, brand colors)
2. Text style (font type, size, positioning, effects)
3. Face/expression patterns (emotions, angles, editing style)
4. Layout structure (composition, element placement)
5. Common visual elements (icons, borders, backgrounds)

Return JSON:
{
    "color_palette": ["color1", "color2", "color3"],
    "text_style": "description of text styling patterns",
    "face_expression": "description of face/expression patterns",
    "layout_style": "description of layout patterns",
    "common_elements": ["element1", "element2"],
    "summary": "2-3 sentence summary of thumbnail style"
}"""


SCRIPT_ANALYSIS_PROMPT = """Analyze these video transcripts from the same YouTube channel.

Channel: {channel_name}

Transcripts:
{transcripts}

Identify patterns:
1. Hook style - How do videos start? First 30 seconds pattern
2. Structure - Intro/body/conclusion format
3. Tone and voice - Formal/casual, energy level, speaking style
4. Recurring phrases - Catchphrases, repeated expressions
5. CTA patterns - How they ask for likes, subs, comments

Return JSON:
{{
    "hook_style": "description of opening hook patterns",
    "structure": "description of video structure",
    "tone_and_voice": "description of speaking style and tone",
    "recurring_phrases": ["phrase1", "phrase2", "phrase3"],
    "cta_patterns": ["cta1", "cta2"],
    "average_length_words": 0,
    "summary": "2-3 sentence summary of script style"
}}"""


CONTENT_STRATEGY_PROMPT = """Analyze the content strategy of this YouTube channel.

Channel: {channel_name}
Description: {channel_description}

Video data (title, views, upload_date, duration):
{video_data}

Analyze:
1. Content pillars - Main topic categories/themes
2. Upload frequency - How often they post
3. Video length patterns - Short/medium/long, when they use each
4. Trending topics - Which topics get most engagement
5. Engagement tactics - How they drive interaction

Return JSON:
{{
    "content_pillars": ["pillar1", "pillar2", "pillar3"],
    "upload_frequency": "frequency pattern description",
    "video_length_pattern": "length pattern description",
    "trending_topics": ["topic1", "topic2", "topic3"],
    "engagement_tactics": ["tactic1", "tactic2"],
    "summary": "2-3 sentence strategy summary"
}}"""


AUDIENCE_PROFILE_PROMPT = """Analyze the target audience of this YouTube channel.

Channel: {channel_name}
Content pillars: {content_pillars}
Sample video titles:
{video_titles}

Sample comments/engagement patterns:
{engagement_data}

Infer:
1. Demographics - Age range, gender, location tendencies
2. Interests - What else they might be interested in
3. Pain points - Problems/needs the content addresses
4. Content preferences - What format/style they prefer

Return JSON:
{{
    "demographics": "demographic profile description",
    "interests": ["interest1", "interest2", "interest3"],
    "pain_points": ["pain1", "pain2", "pain3"],
    "content_preferences": "preference description",
    "summary": "2-3 sentence audience summary"
}}"""


CHANNEL_CONCEPT_PROMPT = """Analyze this YouTube channel's core concept and positioning.

Channel: {channel_name}
Description: {channel_description}
Subscriber count: {subscriber_count}

Top performing videos:
{top_videos}

Content patterns:
{content_patterns}

Analyze:
1. Core channel concept - What is this channel really about?
2. Unique selling point - What makes it different?
3. Brand voice - How does the channel "speak"?

Return JSON:
{{
    "channel_concept": "1-2 sentence channel concept",
    "unique_selling_point": "what makes this channel unique",
    "brand_voice": "description of brand voice and personality"
}}"""


REPLICATION_GUIDE_PROMPT = """Based on the complete analysis of this YouTube channel, create a step-by-step guide to replicate this channel's style and success.

Channel Analysis:
- Concept: {channel_concept}
- USP: {usp}
- Brand Voice: {brand_voice}

Thumbnail Pattern:
{thumbnail_pattern}

Script Pattern:
{script_pattern}

Content Strategy:
{content_strategy}

Target Audience:
{audience_profile}

Create a detailed replication guide covering:
1. Channel setup (name style, branding, description)
2. Content planning (topics, frequency, format)
3. Video production (style, editing, pacing)
4. Thumbnail creation (exact style guide)
5. Script writing (template with examples)
6. Engagement strategy (CTAs, community building)
7. First 10 videos plan

Return JSON:
{{
    "channel_setup": {{
        "naming_style": "guide for channel name",
        "branding_guidelines": "visual branding guide",
        "description_template": "channel description template"
    }},
    "content_planning": {{
        "topic_ideas": ["topic1", "topic2", "topic3"],
        "upload_schedule": "recommended schedule",
        "video_formats": ["format1", "format2"]
    }},
    "production_guide": {{
        "video_style": "production style guide",
        "editing_patterns": "editing guidelines",
        "pacing_notes": "pacing recommendations"
    }},
    "thumbnail_guide": {{
        "template_description": "thumbnail template",
        "color_scheme": "color recommendations",
        "text_guidelines": "text styling guide",
        "example_concepts": ["concept1", "concept2"]
    }},
    "script_template": {{
        "hook_template": "opening hook template",
        "structure_outline": "video structure outline",
        "cta_scripts": ["cta example 1", "cta example 2"],
        "tone_guidelines": "writing tone guide"
    }},
    "engagement_strategy": {{
        "community_tactics": ["tactic1", "tactic2"],
        "comment_engagement": "comment strategy",
        "call_to_actions": "CTA strategy"
    }},
    "first_10_videos": [
        {{"title": "Video 1 idea", "concept": "brief concept"}},
        {{"title": "Video 2 idea", "concept": "brief concept"}}
    ]
}}"""


THUMBNAIL_GRID_ANALYSIS_PROMPT = """You are analyzing a screenshot of a YouTube channel's video page showing multiple video thumbnails in a grid.

Analyze the visual patterns you see across ALL the thumbnails:

1. **Color Scheme**
   - Dominant colors used consistently
   - Brand colors
   - Background color patterns

2. **Text Overlay Style**
   - Font style (bold, italic, outlined, shadowed)
   - Text positioning (top, bottom, center, corner)
   - Text size relative to thumbnail
   - Use of ALL CAPS vs sentence case
   - Language patterns in text

3. **Face/Person Patterns**
   - Are faces shown? How prominent?
   - Facial expressions (surprised, happy, serious, exaggerated)
   - Face positioning and size
   - Consistent editing style (cutouts, circles, etc.)

4. **Composition & Layout**
   - Common layout templates
   - Use of split screens or before/after
   - Object placement patterns
   - Negative space usage

5. **Visual Effects & Style**
   - Arrows, circles, highlights
   - Emojis or icons
   - Borders or frames
   - Brightness/contrast patterns
   - Photo vs graphic style

6. **Consistency Score**
   - How consistent is the visual branding? (1-10)
   - What makes them recognizable as the same channel?

Return JSON:
{
    "color_palette": ["color1", "color2", "color3"],
    "text_style": "detailed description of text styling",
    "face_expression": "description of face/expression patterns",
    "layout_style": "description of common layout patterns",
    "visual_effects": ["effect1", "effect2"],
    "common_elements": ["element1", "element2"],
    "consistency_score": 8,
    "brand_recognition": "what makes this channel's thumbnails recognizable",
    "summary": "2-3 sentence summary of the overall thumbnail style",
    "replication_tips": ["tip1", "tip2", "tip3"]
}"""


INDIVIDUAL_THUMBNAIL_ANALYSIS_PROMPT = """Analyze this individual YouTube thumbnail in detail.

Describe:
1. Main subject/focus
2. Color usage (exact colors if possible)
3. Text content and styling
4. Facial expression if present
5. Background style
6. Any graphics, icons, or effects
7. Overall mood/emotion conveyed

Be specific and detailed for replication purposes."""


# ============ 분리된 복제 가이드 프롬프트들 ============

REPLICATION_CHANNEL_SETUP_PROMPT = """분석된 유튜브 채널의 채널 셋업 가이드를 만들어주세요.

채널 컨셉: {channel_concept}
차별화 포인트: {usp}
브랜드 보이스: {brand_voice}

채널 셋업에 대해 구체적으로 작성해주세요:
1. 채널명 스타일 - 어떤 형태의 이름이 좋을지
2. 브랜딩 가이드라인 - 시각적 브랜딩 방향
3. 채널 설명 템플릿 - 소개글 작성 방법

한국어로 JSON 형식으로 응답:
{{
    "naming_style": "채널명 가이드 (구체적인 예시 포함)",
    "branding_guidelines": "시각적 브랜딩 가이드라인",
    "description_template": "채널 설명 템플릿"
}}"""


REPLICATION_CONTENT_PLANNING_PROMPT = """분석된 유튜브 채널의 콘텐츠 기획 가이드를 만들어주세요.

채널 컨셉: {channel_concept}
콘텐츠 전략: {content_strategy}
타겟 오디언스: {audience_profile}

콘텐츠 기획에 대해 구체적으로 작성해주세요:
1. 추천 주제 아이디어 5개
2. 업로드 스케줄 권장사항
3. 영상 포맷 종류

한국어로 JSON 형식으로 응답:
{{
    "topic_ideas": ["주제1", "주제2", "주제3", "주제4", "주제5"],
    "upload_schedule": "업로드 스케줄 권장사항",
    "video_formats": ["포맷1", "포맷2", "포맷3"]
}}"""


REPLICATION_THUMBNAIL_GUIDE_PROMPT = """당신은 유튜브 썸네일 전문가입니다. 분석된 채널의 썸네일 제작 가이드를 만들어주세요.

썸네일 패턴: {thumbnail_pattern}
브랜드 보이스: {brand_voice}

중요: 아래 JSON 형식으로만 응답하세요. 설명이나 다른 텍스트 없이 순수 JSON만 출력하세요.

{{
    "template_description": "썸네일 레이아웃과 구성 요소 상세 설명",
    "color_scheme": "주요 색상과 배색 가이드",
    "text_guidelines": "폰트, 크기, 위치, 효과 등 텍스트 스타일",
    "example_concepts": ["썸네일 컨셉 1", "썸네일 컨셉 2", "썸네일 컨셉 3"]
}}"""


REPLICATION_SCRIPT_TEMPLATE_PROMPT = """당신은 유튜브 스크립트 전문가입니다. 분석된 채널의 스크립트 작성 가이드를 만들어주세요.

스크립트 패턴: {script_pattern}
브랜드 보이스: {brand_voice}
타겟 오디언스: {audience_profile}

중요: 아래 JSON 형식으로만 응답하세요. 설명이나 다른 텍스트 없이 순수 JSON만 출력하세요.

{{
    "hook_template": "영상 시작 후킹 템플릿 예시 문장",
    "structure_outline": "인트로-본론-마무리 구조 설명",
    "cta_scripts": ["구독 유도 멘트 예시", "좋아요 유도 멘트 예시"],
    "tone_guidelines": "말투와 어조 가이드라인"
}}"""


REPLICATION_ENGAGEMENT_PROMPT = """분석된 유튜브 채널의 참여 유도 전략 가이드를 만들어주세요.

콘텐츠 전략: {content_strategy}
타겟 오디언스: {audience_profile}

참여 전략에 대해 구체적으로 작성해주세요:
1. 커뮤니티 빌딩 전술 3개
2. 댓글 참여 전략
3. CTA 전략

한국어로 JSON 형식으로 응답:
{{
    "community_tactics": ["전술1", "전술2", "전술3"],
    "comment_engagement": "댓글 참여 전략",
    "call_to_actions": "CTA 전략"
}}"""


REPLICATION_FIRST_VIDEOS_PROMPT = """분석된 유튜브 채널 스타일로 첫 5개 영상 아이디어를 만들어주세요.

채널 컨셉: {channel_concept}
콘텐츠 전략: {content_strategy}
추천 주제: {topic_ideas}

각 영상에 대해 제목과 컨셉을 작성해주세요.

한국어로 JSON 형식으로 응답:
{{
    "videos": [
        {{"title": "영상 1 제목", "concept": "간단한 컨셉 설명"}},
        {{"title": "영상 2 제목", "concept": "간단한 컨셉 설명"}},
        {{"title": "영상 3 제목", "concept": "간단한 컨셉 설명"}},
        {{"title": "영상 4 제목", "concept": "간단한 컨셉 설명"}},
        {{"title": "영상 5 제목", "concept": "간단한 컨셉 설명"}}
    ]
}}"""
