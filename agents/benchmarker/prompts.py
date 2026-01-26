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
