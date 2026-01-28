#!/bin/bash
set -e

cd /data/projects/routine/studio

echo "[1/4] Python syntax 검사..."
python3 -m py_compile agents/planner/agent.py
python3 -m py_compile agents/orchestrator.py
python3 -m py_compile apps/api/main.py
python3 -m py_compile apps/api/services/tts.py
echo "✓ Syntax OK"

echo "[2/4] Docker 이미지 빌드..."
docker build -f Dockerfile.shadow-api -t routine-studio-api . -q

echo "[3/4] 컨테이너 교체..."
docker rm -f routine-studio-api 2>/dev/null || true
docker run -d --name routine-studio-api -p 8002:8002 \
  --env-file /data/.env \
  -e VISION_MODEL=Qwen3-VL-30B \
  -v /data/projects/routine/studio/data:/app/data \
  -v /data/projects/routine/studio/output:/app/output \
  -v /data/volumes/routine/youtube-studio/voices:/data/volumes/routine/youtube-studio/voices:ro \
  --health-cmd="curl -sf http://localhost:8002/health || exit 1" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  --restart unless-stopped \
  routine-studio-api

echo "[4/4] 헬스체크 대기 (5초)..."
sleep 5

if curl -sf http://localhost:8002/health > /dev/null; then
  echo "✓ API 서버 정상 작동!"
  curl -s http://localhost:8002/health | jq .
else
  echo "✗ API 서버 시작 실패!"
  docker logs routine-studio-api --tail 20
  exit 1
fi
