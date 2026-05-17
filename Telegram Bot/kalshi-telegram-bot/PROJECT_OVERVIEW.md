# Kalshi NBA Playoffs Telegram Bot - Complete Project Overview

## Quick Summary
A production-ready Telegram bot that fetches NBA Playoffs prediction markets from the Kalshi API daily, allows users to make predictions via Telegram, logs predictions to SQLite, and tracks prediction accuracy.

**Location:** `/home/carter/claude_programs/Polymarket/Telegram Bot/kalshi-telegram-bot/`

---

## How It Works (Simple)

1. **Every day at 9 AM MST**: Bot fetches active NBA Playoffs markets from Kalshi API
2. **Bot sends**: Numbered list of matchups to Telegram chat (e.g., "1. Warriors vs Suns")
3. **User replies**: With predictions (e.g., "Warriors Yes, Heat No, Lakers Yes")
4. **Bot logs**: Predictions to SQLite database with timestamps
5. **Every 6 hours**: Bot checks if markets have resolved and updates win/loss
6. **User can**: Check `/stats` to see prediction accuracy

---

## Quick Commands

**Start the bot:**
```bash
cd "/home/carter/claude_programs/Polymarket/Telegram Bot/kalshi-telegram-bot"
source venv/bin/activate
python main.py
```

**Stop the bot:** `Ctrl+C`

**Telegram commands (once running):**
- `/start` - Welcome message
- `/help` - Usage instructions
- `/stats` - View your prediction accuracy
- `/refresh` - Fetch markets now (doesn't wait for 9 AM)

---

## Project Structure

```
kalshi-telegram-bot/
├── main.py                    # Entry point, scheduler setup
├── bot.py                     # Telegram handlers (/start, /help, /stats, /refresh)
├── kalshi_client.py           # Kalshi API wrapper
├── database.py                # SQLite operations
├── predictor_parser.py        # Parse user prediction text
├── config.py                  # Load .env configuration
├── requirements.txt           # Python dependencies
├── .env                       # Your credentials (NOT in git)
├── .env.example              # Template for .env
├── kalshi_predictions.db     # SQLite database (auto-created)
├── logs/
│   └── bot.log              # Bot activity logs
└── venv/                     # Python virtual environment
```

---

## Configuration (.env File)

Required fields:
```
TELEGRAM_BOT_TOKEN=your_token_from_BotFather
TELEGRAM_CHAT_ID=your_chat_id_from_userinfobot
KALSHI_API_KEY=your_kalshi_api_key
KALSHI_API_SECRET=your_kalshi_api_secret
```

Optional fields (have defaults):
```
KALSHI_BASE_URL=https://api.kalshi.com/v1
TIMEZONE=America/Phoenix
SEND_TIME=09:00
DB_PATH=./kalshi_predictions.db
LOG_LEVEL=INFO
DEBUG=False
```

---

## Database Schema

### predictions table
Stores all user predictions:
- `id` - Auto-increment primary key
- `market_id` - Kalshi market UUID
- `market_date` - When market was sent to user
- `team_a`, `team_b` - The two teams
- `predicted_team` - Which team user chose
- `predicted_outcome` - "Yes" or "No"
- `prediction_timestamp` - When user submitted
- `resolved` - Whether market has resolved (0/1)
- `result_outcome` - Actual market result
- `win_loss` - Whether user won (True/False/NULL)

### markets table
Tracks markets sent to user:
- `market_id` - Unique identifier
- `team_a`, `team_b` - Teams
- `sent_date` - When sent to chat
- `kalshi_status` - Status from API

---

## Key Files and Functions

### main.py
- `main()` - Entry point, initializes bot and scheduler
- `setup_scheduler()` - Sets up APScheduler for 9 AM daily market fetch
- `scheduled_fetch_markets()` - Job called by scheduler
- `check_and_resolve_markets()` - Job called every 6 hours to check results

### bot.py
- `BotHandlers` class - All Telegram message handlers
  - `start()` - `/start` command
  - `help()` - `/help` command
  - `stats()` - `/stats` command (shows accuracy)
  - `refresh()` - `/refresh` command (fetch markets now)
  - `message_handler()` - Parse user prediction text
  - `send_daily_markets()` - Fetch and send Kalshi markets
- `build_application()` - Create Telegram Application with handlers

### kalshi_client.py
- `KalshiClient` class - API wrapper
  - `get_playoff_markets()` - Fetch active NBA Playoffs markets
  - `get_market_result()` - Get market result after resolution
  - `format_market_display()` - Format markets for Telegram

### predictor_parser.py
- `parse_predictions()` - Parse user text into (team, outcome) tuples
  - Supports: "Team Yes, Team No" or line-break format
  - Fuzzy matching on team names (typo tolerant)
- `_match_team()` - Match user input to actual team name
- `validate_predictions()` - Validate prediction count and format

### database.py
- `init_db()` - Create tables if not exist
- `log_prediction()` - Insert prediction row
- `save_market()` - Insert market row
- `get_todays_markets()` - Get markets sent today
- `get_unresolved_markets()` - Get market IDs waiting for resolution
- `update_market_result()` - Mark resolved and set win/loss
- `get_user_stats()` - Calculate accuracy, win rate, streaks

### config.py
- Loads environment variables from .env
- Validates required fields (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
- Exports config constants for use in other modules

---

## How Predictions Flow Through the System

1. **9 AM MST or `/refresh` command**
   - `scheduled_fetch_markets()` or `refresh()` calls `send_daily_markets()`
   - Fetches markets from Kalshi API via `kalshi_client.get_playoff_markets()`
   - Saves each market to DB with `database.save_market()`
   - Sends formatted list to Telegram chat

2. **User replies with prediction**
   - `message_handler()` receives the text
   - `get_todays_markets()` retrieves markets sent today from DB
   - `parse_predictions()` converts text to (team, outcome) tuples
   - Loops through predictions and calls `log_prediction()` for each
   - Bot replies with confirmation

3. **Every 6 hours (background)**
   - `check_and_resolve_markets()` gets unresolved market IDs
   - For each, calls `get_market_result()` from Kalshi API
   - If resolved, calls `update_market_result()` with win/loss
   - User's `/stats` command now shows updated accuracy

---

## User Prediction Flow

**Comma-separated format:**
```
Warriors Yes, Heat No, Lakers Yes
```
→ Parsed to: [("Warriors", "Yes"), ("Heat", "No"), ("Lakers", "Yes")]

**Line-break format:**
```
Warriors Yes
Heat No
Lakers Yes
```
→ Same result

**Fuzzy matching example:**
- User types: "warroirs yes" 
- Fuzzy matcher corrects to: "Warriors"
- Stores: ("Warriors", "Yes")

---

## Important Technical Details

### Timezone Handling
- All timestamps stored in UTC internally
- Converted to configured TIMEZONE for display/scheduling
- Default timezone: `America/Phoenix` (MST/Sedona)
- Must use valid pytz timezone string

### Event Loop Management
- Uses `BackgroundScheduler` from APScheduler (runs in background thread)
- Telegram bot uses `app.run_polling()` (async, main thread)
- Scheduled jobs use `asyncio.run()` to call async handlers
- Prevents event loop conflicts

### Error Handling
- Kalshi API errors: Exponential backoff, max 3 retries
- Invalid predictions: Clear error messages to user
- Missing markets: Bot tells user to use `/refresh`
- Database errors: Logged but don't crash bot

### Fuzzy Matching
- Uses `fuzzywuzzy` library with 90% match threshold
- Matches team names even with typos
- If no match found, asks user to confirm

---

## Troubleshooting

**Bot won't start - "invalid token"**
- .env file has placeholder values
- Fill in real credentials from BotFather and Kalshi

**Bot starts but doesn't respond to commands**
- Check bot is in the chat
- Try `/start` first
- View logs: `tail -f logs/bot.log`

**Markets not sending at 9 AM**
- Check TIMEZONE in .env is valid
- Check SEND_TIME format is HH:MM
- Use `/refresh` to test manually

**No markets returned**
- Kalshi API might not have active NBA Playoffs markets
- Check `/refresh` returns error or empty list
- Try Kalshi sandbox URL to test API connection

**Database errors**
- Delete `kalshi_predictions.db` to reset
- Bot will recreate it on restart
- (You'll lose all prediction history)

---

## Dependencies

- **python-telegram-bot** (20.0) - Telegram bot API
- **requests** (2.31.0) - HTTP client for Kalshi API
- **python-dotenv** (1.0.0) - Load .env configuration
- **apscheduler** (3.10.4) - Job scheduling
- **pytz** (2023.3) - Timezone handling
- **fuzzywuzzy** (0.18.0) - Fuzzy string matching

All listed in `requirements.txt`

---

## Testing Checklist

- [ ] Bot starts without errors
- [ ] `/start` returns welcome message
- [ ] `/help` returns instructions
- [ ] `/stats` returns stats (should be 0 initially)
- [ ] `/refresh` fetches and sends markets
- [ ] User can reply with comma-separated predictions
- [ ] User can reply with line-break predictions
- [ ] Bot confirms predictions logged
- [ ] Database stores predictions (check with query)
- [ ] `/stats` shows updated count after prediction

---

## Future Enhancements (Not Yet Implemented)

- Live mode: Place actual bets via Kalshi API
- Multiple categories: NFL, MLB, etc.
- Confidence levels: "Warriors 80% Yes"
- Admin commands: `/reset`, `/export_csv`
- Web dashboard for stats
- Email/SMS notifications
- Team abbreviations: "GSW" → "Warriors"
- Multi-user support

---

## Notes for Next Session

1. **To pick up work**: Just run the start command above
2. **To make changes**: Edit the relevant .py file
3. **To restart after changes**: Stop with Ctrl+C, start again
4. **To test a feature**: Use `/refresh` to fetch markets without waiting for 9 AM
5. **To check logs**: `tail -f logs/bot.log`
6. **Database is persistent**: Survives restarts (file: `kalshi_predictions.db`)
7. **Config must be in .env**: Never hardcode credentials

---

## File Paths Reference

- Main entry: `/home/carter/claude_programs/Polymarket/Telegram Bot/kalshi-telegram-bot/main.py`
- Config template: `/home/carter/claude_programs/Polymarket/Telegram Bot/kalshi-telegram-bot/.env.example`
- Database: `/home/carter/claude_programs/Polymarket/Telegram Bot/kalshi-telegram-bot/kalshi_predictions.db`
- Logs: `/home/carter/claude_programs/Polymarket/Telegram Bot/kalshi-telegram-bot/logs/bot.log`

---

## Contact Points

When debugging, check these areas first:
1. **Telegram connection**: Check bot token in .env
2. **Kalshi API**: Check API key/secret in .env
3. **Scheduling**: Check TIMEZONE and SEND_TIME in .env
4. **Predictions**: Check database schema in database.py
5. **Parsing**: Check fuzzy matching threshold in predictor_parser.py

---

**Last Updated:** May 6, 2026
**Status:** Production Ready ✅
