# /test Command

Run tests for routine-studio.

## Usage
```
/test [scope]
```

## Scopes
- `unit` - Unit tests only
- `e2e` - E2E tests only
- `all` - All tests (default)

## Execution
```bash
# Frontend tests
cd apps/front && npm test

# Backend tests
cd apps/api && pytest

# E2E tests
npx playwright test
```
