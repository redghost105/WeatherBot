#!/bin/bash

# Live Trading Dashboard
# Real-time monitoring of paper trading performance

clear

LOG_DIR="$HOME/trading_logs"
TODAY=$(date +"%Y-%m-%d")
LOG_FILE="$LOG_DIR/trading_${TODAY}.log"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        POLYMARKET PAPER TRADING LIVE DASHBOARD                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if engine is running
if pgrep -f "python3 trading_engine.py" > /dev/null; then
    ENGINE_PID=$(pgrep -f "python3 trading_engine.py" | head -1)
    echo -e "${GREEN}✓ Trading Engine: RUNNING (PID: $ENGINE_PID)${NC}"
else
    echo -e "${RED}✗ Trading Engine: STOPPED${NC}"
    echo "  Start with: ./start_paper_trading.sh"
fi

echo ""
echo -e "${BLUE}┌─ SYSTEM STATUS ──────────────────────────────────────────────┐${NC}"

# Uptime
if [ -f "$LOG_FILE" ]; then
    START_TIME=$(head -1 "$LOG_FILE" | grep -oP '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}' || echo "N/A")
    UPTIME=$(tail -1 "$LOG_FILE")
    echo -e "  Started: $START_TIME"
else
    echo -e "  ${YELLOW}No logs for today${NC}"
fi

echo -e "  Current Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "  Log File: $LOG_FILE"

echo -e "${BLUE}└──────────────────────────────────────────────────────────────┘${NC}"
echo ""

# Trading statistics
if [ -f "$LOG_FILE" ]; then
    echo -e "${BLUE}┌─ TRADING STATISTICS ─────────────────────────────────────────┐${NC}"

    # Count metrics
    TOTAL_SCANS=$(grep -c "Qualified.*markets" "$LOG_FILE" 2>/dev/null || echo "0")
    SIGNALS=$(grep -c "✓ Signal generated" "$LOG_FILE" 2>/dev/null || echo "0")
    VALIDATED=$(grep -c "Validated.*trades" "$LOG_FILE" 2>/dev/null || echo "0")
    EXECUTED=$(grep -c "execution complete" "$LOG_FILE" 2>/dev/null || echo "0")
    REJECTED=$(grep -c "Rejected" "$LOG_FILE" 2>/dev/null || echo "0")

    echo "  Market Scans: $TOTAL_SCANS"
    echo "  Signals Generated: $SIGNALS"
    echo "  Signals Validated: $VALIDATED"
    echo "  Trades Executed: $EXECUTED"
    echo -e "  Trades Rejected: ${YELLOW}$REJECTED${NC}"

    # Calculate conversion rates
    if [ "$SIGNALS" -gt 0 ]; then
        VALIDATION_RATE=$((VALIDATED * 100 / SIGNALS))
        echo "  Validation Rate: $VALIDATION_RATE%"
    fi

    if [ "$VALIDATED" -gt 0 ]; then
        EXECUTION_RATE=$((EXECUTED * 100 / VALIDATED))
        echo "  Execution Rate: $EXECUTION_RATE%"
    fi

    echo -e "${BLUE}└──────────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # Recent activity
    echo -e "${BLUE}┌─ RECENT ACTIVITY (Last 10 minutes) ───────────────────────────┐${NC}"

    # Show recent signals
    RECENT_SIGNALS=$(grep "$(date '+%Y-%m-%d %H:%M' | cut -c1-13)" "$LOG_FILE" | grep "✓ Signal" | wc -l)
    RECENT_EXECUTED=$(grep "$(date '+%Y-%m-%d %H:%M' | cut -c1-13)" "$LOG_FILE" | grep "execution complete" | wc -l)

    echo "  Recent Signals (Last Hour): $RECENT_SIGNALS"
    echo "  Recent Executions (Last Hour): $RECENT_EXECUTED"

    # Latest signal
    LATEST_SIGNAL=$(grep "✓ Signal generated" "$LOG_FILE" | tail -1)
    if [ -n "$LATEST_SIGNAL" ]; then
        echo ""
        echo "  Latest Signal:"
        echo "    $LATEST_SIGNAL" | sed 's/^/    /'
    fi

    # Latest execution
    LATEST_EXEC=$(grep "execution complete" "$LOG_FILE" | tail -1)
    if [ -n "$LATEST_EXEC" ]; then
        echo ""
        echo "  Latest Execution:"
        echo "    $LATEST_EXEC" | sed 's/^/    /'
    fi

    echo -e "${BLUE}└──────────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # Error summary
    ERROR_COUNT=$(grep -c "ERROR\|FAILED\|Exception" "$LOG_FILE" 2>/dev/null || echo "0")
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  WARNINGS/ERRORS: $ERROR_COUNT${NC}"
        echo "  Recent errors:"
        grep "ERROR\|FAILED" "$LOG_FILE" | tail -3 | sed 's/^/    /'
        echo ""
    fi

else
    echo -e "${YELLOW}No trading activity yet today${NC}"
fi

# Available commands
echo -e "${BLUE}┌─ AVAILABLE COMMANDS ─────────────────────────────────────────┐${NC}"
echo "  View live logs:   tail -f $LOG_FILE"
echo "  View summary:     ./view_trading_logs.sh"
echo "  Stop trading:     pkill -f trading_engine.py"
echo "  Check process:    ps aux | grep trading_engine"
echo "  View all logs:    ls -lh $LOG_DIR"
echo "  Follow tail:      tail -F $LOG_FILE  # Survives log rotation"
echo ""
echo "  Refresh dashboard:"
echo "    watch -n 10 'bash ~/claude_programs/Polymarket/trading_dashboard.sh'"
echo -e "${BLUE}└──────────────────────────────────────────────────────────────┘${NC}"
