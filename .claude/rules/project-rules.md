# routine-studio Project Rules

## Architecture
- **Monorepo Structure**: apps/front (React), apps/api (FastAPI)
- **Styling**: Tailwind CSS only, no custom CSS files
- **State**: Zustand for client state, TanStack Query for server state
- **Video**: Remotion for video generation

## Code Standards

### Frontend (apps/front)
- TypeScript strict mode
- React 19 with functional components only
- No class components
- Use `cn()` utility for conditional classes
- Prefer shadcn/ui components

### Backend (apps/api)
- FastAPI with async/await
- Pydantic v2 for validation
- SQLAlchemy 2.0 async
- Proper error handling with HTTPException

## Security
- All API endpoints require authentication
- No secrets in code (use environment variables)
- Input validation on all endpoints
- CORS configured for allowed origins only

## Testing
- Jest for frontend unit tests
- Pytest for backend tests
- E2E tests with Playwright

## Forbidden
- No `any` type in TypeScript
- No `@ts-ignore` or `@ts-expect-error`
- No inline styles (use Tailwind)
- No console.log in production code
