#!/bin/bash
# 자율 실행 런처 - SSH 끊겨도 계속 실행
# Usage: ./run_autonomous.sh [iterations] [continuous]

SCRIPT_DIR="/data/routine/routine-studio-v2/autonomous"
LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$SCRIPT_DIR/autonomous.pid"

mkdir -p "$LOG_DIR"

# 기존 프로세스 확인
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "기존 프로세스 실행 중 (PID: $OLD_PID)"
        echo "중지하려면: kill $OLD_PID"
        exit 1
    fi
fi

ITERATIONS="${1:-5}"
CONTINUOUS="${2:-}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MAIN_LOG="$LOG_DIR/main_$TIMESTAMP.log"

echo "============================================"
echo "자율 퀄리티 테스트 시작"
echo "반복: $ITERATIONS 회"
echo "연속 모드: ${CONTINUOUS:-OFF}"
echo "로그: $MAIN_LOG"
echo "============================================"

if [ "$CONTINUOUS" == "continuous" ] || [ "$CONTINUOUS" == "-c" ]; then
    nohup python3 "$SCRIPT_DIR/quality_tester.py" -i "$ITERATIONS" -c >> "$MAIN_LOG" 2>&1 &
else
    nohup python3 "$SCRIPT_DIR/quality_tester.py" -i "$ITERATIONS" >> "$MAIN_LOG" 2>&1 &
fi

echo $! > "$PID_FILE"
echo "PID: $(cat $PID_FILE)"
echo ""
echo "로그 확인: tail -f $MAIN_LOG"
echo "중지: kill $(cat $PID_FILE)"
