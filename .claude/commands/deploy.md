# /deploy Command

Deploy routine-studio to production.

## Usage
```
/deploy [target]
```

## Targets
- `api` - Deploy API only
- `front` - Deploy frontend only  
- `all` - Deploy both (default)

## Execution
```bash
cd /data/routine/routine-studio
./scripts/deploy.sh [target]
```

## Verification
1. Check service health
2. Verify API endpoints respond
3. Test frontend loads correctly
