# Video Generation Skill

## Overview
routine-studio uses Remotion for programmatic video generation.

## Key Components

### Remotion Setup
- Location: `apps/front/src/remotion/`
- Composition entry: `apps/front/src/remotion/Root.tsx`

### Video Templates
- Channel intros
- News summaries
- Marketing clips

## API Integration

### Render Endpoint
```python
POST /api/v1/render
{
  "template": "news-summary",
  "data": { ... },
  "output_format": "mp4"
}
```

### Status Check
```python
GET /api/v1/render/{job_id}/status
```

## Best Practices
1. Use composition props for dynamic content
2. Optimize assets (images, audio) before rendering
3. Use `delayRender()` for async data fetching
4. Test with `npx remotion preview` before production render
