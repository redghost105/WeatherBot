#!/bin/bash

# Trading Log Viewer
# Shows trading performance summary from logs

LOG_DIR="$HOME/trading_logs"
TODAY=$(date +"%Y-%m-%d")
LOG_FILE="$LOG_DIR/trading_${TODAY}.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "No log file found for today: $LOG_FILE"
    echo ""
    echo "Available logs:"
    ls -lh "$LOG_DIR"/trading_*.log 2>/dev/null || echo "No logs found"
    exit 1
fi

echo "=========================================="
echo "📊 PAPER TRADING PERFORMANCE SUMMARY"
echo "=========================================="
echo "Log File: $LOG_FILE"
echo "Date: $TODAY"
echo ""

# Count signals and trades
SIGNALS=$(grep -c "Signal generated" "$LOG_FILE" 2>/dev/null || echo "0")
VALIDATED=$(grep -c "Validated.*signals passed" "$LOG_FILE" 2>/dev/null || echo "0")
EXECUTED=$(grep -c "execution complete" "$LOG_FILE" 2>/dev/null || echo "0")
FAILED=$(grep -c "Trade execution failed\|Rejected" "$LOG_FILE" 2>/dev/null || echo "0")

echo "📈 SIGNAL SUMMARY"
echo "  Signals Generated: $SIGNALS"
echo "  Signals Validated: $VALIDATED"
echo "  Trades Executed: $EXECUTED"
echo "  Trades Failed/Rejected: $FAILED"
echo ""

# Show latest signals
echo "📝 LATEST SIGNALS (Last 10):"
echo "----------------------------------------"
grep "✓ Signal generated" "$LOG_FILE" | tail -10 | sed 's/^/  /'
echo ""

# Show latest executions
echo "✅ LATEST EXECUTIONS (Last 5):"
echo "----------------------------------------"
grep "execution complete" "$LOG_FILE" | tail -5 | sed 's/^/  /'
echo ""

# Show errors if any
ERROR_COUNT=$(grep -c "ERROR\|FAILED" "$LOG_FILE" 2>/dev/null || echo "0")
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "⚠️  RECENT ERRORS (Last 5):"
    echo "----------------------------------------"
    grep "ERROR\|FAILED" "$LOG_FILE" | tail -5 | sed 's/^/  /'
    echo ""
fi

# Show status
echo "🔍 CURRENT STATUS:"
echo "----------------------------------------"
LAST_LINE=$(tail -5 "$LOG_FILE" | grep -E "Generated|Validated|Executed" | tail -1)
if [ -z "$LAST_LINE" ]; then
    LAST_LINE=$(tail -1 "$LOG_FILE")
fi
echo "  $LAST_LINE"
echo ""

# Show real-time tail option
echo "=========================================="
echo "To follow live logs:"
echo "  tail -f $LOG_FILE"
echo ""
echo "To search for specific market:"
echo "  grep KXLOWTSATX $LOG_FILE"
echo ""
echo "To view all logs:"
echo "  ls -lh $LOG_DIR"
echo "=========================================="
