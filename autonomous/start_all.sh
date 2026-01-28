#!/bin/bash
# 모든 자율 테스트 시작 (SSH 끊겨도 계속 실행)

SCRIPT_DIR="/data/routine/routine-studio-v2/autonomous"
VENV="$SCRIPT_DIR/venv/bin/python3"
LOG_DIR="$SCRIPT_DIR/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$LOG_DIR"

echo "============================================"
echo "자율 테스트 시스템 시작"
echo "시작 시간: $(date)"
echo "============================================"

# 기존 프로세스 정리
pkill -f "auto_improve.py" 2>/dev/null
pkill -f "e2e_tester.py" 2>/dev/null
sleep 2

# 1. 품질 자동 개선 시스템 시작
echo "[1] 품질 자동 개선 시스템 시작..."
nohup $VENV "$SCRIPT_DIR/auto_improve.py" > "$LOG_DIR/auto_improve_$TIMESTAMP.log" 2>&1 &
QUALITY_PID=$!
echo "PID: $QUALITY_PID"
echo $QUALITY_PID > "$SCRIPT_DIR/quality.pid"

# 2. E2E 테스트 시작 (30초 뒤)
echo "[2] E2E 테스트 30초 후 시작 예약..."
nohup bash -c "sleep 30 && $VENV $SCRIPT_DIR/e2e_tester.py" > "$LOG_DIR/e2e_$TIMESTAMP.log" 2>&1 &
E2E_PID=$!
echo "PID: $E2E_PID"
echo $E2E_PID > "$SCRIPT_DIR/e2e.pid"

echo ""
echo "============================================"
echo "자율 테스트 실행 중!"
echo "============================================"
echo ""
echo "로그 확인:"
echo "  품질 테스트: tail -f $LOG_DIR/auto_improve_$TIMESTAMP.log"
echo "  E2E 테스트:  tail -f $LOG_DIR/e2e_$TIMESTAMP.log"
echo ""
echo "상태 확인:"
echo "  ps aux | grep -E 'auto_improve|e2e_tester'"
echo ""
echo "중지:"
echo "  kill $(cat $SCRIPT_DIR/quality.pid) $(cat $SCRIPT_DIR/e2e.pid)"
echo ""
echo "6시간 후 확인하세요!"
