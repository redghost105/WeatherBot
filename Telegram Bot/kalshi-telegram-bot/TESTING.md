# Testing Guide

This guide helps you verify each component of the bot works correctly.

## Unit Tests by Component

### 1. Config Module
```bash
python3 << 'EOF'
from config import TELEGRAM_BOT_TOKEN, TIMEZONE, SEND_TIME
print(f"✅ Config loaded")
print(f"   Timezone: {TIMEZONE}")
print(f"   Send Time: {SEND_TIME}")
EOF
```
**Expected:** Shows timezone and send time without errors.

### 2. Database Module
```bash
python3 << 'EOF'
from database import init_db, get_user_stats
import os

# Clean test database
test_db = "test_predictions.db"
if os.path.exists(test_db):
    os.remove(test_db)

# Use test database
import database
database.DB_PATH = test_db

init_db()
print("✅ Database initialized")

stats = get_user_stats()
print(f"✅ Empty stats: {stats}")

# Cleanup
os.remove(test_db)
EOF
```
**Expected:** Creates database and returns empty stats without errors.

### 3. Kalshi Client Module
```bash
python3 << 'EOF'
from kalshi_client import KalshiClient

# Create client with dummy credentials (will fail on actual API call but validates syntax)
try:
    client = KalshiClient("test_key", "test_secret", "https://api.kalshi.com/v1")
    
    # Test formatting (doesn't need API)
    markets = [
        {"team_a": "Warriors", "team_b": "Suns"},
        {"team_a": "Celtics", "team_b": "Heat"}
    ]
    
    formatted = client.format_market_display(markets)
    print("✅ Market formatting works:")
    print(formatted)
    
except Exception as e:
    print(f"❌ Error: {e}")
EOF
```
**Expected:** Shows formatted markets list without errors.

### 4. Prediction Parser Module
```bash
python3 << 'EOF'
from predictor_parser import parse_predictions, _match_team

# Test exact match
matched = _match_team("Warriors", ("Warriors", "Suns"))
assert matched == "Warriors", f"Expected Warriors, got {matched}"
print("✅ Exact team match works")

# Test fuzzy match
matched = _match_team("Warroirs", ("Warriors", "Suns"))
assert matched == "Warriors", f"Fuzzy match failed"
print("✅ Fuzzy team matching works (typo tolerance)")

# Test comma-separated parsing
markets = [
    {"team_a": "Warriors", "team_b": "Suns"},
    {"team_a": "Celtics", "team_b": "Heat"}
]

predictions = parse_predictions("Warriors Yes, Heat No", markets)
assert len(predictions) == 2
assert predictions[0] == ("Warriors", "Yes")
assert predictions[1] == ("Heat", "No")
print("✅ Comma-separated parsing works")

# Test line-break parsing
predictions = parse_predictions("Warriors Yes\nHeat No", markets)
assert len(predictions) == 2
print("✅ Line-break parsing works")

# Test error handling
try:
    parse_predictions("Warriors", markets)  # Too few predictions
    print("❌ Should have raised ValueError for count mismatch")
except ValueError as e:
    print(f"✅ Correctly catches count mismatch: {e}")

print("\n✅ All parser tests passed!")
EOF
```
**Expected:** Shows all parser tests passing.

## Integration Tests

### Full Prediction Flow (Without API)
```bash
python3 << 'EOF'
import os
import sys
from datetime import datetime, timedelta
import sqlite3

# Setup test database
test_db = "test_integration.db"
if os.path.exists(test_db):
    os.remove(test_db)

# Temporarily override DB_PATH
import database
original_db = database.DB_PATH
database.DB_PATH = test_db

# Initialize
database.init_db()

# Save a test market (simulating what bot would do)
now = datetime.utcnow().isoformat()
database.save_market("market_123", "Warriors", "Suns", now, "active")
print("✅ Market saved to database")

# Get today's markets
todays = database.get_todays_markets()
print(f"✅ Retrieved {len(todays)} markets for today")

# Log a prediction
database.log_prediction(
    "market_123",
    now,
    "Warriors",
    "Suns",
    "Warriors",
    "Yes"
)
print("✅ Prediction logged")

# Get stats
stats = database.get_user_stats()
assert stats["total_predictions"] == 1
assert stats["wins"] == 0  # Not resolved yet
print(f"✅ Stats retrieved: {stats}")

# Update with resolution
database.update_market_result("market_123", "Yes", True)
print("✅ Market result updated")

# Check updated stats
stats = database.get_user_stats()
assert stats["wins"] == 1
print(f"✅ Win counted in stats: {stats}")

# Cleanup
database.DB_PATH = original_db
os.remove(test_db)

print("\n✅ All integration tests passed!")
EOF
```
**Expected:** All database operations complete successfully.

## Manual Testing Checklist

### Before Running Bot

- [ ] `.env` file exists with all required fields
- [ ] No extra spaces in `.env` values
- [ ] Python 3.10+ installed: `python3 --version`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] All Python files compile: `python3 -m py_compile *.py`

### Running the Bot

```bash
# Start the bot
python3 main.py
```

Wait for output:
```
INFO - Starting Kalshi NBA Playoffs Telegram Bot...
INFO - Database initialized
INFO - Scheduler started. Daily market fetch at XX:XX America/Phoenix
INFO - Starting bot polling...
```

### Telegram Bot Tests

1. **Start command:**
   - Send `/start` to bot
   - Should receive welcome message

2. **Help command:**
   - Send `/help` to bot
   - Should receive detailed instructions

3. **Stats command:**
   - Send `/stats` to bot
   - Should show empty stats (no predictions yet)

4. **Manual market sending (optional):**
   - Modify `SEND_TIME` in `.env` to 1 minute from now
   - Restart bot
   - Check Telegram within 2 minutes for markets message
   - Or wait until next scheduled time

### Prediction Logging Tests

Once markets are sent (or you force send them):

1. **Valid comma-separated prediction:**
   - Reply: `Team1 Yes, Team2 No`
   - Bot should confirm: "✅ Logged 2 predictions"

2. **Valid line-break prediction:**
   - Reply with predictions on separate lines
   - Bot should confirm logging

3. **Invalid prediction count:**
   - Send fewer predictions than markets
   - Bot should reply: "Expected N predictions, got M"

4. **Invalid team name:**
   - Send a team name not in the market
   - Bot should suggest correct names

5. **Invalid outcome:**
   - Send `Team Mayb` instead of `Team Yes`
   - Bot should reply: "Use 'Yes' or 'No' for each prediction"

## Debugging

### Enable Debug Logging
```bash
# Edit .env
DEBUG=True
LOG_LEVEL=DEBUG
```

### View Logs
```bash
tail -f logs/bot.log
```

### Test Kalshi API Connection
```bash
python3 << 'EOF'
from config import KALSHI_API_KEY, KALSHI_API_SECRET, KALSHI_BASE_URL
from kalshi_client import KalshiClient

try:
    client = KalshiClient(KALSHI_API_KEY, KALSHI_API_SECRET, KALSHI_BASE_URL)
    markets = client.get_playoff_markets()
    print(f"✅ Connected to Kalshi API")
    print(f"✅ Found {len(markets)} active NBA markets")
    if markets:
        print(f"   Example: {markets[0]}")
except Exception as e:
    print(f"❌ Kalshi API Error: {e}")
    print("\nTroubleshooting:")
    print("- Verify API credentials in .env")
    print("- Check internet connection")
    print("- Try https://sandbox.kalshi.com/v1 if in sandbox mode")
    print("- Check Kalshi API docs at https://kalshi.com/api-docs")
EOF
```

## Performance Testing

### Database Query Speed
```bash
python3 << 'EOF'
import time
from database import get_user_stats, get_todays_markets, get_unresolved_markets

# Time the queries
start = time.time()
stats = get_user_stats()
print(f"get_user_stats: {(time.time()-start)*1000:.1f}ms")

start = time.time()
markets = get_todays_markets()
print(f"get_todays_markets: {(time.time()-start)*1000:.1f}ms")

start = time.time()
unresolved = get_unresolved_markets()
print(f"get_unresolved_markets: {(time.time()-start)*1000:.1f}ms")

# All should be <100ms
EOF
```

## Continuous Testing

To test overnight:
1. Set `SEND_TIME=09:00` in `.env` (or your desired time)
2. Start bot with: `nohup python3 main.py > bot.log 2>&1 &`
3. Check `logs/bot.log` and `bot.log` periodically
4. Send test predictions when markets are sent
5. Verify stats update after markets resolve

## Test Matrix

| Component | Method | Expected Result |
|-----------|--------|-----------------|
| Config | Import | No errors |
| Database | Init | Tables created |
| Parser | Comma format | Predictions parsed |
| Parser | Line format | Predictions parsed |
| Parser | Fuzzy match | Typos tolerated |
| Bot | /start | Welcome message |
| Bot | /stats | Stats displayed |
| Scheduler | CronTrigger | Daily at set time |
| Kalshi | get_playoff_markets | Markets list returned |

All tests should complete in <5 seconds unless explicitly waiting for scheduled events.
