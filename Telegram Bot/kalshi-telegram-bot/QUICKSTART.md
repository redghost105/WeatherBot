# Quick Start Guide

## 5-Minute Setup

### Step 1: Get Your Credentials

**Telegram Bot Token:**
1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Follow prompts, choose a name and username
4. Copy the token you receive (looks like `123456789:ABCDefGhIjKlMnOpQrStUvWxYz`)

**Your Chat ID:**
1. Search for `@userinfobot` in Telegram
2. Send it any message
3. It will reply with your User ID
4. Use this as `TELEGRAM_CHAT_ID`

**Kalshi API Credentials:**
1. Go to https://www.kalshi.com
2. Register or sign in
3. Go to Account Settings → API
4. Generate API Key and Secret
5. Copy both (keep secret!)

### Step 2: Install and Configure

```bash
# Navigate to the bot directory
cd /home/carter/claude_programs/Polymarket/Telegram\ Bot/kalshi-telegram-bot

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Fill in these required fields:
```
TELEGRAM_BOT_TOKEN=your_token_from_BotFather
TELEGRAM_CHAT_ID=your_chat_id_from_userinfobot
KALSHI_API_KEY=your_kalshi_api_key
KALSHI_API_SECRET=your_kalshi_api_secret
```

### Step 3: Run the Bot

```bash
python main.py
```

You should see:
```
INFO - Starting Kalshi NBA Playoffs Telegram Bot...
INFO - Database initialized
INFO - Scheduler started. Daily market fetch at 09:00 America/Phoenix
INFO - Starting bot polling...
```

### Step 4: Test It

1. Open Telegram and find your bot (search by username from step 1)
2. Send `/start`
3. Bot responds with welcome message
4. Send `/help` for usage instructions
5. Send `/stats` to see empty stats

### To Test Market Sending

Option A: Wait until 9 AM MST to see markets automatically sent.

Option B: Temporarily modify `SEND_TIME` in `.env` to 1 minute from now:
```
SEND_TIME=14:32  # Set to current time + 1 minute
```
Restart bot, watch for message in Telegram within 1 minute.

## Using the Bot

Once markets are sent (daily at 9 AM MST):

1. **Reply with predictions:**
   ```
   Warriors Yes, Heat No, Lakers Yes
   ```
   or
   ```
   Warriors Yes
   Heat No
   Lakers Yes
   ```

2. **Bot confirms:**
   ```
   ✅ Logged 3 predictions:
   1. Warriors — Yes
   2. Heat — No
   3. Lakers — Yes
   ```

3. **Check your stats:**
   ```
   /stats
   ```

4. **Markets resolve in 2-7 days** - bot checks every 6 hours and updates results

5. **Your accuracy** is calculated once markets resolve

## Common Issues

### "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set"
- Check `.env` file exists in the same directory as `main.py`
- Verify you copied credentials correctly (no extra spaces)

### Bot runs but sends nothing at 9 AM
- Check `logs/bot.log` for errors
- Verify `TIMEZONE=America/Phoenix` matches your intended timezone
- Verify `SEND_TIME=09:00` is in 24-hour format

### "No markets found" on first run
- This is normal if no NBA Playoffs are happening
- The bot will still run but won't have markets to send
- Try again during playoff season

### Permission denied on `kalshi_predictions.db`
- Check write permissions: `chmod 644 kalshi_predictions.db`
- Or delete and let bot recreate it

## Next Steps

- Read `README.md` for full documentation
- Check `logs/bot.log` to monitor bot activity
- Set up a process manager (systemd/supervisor) for continuous running on a server
- Deploy to Android (Termux) or AWS for 24/7 operation

## Getting Help

If something doesn't work:
1. Check `logs/bot.log` for error messages
2. Verify `.env` has all required fields with no extra spaces
3. Make sure Kalshi API credentials are correct (try Sandbox first)
4. Check that your timezone is a valid pytz timezone: `python -c "import pytz; print(pytz.common_timezones)"`
