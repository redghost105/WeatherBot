# Paper Trading Session Guide

## ✅ Status: TRADING ENGINE NOW RUNNING

Your automated paper trading session is **currently active** and continuously scanning Kalshi markets every 5 minutes.

**Current Process:**
- PID: See with `ps aux | grep trading_engine`
- Mode: 🟡 PAPER (simulated trades, no real money at risk)
- Status: 🟢 RUNNING
- Logs: `~/trading_logs/trading_2026-05-22.log`

---

## 📊 Quick Monitoring Commands

### View Live Logs (Real-Time)
```bash
tail -f ~/trading_logs/trading_$(date +%Y-%m-%d).log
```
Shows logs as they're written - updates in real-time as signals are generated and trades executed.

### View Trading Summary
```bash
cd ~/claude_programs/Polymarket
./view_trading_logs.sh
```
Quick overview of today's trading performance with key statistics.

### View Live Dashboard
```bash
cd ~/claude_programs/Polymarket
bash trading_dashboard.sh
```
ASCII dashboard showing:
- Engine status (running/stopped)
- Today's statistics (scans, signals, executions)
- Recent activity
- Latest signals and executions
- Available commands

### Auto-Refresh Dashboard (Every 10 seconds)
```bash
watch -n 10 'bash ~/claude_programs/Polymarket/trading_dashboard.sh'
```
Continuously updates the dashboard. Press `q` to exit.

### Check if Engine is Running
```bash
ps aux | grep -E "trading_engine|start_paper" | grep -v grep
```
Shows all trading-related processes.

### View All Logs for This Session
```bash
ls -lh ~/trading_logs/
```
Shows all trading logs with file sizes and timestamps.

---

## 🔧 Managing the Trading Session

### Stop Paper Trading (Graceful)
```bash
pkill -f trading_engine.py
```
Stops the trading engine immediately. Logs are preserved.

### Restart Paper Trading
```bash
cd ~/claude_programs/Polymarket
./start_paper_trading.sh
```
Starts a new trading session with fresh logs.

### View Last 100 Lines of Today's Log
```bash
tail -100 ~/trading_logs/trading_$(date +%Y-%m-%d).log
```

### Search for Specific Markets in Logs
```bash
grep "KXLOWTSATX" ~/trading_logs/trading_$(date +%Y-%m-%d).log
```
Find all activity for a specific market ticker.

### Search for Errors
```bash
grep -i "error\|failed\|exception" ~/trading_logs/trading_$(date +%Y-%m-%d).log
```

### Count Trading Metrics
```bash
# Total signals generated
grep -c "✓ Signal generated" ~/trading_logs/trading_$(date +%Y-%m-%d).log

# Total trades executed
grep -c "execution complete" ~/trading_logs/trading_$(date +%Y-%m-%d).log

# Rejected trades
grep -c "Rejected" ~/trading_logs/trading_$(date +%Y-%m-%d).log
```

---

## 🚀 Setting Up Auto-Start on System Wake

### Option 1: Systemd Service (Recommended)

The systemd service is already installed at:
```
~/.config/systemd/user/polymarket-trading.service
```

**Enable auto-start:**
```bash
systemctl --user enable polymarket-trading.service
```

**Start the service:**
```bash
systemctl --user start polymarket-trading.service
```

**Check status:**
```bash
systemctl --user status polymarket-trading.service
```

**View service logs:**
```bash
journalctl --user-unit polymarket-trading.service -f
```

**Disable (if needed):**
```bash
systemctl --user disable polymarket-trading.service
```

### Option 2: Desktop Entry (GUI Launch)

The desktop entry is installed at:
```
~/.local/share/applications/polymarket-paper-trading.desktop
```

This makes the trading session appear in your application launcher:
- Search for "Polymarket" in activities
- Click to launch paper trading
- Automatically runs in background

### Option 3: Cron Job (@reboot)

For additional reliability, add to crontab:

```bash
crontab -e
```

Add this line:
```
@reboot sleep 30 && /home/carter/claude_programs/Polymarket/start_paper_trading.sh > /home/carter/trading_logs/cron_startup.log 2>&1
```

---

## 📈 Understanding the Logs

### Signal Generated Log Entry
```
[INFO] ✓ Signal generated for KXLOWTSATX-26MAY22-T71: edge=17.3%, confidence=78/100
```
- **KXLOWTSATX-26MAY22-T71**: Market ticker
- **edge=17.3%**: Price edge detected (model prob 17% higher than market)
- **confidence=78/100**: Confidence score (0-100)

### Validation Log Entry
```
[INFO] ✓ Validated KXLOWTSATX-26MAY22-T71: size=$3.00, edge=17.3%, confidence=78/100
```
- Signal passed all risk checks
- Trade size: $3.00
- Ready for execution

### Execution Log Entry
```
[INFO] [PAPER] BUY 2 of KXLOWTSATX-26MAY22-T71 (71-72)
[INFO] ✓ KXLOWTSATX-26MAY22-T71 execution complete: 2 order(s)
```
- Paper mode: `[PAPER]` indicates simulated (not real money)
- 2 contracts ordered for 71-72°F bucket
- Execution complete

### Rejection Log Entry
```
[INFO] Rejected KXLOWTSATX-26MAY22-T71: Trade size $4.50 exceeds max $4.00
```
- Signal failed risk validation
- Reason: exceeds maximum position size
- Signal discarded

### Audit Log Entry
```
[AUDIT] {"station_id": "KNYC", "method": "blended", "forecast_mean": 70.1, 
         "bias_applied": 2.1, "adjusted_mean": 68.0, "confidence": 0.78, 
         "prob_sum": 0.9998}
```
- Full audit trail of probability calculation
- Station: KNYC (NYC)
- Method: hybrid (ensemble + statistical)
- Forecast adjusted for known bias

---

## 📊 Expected Performance

### Typical Daily Activity (Paper Mode)

With live Kalshi weather markets:
- **Markets Scanned**: 10-20 per scan (every 5 min)
- **Signals Generated**: 2-5 per day (depends on edges available)
- **Validation Rate**: 60-80% (most signals pass risk checks)
- **Execution Rate**: 80-100% (validated signals execute)

### Expected Trade Metrics

**Edge Distribution**:
- Average edge: 10-15%
- Max edge: 30-50% (rare, high-conviction)
- Min edge: 10% (threshold)

**Confidence Distribution**:
- Average: 65-75/100
- Range: 55-95/100

**Position Sizing**:
- Typical: $2-4 per trade (3-4% of equity)
- Range: $1-4 depending on available equity

---

## 🎯 Trading Lifecycle

### 1. Market Scan (Every 5 minutes)
```
[INFO] Found 28 open markets
[INFO] Qualified 15 markets in 18-30 hour window
```
Engine identifies 10-20 viable markets.

### 2. Signal Generation
```
[INFO] ✓ Signal generated for MARKET: edge=X%, confidence=Y/100
```
Weather predictor finds price mismatches.

### 3. Risk Validation
```
[INFO] ✓ Validated MARKET: size=$X, edge=Y%, confidence=Z/100
```
Or:
```
[INFO] Rejected MARKET: Reason (size/exposure/confidence/loss limit)
```

### 4. Order Execution
```
[INFO] [PAPER] BUY N of MARKET (BUCKET)
[INFO] ✓ MARKET execution complete: N order(s)
```

### 5. Resolution Learning (Every 3 scans ~15 minutes)
```
[INFO] ✓ Market settled: MARKET | Actual: 72.1°F | PnL: $97.00
[INFO] Updated bias for STATION: forecast≈70.0°F, actual=72.1°F
```
System learns from outcomes and improves future predictions.

---

## 🛡️ Safety & Limits

### Risk Constraints (All Active)
```
Global Exposure Limit:    25% of equity
Per-City Limit:           10% of equity
Single Trade Max:          4% of equity
Daily Loss Soft Stop:     -5% of equity (warning)
Daily Loss Hard Stop:     -8% of equity (circuit breaker)
Minimum Confidence:        55/100
Minimum Edge:              10%
```

### Example: $100 Account
```
Global limit:     $25 max at any time
Per-city limit:   $10 per city maximum
Single trade:      $4 maximum per trade
Soft loss:        -$5 daily (warns, can continue)
Hard loss:        -$8 daily (stops all trading)
```

---

## 📋 Log Interpretation Examples

### Good Signal
```
[INFO] ✓ Signal generated for KXLOWTSATX-26MAY22-T71: edge=18.5%, confidence=82/100
[INFO] ✓ Validated KXLOWTSATX-26MAY22-T71: size=$3.00, edge=18.5%, confidence=82/100
[INFO] [PAPER] BUY 2 of KXLOWTSATX-26MAY22-T71 (71-72)
[INFO] [PAPER] BUY 1 of KXLOWTSATX-26MAY22-T71 (72-73)
[INFO] ✓ KXLOWTSATX-26MAY22-T71 execution complete: 2 order(s)
```
✓ High edge (18.5%), high confidence (82/100) → Executed with adjacent spread

### Rejected Signal
```
[INFO] ✓ Signal generated for KXLOWTSATX-26MAY22-T72: edge=12.3%, confidence=58/100
[INFO] Rejected KXLOWTSATX-26MAY22-T72: Confidence 58 below threshold 55
```
✓ Signal too weak (confidence just above threshold) → Rejected automatically

### Market with No Signals
```
[INFO] Qualified 15 markets in 18-30 hour window
[INFO] Generated 0 trading signals from 15 markets
```
✓ No opportunities found → Waits for next scan

---

## 🔍 Troubleshooting

### Engine Stops Unexpectedly
**Check logs for error:**
```bash
grep -i "error\|exception" ~/trading_logs/trading_$(date +%Y-%m-%d).log | tail -10
```

**Common causes:**
- API rate limit hit → Auto-restarts in 30 seconds
- Network issue → Check connectivity
- Configuration error → Review environment variables

**Restart manually:**
```bash
pkill -f trading_engine.py
cd ~/claude_programs/Polymarket
./start_paper_trading.sh
```

### No Signals Being Generated
**Possible reasons:**
1. No markets in 18-30 hour window yet
2. All markets have insufficient edges (< 10%)
3. All potential trades rejected by risk manager

**Check log:**
```bash
tail -50 ~/trading_logs/trading_$(date +%Y-%m-%d).log | grep -E "Qualified|Generated|Rejected"
```

### High Rejection Rate
**Check which signals are rejected:**
```bash
grep "Rejected" ~/trading_logs/trading_$(date +%Y-%m-%d).log
```

**Common reasons:**
- Position size too large → Lower `MIN_EDGE_THRESHOLD` to find better edges
- City already concentrated → Diversify across cities
- Daily loss limit hit → Engine pauses until next day

---

## 💾 Log Archive & Analysis

### Daily Log Files
```bash
ls -lh ~/trading_logs/trading_*.log
```

Each day gets its own log file. Files contain full audit trail for backtesting.

### Archiving Old Logs
```bash
# Compress logs older than 7 days
find ~/trading_logs -name "trading_*.log" -mtime +7 -exec gzip {} \;

# View compressed logs
zcat ~/trading_logs/trading_2026-05-15.log.gz | tail -100
```

### Export Trading Summary
```bash
# Create CSV of all signals from today
grep "✓ Signal generated" ~/trading_logs/trading_$(date +%Y-%m-%d).log | \
  sed 's/.*for //' | sed 's/: edge=/,/' | sed 's/%, confidence=/,/' | \
  sed 's/%//' > trading_signals_$(date +%Y-%m-%d).csv
```

---

## 📞 Quick Reference

| Task | Command |
|------|---------|
| View live logs | `tail -f ~/trading_logs/trading_$(date +%Y-%m-%d).log` |
| Summary | `./view_trading_logs.sh` |
| Dashboard | `bash trading_dashboard.sh` |
| Stop engine | `pkill -f trading_engine.py` |
| Check status | `ps aux \| grep trading_engine` |
| View all logs | `ls -lh ~/trading_logs/` |
| Count signals | `grep -c "✓ Signal" ~/trading_logs/trading_$(date +%Y-%m-%d).log` |
| Count trades | `grep -c "execution complete" ~/trading_logs/trading_$(date +%Y-%m-%d).log` |
| Find errors | `grep -i error ~/trading_logs/trading_$(date +%Y-%m-%d).log` |
| Follow logs | `tail -F ~/trading_logs/trading_$(date +%Y-%m-%d).log` |

---

## Next Steps

1. **Monitor for 1 hour** - Verify signals are being generated
2. **Review 1 day** - Analyze performance and edge capture
3. **Tune if needed** - Adjust `MIN_EDGE_THRESHOLD` based on results
4. **Plan next week** - Decide if ready for live trading

**Live Trading Checklist:**
- [ ] Paper trading running stably for 1 week
- [ ] Win rate acceptable (60%+ in simulation)
- [ ] Edge capture reasonable (10-20% typical)
- [ ] No crashes or errors in logs
- [ ] Dashboard monitoring set up
- [ ] Risk limits understood and appropriate

---

**Current Session Started**: 2026-05-22 10:47:06 UTC  
**Trading Mode**: 🟡 PAPER (simulated)  
**Status**: 🟢 RUNNING  
**Log Location**: ~/trading_logs/trading_2026-05-22.log

Happy trading! 📊
