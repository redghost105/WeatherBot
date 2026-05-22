#!/bin/bash

# Paper Trading Session Launcher
# Starts trading_engine.py in background with comprehensive logging
# Auto-restarts if process dies
# Full audit trail saved to ~/trading_logs/

set -e

cd /home/carter/claude_programs/Polymarket

# Configuration
TRADING_MODE="paper"
MIN_EDGE_THRESHOLD="0.10"
TRADING_SCAN_INTERVAL="300"  # 5 minutes
LOG_DIR="$HOME/trading_logs"
DATE=$(date +"%Y-%m-%d")
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$LOG_DIR/trading_${DATE}.log"
PID_FILE="/tmp/polymarket_trading.pid"

# Create logs directory
mkdir -p "$LOG_DIR"

# Export configuration
export TRADING_MODE
export MIN_EDGE_THRESHOLD
export TRADING_SCAN_INTERVAL
export PYTHONUNBUFFERED=1  # Unbuffered output for real-time logging

echo "=================================================="
echo "🚀 POLYMARKET PAPER TRADING SESSION STARTED"
echo "=================================================="
echo "Start Time: $(date)"
echo "Mode: $TRADING_MODE"
echo "Min Edge Threshold: $MIN_EDGE_THRESHOLD"
echo "Scan Interval: ${TRADING_SCAN_INTERVAL}s"
echo "Log File: $LOG_FILE"
echo "=================================================="
echo ""

# Function to start the engine
start_engine() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting trading engine..." >> "$LOG_FILE"

    # Start in background, redirect all output to log file
    nohup python3 trading_engine.py >> "$LOG_FILE" 2>&1 &

    local PID=$!
    echo $PID > "$PID_FILE"

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Trading engine started with PID: $PID" >> "$LOG_FILE"
    echo "✓ Trading engine running (PID: $PID)"
    echo "✓ Logging to: $LOG_FILE"

    return $PID
}

# Function to monitor engine
monitor_engine() {
    local PID=$1

    while true; do
        if ! kill -0 $PID 2>/dev/null; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  Trading engine crashed (PID: $PID)" >> "$LOG_FILE"
            echo "⚠️  Trading engine crashed. Restarting..."

            # Wait 30 seconds before restart
            sleep 30
            start_engine
            PID=$!
        fi

        # Check every 30 seconds
        sleep 30
    done
}

# Start the engine
start_engine &
ENGINE_PID=$!

# Trap signals to clean up
cleanup() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Shutting down trading engine..." >> "$LOG_FILE"
    kill $ENGINE_PID 2>/dev/null || true
    if [ -f "$PID_FILE" ]; then
        kill $(cat "$PID_FILE") 2>/dev/null || true
        rm -f "$PID_FILE"
    fi
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Trading engine shutdown complete" >> "$LOG_FILE"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Monitor engine (restart if it dies)
monitor_engine $ENGINE_PID &
MONITOR_PID=$!

echo ""
echo "📊 MONITORING SETUP"
echo "=================================================="
echo "Process ID (Engine): See PID file"
echo "Monitor PID: $MONITOR_PID"
echo ""
echo "To view logs in real-time:"
echo "  tail -f $LOG_FILE"
echo ""
echo "To view trading summary:"
echo "  ./view_trading_logs.sh"
echo ""
echo "To stop trading:"
echo "  kill $MONITOR_PID"
echo "  pkill -f trading_engine.py"
echo ""
echo "To check if running:"
echo "  ps aux | grep trading_engine"
echo "=================================================="
echo ""

# Keep this script running
wait $MONITOR_PID
