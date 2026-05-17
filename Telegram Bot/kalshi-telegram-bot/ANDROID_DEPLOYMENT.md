# Android (Termux) Deployment Guide

Run the Kalshi bot 24/7 on your Android device using Termux.

## Prerequisites

- Android device (any modern phone/tablet)
- Internet connection (WiFi or mobile data)
- ~200MB free storage
- ~50MB RAM available

## Step 1: Install Termux

1. Download Termux from F-Droid (recommended): https://f-droid.org/en/packages/com.termux/
   - OR from Google Play Store: https://play.google.com/store/apps/details?id=com.termux
2. Install and open the app
3. You should see a terminal prompt: `$ `

## Step 2: Install Python and Dependencies

Copy-paste these commands into Termux:

```bash
# Update package list
apt update

# Install Python 3
apt install -y python3

# Install pip and required build tools
apt install -y python3-pip git

# Verify installation
python3 --version
pip3 --version
```

## Step 3: Download the Bot

Option A: Clone from git (if available):
```bash
cd ~
git clone <repo_url> kalshi-bot
cd kalshi-bot
```

Option B: Copy files manually
1. On your computer, zip the `kalshi-telegram-bot` directory
2. Transfer via email, cloud storage, or USB
3. In Termux:
```bash
# Unzip (you may need: apt install unzip)
cd ~
unzip kalshi-telegram-bot.zip
cd kalshi-telegram-bot
```

## Step 4: Install Python Dependencies

```bash
pip3 install -r requirements.txt
```

This installs:
- python-telegram-bot
- requests
- python-dotenv
- apscheduler
- pytz
- fuzzywuzzy
- python-Levenshtein

Takes ~2-5 minutes depending on connection.

## Step 5: Configure Environment

Create `.env` file with your credentials:

```bash
# Create .env file
cat > .env << 'EOF'
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
KALSHI_API_KEY=your_key_here
KALSHI_API_SECRET=your_secret_here
KALSHI_BASE_URL=https://api.kalshi.com/v1
TIMEZONE=America/Phoenix
SEND_TIME=09:00
DB_PATH=./kalshi_predictions.db
LOG_LEVEL=INFO
DEBUG=False
EOF
```

Replace the values with your actual credentials.

## Step 6: Test the Bot

```bash
# Run the bot
python3 main.py
```

You should see:
```
INFO - Starting Kalshi NBA Playoffs Telegram Bot...
INFO - Database initialized
INFO - Scheduler started...
INFO - Starting bot polling...
```

Send `/start` to your Telegram bot. You should receive the welcome message.

**To stop:** Press `Ctrl+C`

## Step 7: Keep Bot Running 24/7

Termux sessions close when you exit the app. Use one of these methods:

### Option A: Termux:Boot (Recommended)

1. Install Termux:Boot addon: https://play.google.com/store/apps/details?id=com.termux.boot
2. Grant it device admin permissions in settings
3. Create boot script:
```bash
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/start-bot << 'EOF'
#!/bin/bash
cd ~/kalshi-telegram-bot
nohup python3 main.py > bot.log 2>&1 &
EOF

chmod +x ~/.termux/boot/start-bot
```
4. Reboot device
5. Bot starts automatically in background

### Option B: Keep Termux Running

1. Open Termux
2. Run: `python3 main.py`
3. Lock screen (bot keeps running if "Run in background" is enabled)
4. In Termux settings: Enable "Run in background"

### Option C: Use Screen/Tmux

```bash
# Install screen
apt install -y screen

# Start bot in screen session
screen -dmS kalshi-bot python3 main.py

# To check: screen -ls
# To attach: screen -r kalshi-bot
# To detach: Ctrl+A then D
```

### Option D: Create a Start Script

```bash
cat > start_bot.sh << 'EOF'
#!/bin/bash
cd ~/kalshi-telegram-bot
nohup python3 main.py >> logs/bot.log 2>&1 &
echo "Bot started. Check logs/bot.log for status."
EOF

chmod +x start_bot.sh

# Run: ./start_bot.sh
```

## Monitoring

### Check Bot Status

```bash
# View recent logs
tail logs/bot.log

# View live logs
tail -f logs/bot.log
```

### Check Running Processes

```bash
# List Python processes
ps aux | grep python3

# Stop bot
killall python3  # stops all Python processes
```

### Check Database

```bash
# View prediction count
python3 << 'EOF'
from database import get_user_stats
stats = get_user_stats()
print(f"Total predictions: {stats['total_predictions']}")
print(f"Wins: {stats['wins']}")
print(f"Accuracy: {stats['accuracy']}%")
EOF
```

## Troubleshooting

### Bot Crashes on Startup

**Error:** `ModuleNotFoundError: No module named 'telegram'`
```bash
# Reinstall dependencies
pip3 install -r requirements.txt
```

**Error:** `TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set`
```bash
# Check .env file exists
cat .env

# Verify no missing values
# If .env is wrong, edit it:
nano .env  # or: vi .env
```

### Bot Doesn't Send Markets at 9 AM

**Check timezone:**
```bash
python3 << 'EOF'
import pytz
print("System timezone tests:")
print("Current timezone:", pytz.timezone('America/Phoenix'))
from config import TIMEZONE
print("Bot timezone:", TIMEZONE)
EOF
```

**Check time format:**
- Ensure SEND_TIME is in 24-hour format (HH:MM)
- Example: 09:00 for 9 AM, 17:30 for 5:30 PM

### Database Grows Too Large

```bash
# Check size
du -h kalshi_predictions.db

# Archive and clean old data (2026-05-06+)
sqlite3 kalshi_predictions.db << 'EOF'
DELETE FROM predictions WHERE DATE(prediction_timestamp) < DATE('now', '-90 days');
VACUUM;
EOF
```

### Device Runs Out of Storage

```bash
# Check storage
df -h

# Reduce log size
rm logs/bot.log
```

## Performance Tips

1. **Battery:** Disable WiFi/mobile data scanning in settings (reduces wake-ups)
2. **Heat:** Keep device cool; disable high-performance mode
3. **Memory:** Close other apps before running bot
4. **Network:** Use WiFi if available (faster, cheaper)
5. **Logging:** Set `LOG_LEVEL=WARNING` to reduce disk usage

## Update the Bot

```bash
# Stop current bot (Ctrl+C or killall python3)

# Get new files
# Option 1: git pull (if cloned from git)
git pull

# Option 2: Re-download and unzip

# Restart
python3 main.py
```

## Backup Predictions

Before updating, backup your data:

```bash
# Create backup
cp kalshi_predictions.db kalshi_predictions.db.backup

# Email the backup or upload to cloud
```

## Remote Monitoring (Optional)

For true 24/7 without keeping app open, consider:

1. **Cloud Server (AWS/DigitalOcean):** Deploy on a $5/month server instead
2. **Home Server:** Use a Raspberry Pi or old computer running Linux
3. **GitHub Actions:** Use free CI/CD to run bot (limited by action minutes)

See `README.md` "Deployment" section for cloud options.

## Keep Device Awake

Add to Termux startup:

```bash
apt install -y wakelock

# Enable wakelock
wakelock acquire

# Disable when not needed
wakelock release
```

## Logs Location

- **Termux logs:** `~/kalshi-telegram-bot/logs/bot.log`
- **Nohup logs:** `~/kalshi-telegram-bot/nohup.out` (if running with nohup)

## Testing Before 24/7 Run

```bash
# 1. Test parser
python3 test_parser.py

# 2. Test database
python3 test_database.py

# 3. Test Kalshi connection
python3 test_kalshi.py

# 4. Run bot for 1 hour manually
python3 main.py

# 5. Check logs
cat logs/bot.log
```

## Summary

Quick checklist:
- [ ] Termux installed
- [ ] Python 3 installed
- [ ] Dependencies installed (`pip3 install -r requirements.txt`)
- [ ] `.env` file configured with credentials
- [ ] Bot tested manually (`python3 main.py`)
- [ ] Bot set to run on boot (Termux:Boot or screen)
- [ ] Logs monitored (`tail -f logs/bot.log`)
- [ ] Device configured to stay awake

The bot should now run 24/7 on your Android device!

For issues, check `logs/bot.log` or refer to `TESTING.md` for debugging steps.
