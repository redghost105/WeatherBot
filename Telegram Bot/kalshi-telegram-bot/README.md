# Kalshi NBA Playoffs Telegram Bot

A Telegram bot that fetches active NBA Playoffs prediction markets from the Kalshi API, sends them daily, and logs user predictions to a SQLite database for performance tracking.

## Features

- **Daily Market Fetch**: Automatically fetches active NBA Playoffs markets from Kalshi at 9 AM MST
- **Flexible Prediction Input**: Accepts predictions in comma-separated or line-break formats
- **SQLite Tracking**: Logs all predictions with team names, outcomes, and timestamps
- **Performance Stats**: View your prediction accuracy with `/stats` command
- **Market Resolution**: Periodically checks for resolved markets and updates prediction results
- **Error Handling**: Clear, actionable error messages for invalid inputs
- **Fuzzy Team Matching**: Tolerates team name typos and variations

## Setup

### Prerequisites

- Python 3.10+
- A Telegram bot token (get from @BotFather)
- Kalshi API credentials (register at https://www.kalshi.com)

### Installation

1. Clone or download the project to your device.

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file from the template:
   ```bash
   cp .env.example .env
   ```

4. Edit `.env` with your credentials:
   - `TELEGRAM_BOT_TOKEN`: Get from @BotFather
   - `TELEGRAM_CHAT_ID`: Your chat ID (find with @userinfobot)
   - `KALSHI_API_KEY` and `KALSHI_API_SECRET`: From Kalshi account settings
   - Other settings as needed (timezone, send time, etc.)

### Running the Bot

```bash
python main.py
```

The bot will:
- Initialize the database
- Start the scheduler for daily 9 AM MST market fetches
- Begin listening for Telegram messages

## Usage

### Commands

- `/start` - Welcome message with instructions
- `/help` - Display detailed usage instructions
- `/stats` - View your prediction accuracy and streaks

### Prediction Format

Reply to market messages in either format:

**Comma-separated:**
```
Warriors Yes, Heat No, Lakers Yes
```

**Line-break separated:**
```
Warriors Yes
Heat No
Lakers Yes
```

Team names are fuzzy-matched, so "Warriors" works for "Golden State Warriors".

## Database Schema

### `predictions` table
- `market_id`: Kalshi market UUID
- `market_date`: When the market was sent
- `team_a`, `team_b`: The two teams in the matchup
- `predicted_team`: Which team you predicted
- `predicted_outcome`: "Yes" or "No"
- `prediction_timestamp`: When you submitted the prediction
- `resolved`: Whether the market has resolved (0/1)
- `result_outcome`: The actual market outcome ("Yes"/"No")
- `win_loss`: Whether your prediction was correct (True/False)

### `markets` table
- `market_id`: Unique market identifier
- `team_a`, `team_b`: Teams in the matchup
- `sent_date`: When the market was sent to chat
- `kalshi_status`: Market status from Kalshi API

## Configuration

All configuration is via environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| TELEGRAM_BOT_TOKEN | (required) | Telegram bot token |
| TELEGRAM_CHAT_ID | (required) | Chat to send markets to |
| KALSHI_API_KEY | (required) | Kalshi API key |
| KALSHI_API_SECRET | (required) | Kalshi API secret |
| KALSHI_BASE_URL | https://api.kalshi.com/v1 | Kalshi API endpoint |
| TIMEZONE | America/Phoenix | Timezone for scheduling |
| SEND_TIME | 09:00 | Daily send time (HH:MM) |
| DB_PATH | ./kalshi_predictions.db | SQLite database file |
| LOG_LEVEL | INFO | Logging verbosity |
| DEBUG | False | Debug mode |

## Deployment

### Local Machine / Android (Termux)

1. Install Python and required packages
2. Copy bot files to your device
3. Create `.env` with your credentials
4. Run `python main.py` in a terminal session or use a process manager

### Cloud Server (AWS EC2, etc.)

1. Launch a small Linux instance (t2.micro is sufficient)
2. Install Python 3.10+
3. Clone the repository
4. Create `.env` file
5. Use systemd service or supervisor to keep the bot running

**Example systemd service** (`/etc/systemd/system/kalshi-bot.service`):
```ini
[Unit]
Description=Kalshi Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/kalshi-telegram-bot
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable kalshi-bot
sudo systemctl start kalshi-bot
```

## Error Handling

The bot handles several error scenarios:

- **Invalid prediction count**: "Expected N predictions, got M"
- **Missing team name**: "Did you mean X or Y?"
- **Invalid outcome**: "Use 'Yes' or 'No' for each prediction"
- **No markets today**: "No markets sent today yet. Check back at 9 AM MST"
- **API failures**: Logged with retry logic; user notified

## Troubleshooting

### Bot doesn't send markets at scheduled time
- Check `TIMEZONE` is a valid pytz timezone
- Verify `SEND_TIME` format is HH:MM (24-hour)
- Check logs in `logs/bot.log`

### Predictions not logging
- Ensure `/env` has all required fields
- Check database permissions on `DB_PATH` directory
- Verify chat has sent markets today (check in Telegram)

### "Invalid Kalshi API credentials"
- Generate new API key/secret from Kalshi account settings
- Verify values in `.env` have no extra spaces
- Try sandbox URL first to test

### Database corruption
- Stop the bot
- Delete `kalshi_predictions.db`
- Restart bot (will recreate database)
- Note: This will lose all historical predictions

## Future Enhancements

- Live betting mode (place actual bets via Kalshi API)
- Multiple market categories (NFL, MLB, etc.)
- Confidence levels in predictions
- Admin commands for reset/export
- Web dashboard for stats
- Notifications on market resolution
- CSV bulk import of markets

## License

This project is provided as-is for personal use.

## Support

For issues with:
- **Telegram Bot API**: See https://core.telegram.org/bots/api
- **Kalshi API**: See https://kalshi.com/api-docs
- **APScheduler**: See https://apscheduler.readthedocs.io
