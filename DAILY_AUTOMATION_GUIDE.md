# Daily Automation Guide - Market Ticker Updates

## Question: Will the Program Understand Daily Market Ticker Changes?

**Answer: YES** ✅

The program is designed to automatically understand and process new market tickers each day. Here's how:

---

## How Market Tickers Change Daily

### Example Timeline

**May 20, 2026 (Monday)**
```
Markets returned by Kalshi API:
├─ KXHIGHNY-20MAY26-T68  ← Today's market (may be closing)
├─ KXHIGHNY-20MAY26-T70
├─ KXHIGHNY-21MAY26-T68  ← Tomorrow (NEW)
├─ KXHIGHNY-21MAY26-T70
├─ KXHIGHNY-22MAY26-T68  ← Day after (NEW)
└─ ... more future dates
```

**May 21, 2026 (Tuesday)**
```
Markets returned by Kalshi API:
├─ KXHIGHNY-21MAY26-T68  ← Today (was tomorrow)
├─ KXHIGHNY-21MAY26-T70
├─ KXHIGHNY-22MAY26-T68  ← Tomorrow (was day after)
├─ KXHIGHNY-22MAY26-T70
├─ KXHIGHNY-23MAY26-T68  ← NEW day
└─ ... more future dates
```

---

## Program Handles This Automatically

### 1. Dynamic Ticker Parsing ✅
```python
# Extracts date from any ticker format
date_str = parts[1]  # Gets "20MAY26", "21MAY26", etc.
market_date = datetime.strptime(date_str, "%d%b%y")
```

### 2. Fresh Market Fetch ✅
Each execution calls:
```python
# Gets ONLY open and unopened markets (excludes closed)
found_markets = kalshi.get_markets(status="open", series_ticker=KXHIGHNY)
unopened = kalshi.get_markets(status="unopened", series_ticker=KXHIGHNY)
```

### 3. Date Filtering ✅
```python
# Automatically skips past markets
if market_date.date() >= now.date():  # Today and future only
    recent_markets.append(market)
```

---

## How to Set Up Daily Automation

### Option 1: Simple Python Scheduler (Recommended for Development)

**Install schedule library:**
```bash
pip install schedule
```

**Run daily at 9 AM UTC:**
```bash
python3 scheduler.py --daily
```

**Run every hour:**
```bash
python3 scheduler.py --hourly
```

**Run once immediately:**
```bash
python3 scheduler.py
```

---

### Option 2: Linux/Mac Cron Job (Production)

**Edit crontab:**
```bash
crontab -e
```

**Add one of these lines:**

#### Daily at 9 AM UTC
```cron
0 9 * * * /usr/bin/python3 /path/to/kalshi_predictor_live.py >> /tmp/kalshi.log 2>&1
```

#### Every 6 hours
```cron
0 */6 * * * /usr/bin/python3 /path/to/kalshi_predictor_live.py >> /tmp/kalshi.log 2>&1
```

#### Every hour
```cron
0 * * * * /usr/bin/python3 /path/to/kalshi_predictor_live.py >> /tmp/kalshi.log 2>&1
```

#### Every 30 minutes
```cron
*/30 * * * * /usr/bin/python3 /path/to/kalshi_predictor_live.py >> /tmp/kalshi.log 2>&1
```

**Verify it's installed:**
```bash
crontab -l
```

---

### Option 3: Windows Task Scheduler

1. Open **Task Scheduler**
2. Click **Create Basic Task**
3. Name: "WeatherPredictor Daily"
4. **Trigger**: Set to "Daily" at desired time (9 AM)
5. **Action**: 
   - Program: `C:\Python311\python.exe`
   - Arguments: `C:\path\to\kalshi_predictor_live.py`
6. **Conditions**: Check "Wake computer if asleep"
7. Click OK

---

## What Happens with Fresh Markets

### Before (Current)
```
May 20, 2026
├─ Fetch KXHIGHNY series
├─ Get markets for: 20MAY, 21MAY, 22MAY, 23MAY, ...
├─ Process 10 recent markets
└─ Generate report: KALSHI_LIVE_EXECUTION_20260520_090000.md
```

### After (Next Day)
```
May 21, 2026 (9 AM UTC)
├─ Fetch KXHIGHNY series (FRESH)
├─ Get markets for: 21MAY (NEW as "today"), 22MAY, 23MAY, 24MAY (NEW), ...
├─ Automatically skip 20MAY markets (date filtering)
├─ Process 10 NEW recent markets (24-hour old ones removed)
└─ Generate report: KALSHI_LIVE_EXECUTION_20260521_090000.md
```

---

## Key Features for Daily Updates

### ✅ Automatic Date Filtering
```python
now = datetime.now(timezone.utc)
# Only includes markets with settlement_date >= today
if market_date.date() >= now.date():
    process_market()
```

### ✅ Status Filtering
```python
# Only gets tradeable markets (not closed/settled)
open_markets = kalshi.get_markets(status="open", series_ticker=...)
unopened_markets = kalshi.get_markets(status="unopened", series_ticker=...)
```

### ✅ Fresh API Calls
Each execution:
1. Calls API fresh (no caching)
2. Gets current market list
3. Processes only tradeable markets
4. Generates timestamped report

### ✅ No Manual Updates Needed
Just run the script daily - it handles all market ticker changes automatically.

---

## Example: Week of Operations

| Date | Time | Markets Returned | Markets Processed | Report |
|------|------|------------------|-------------------|--------|
| May 20 | 9 AM | 20MAY-23MAY | 20MAY, 21MAY | KALSHI_LIVE_...20260520... |
| May 21 | 9 AM | 21MAY-24MAY | 21MAY, 22MAY | KALSHI_LIVE_...20260521... |
| May 22 | 9 AM | 22MAY-25MAY | 22MAY, 23MAY | KALSHI_LIVE_...20260522... |
| May 23 | 9 AM | 23MAY-26MAY | 23MAY, 24MAY | KALSHI_LIVE_...20260523... |

**Note**: Markets from past dates are automatically filtered out.

---

## Logs and Reports

### Daily Reports
- **File**: `KALSHI_LIVE_EXECUTION_<YYYYMMDD>_<HHMMSS>.md`
- **Contains**: Execution summary, market data, trading signals
- **Auto-generated**: Each run

### Scheduler Logs
If using cron job, logs are saved to `/tmp/kalshi.log`:
```bash
tail -f /tmp/kalshi.log  # Watch live logs
```

---

## Troubleshooting

### No markets found for a city?
- Check if series ticker exists (KXHIGHNY, KXHIGHCHI, etc.)
- Verify API credentials are correct
- Check Kalshi status (may have no open markets for that city)

### Old markets being processed?
- Date filtering is active - markets from yesterday won't be included
- Check the "Market Ticker" log output to see which markets are selected

### Scheduler not running?
- **Cron**: Check `crontab -l` to confirm job is installed
- **Python scheduler**: Keep terminal window open or use `nohup`
- **Task Scheduler**: Check Event Viewer for errors

---

## Best Practices

1. **Run at consistent time**: 9 AM UTC (when markets are most liquid)
2. **Monitor logs**: Check `tail -f /tmp/kalshi.log` periodically
3. **Archive reports**: Move old `.md` files to archive folder monthly
4. **Test first**: Run `python3 scheduler.py` once to verify everything works
5. **Check API limits**: Kalshi allows 100k calls/day (easily sufficient)

---

## Summary

✅ **Yes, the program understands daily market ticker changes**
- Automatically parses new ticker formats
- Filters out past markets
- Fetches fresh markets each run
- No manual updates needed

✅ **Yes, it will refresh new markets every day**
- Just set up a daily cron job or scheduler
- Program handles all ticker changes automatically
- New markets appear in API response each day

✅ **Ready for production**
- All date filtering built in
- Status filtering for only tradeable markets
- Auto-generates timestamped reports
- No manual intervention needed after setup

---

**Next Step**: Choose automation method above and set it up!
