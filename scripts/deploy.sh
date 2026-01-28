#!/bin/bash
#
# routine-studio-v2 배포 스크립트
# 사용법: ./scripts/deploy.sh [api|front|all]
#
# 포트 설정 (한번 정하면 변경 불필요):
API_PORT=8002
FRONT_PORT=5182

PROJECT_DIR="/data/routine/routine-studio-v2"

# 환경변수 로드
if [ -f /data/.env ]; then
    set -a
    source /data/.env
    set +a
fi
API_DIR="$PROJECT_DIR/apps/api"
FRONT_DIR="$PROJECT_DIR/apps/front"
API_LOG="/tmp/routine-api.log"
FRONT_LOG="/tmp/routine-front.log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 포트에서 실행 중인 프로세스 종료
kill_port() {
    local port=$1
    local pids=$(lsof -t -i:$port 2>/dev/null)
    if [ -n "$pids" ]; then
        log "포트 $port 프로세스 종료 중... (PID: $pids)"
        echo $pids | xargs kill -9 2>/dev/null
        sleep 1
    fi
}

deploy_api() {
    log "=== API 배포 시작 (포트: $API_PORT) ==="
    
    # 1. 기존 프로세스 종료
    kill_port $API_PORT
    
    # 2. API 시작
    cd $PROJECT_DIR
    log "API 서버 시작 중..."
    nohup python3 -m uvicorn apps.api.main:app --host 0.0.0.0 --port $API_PORT > $API_LOG 2>&1 &
    
    # 3. 헬스체크
    sleep 2
    if curl -s http://localhost:$API_PORT/health > /dev/null; then
        log "✅ API 배포 성공! http://localhost:$API_PORT"
    else
        error "❌ API 시작 실패. 로그 확인: tail -f $API_LOG"
        return 1
    fi
}

deploy_front() {
    log "=== Frontend 배포 시작 (포트: $FRONT_PORT) ==="
    
    # 1. 기존 프로세스 종료
    kill_port $FRONT_PORT
    
    cd $FRONT_DIR
    
    # 2. 의존성 설치 (package.json 변경 시)
    if [ "$1" == "--install" ] || [ ! -d "node_modules" ]; then
        log "npm install 실행 중..."
        npm install
    fi
    
    # 3. 빌드 (항상 fresh build)
    log "빌드 중... (npm run build)"
    npm run build
    
    # 4. Preview 서버 시작
    log "Preview 서버 시작 중..."
    nohup npx vite preview --port $FRONT_PORT --host 0.0.0.0 > $FRONT_LOG 2>&1 &
    
    # 5. 확인
    sleep 2
    if curl -s http://localhost:$FRONT_PORT > /dev/null; then
        log "✅ Frontend 배포 성공! http://localhost:$FRONT_PORT"
    else
        error "❌ Frontend 시작 실패. 로그 확인: tail -f $FRONT_LOG"
        return 1
    fi
}

deploy_all() {
    deploy_api
    deploy_front $1
}

status() {
    echo ""
    log "=== routine-studio-v2 상태 ==="
    echo ""
    
    # API 상태
    if curl -s http://localhost:$API_PORT/health > /dev/null 2>&1; then
        echo -e "API (:$API_PORT):     ${GREEN}✅ Running${NC}"
    else
        echo -e "API (:$API_PORT):     ${RED}❌ Stopped${NC}"
    fi
    
    # Frontend 상태
    if curl -s http://localhost:$FRONT_PORT > /dev/null 2>&1; then
        echo -e "Frontend (:$FRONT_PORT): ${GREEN}✅ Running${NC}"
    else
        echo -e "Frontend (:$FRONT_PORT): ${RED}❌ Stopped${NC}"
    fi
    
    echo ""
    echo "로그:"
    echo "  API:      tail -f $API_LOG"
    echo "  Frontend: tail -f $FRONT_LOG"
    echo ""
}

# 메인
case "$1" in
    api)
        deploy_api
        ;;
    front)
        deploy_front $2
        ;;
    all)
        deploy_all $2
        ;;
    status)
        status
        ;;
    *)
        echo ""
        echo "routine-studio-v2 배포 스크립트"
        echo ""
        echo "사용법:"
        echo "  ./scripts/deploy.sh api          # API만 재배포"
        echo "  ./scripts/deploy.sh front        # Frontend만 재배포"
        echo "  ./scripts/deploy.sh front --install  # npm install 포함"
        echo "  ./scripts/deploy.sh all          # 전체 재배포"
        echo "  ./scripts/deploy.sh all --install    # 전체 + npm install"
        echo "  ./scripts/deploy.sh status       # 상태 확인"
        echo ""
        echo "포트 설정:"
        echo "  API:      $API_PORT"
        echo "  Frontend: $FRONT_PORT"
        echo ""
        status
        ;;
esac
