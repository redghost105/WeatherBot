import logging
import signal
import sys
from datetime import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import config
import database
from kalshi_client import KalshiClient
from bot import build_application

logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

scheduler = None
app = None
handlers = None

def parse_send_time(time_str: str):
    """Parse HH:MM time string into hour and minute."""
    try:
        hour, minute = map(int, time_str.split(":"))
        return hour, minute
    except (ValueError, IndexError):
        logger.error(f"Invalid SEND_TIME format: {time_str}. Using 09:00")
        return 9, 0

def scheduled_fetch_markets():
    """Scheduled job to fetch and send markets."""
    logger.info("Running scheduled market fetch...")
    try:
        import asyncio
        if handlers and app:
            asyncio.run(handlers.send_daily_markets(app.context))
    except Exception as e:
        logger.error(f"Error in scheduled market fetch: {e}")

def check_and_resolve_markets():
    """Scheduled job to check for resolved markets every 6 hours."""
    logger.info("Checking for resolved markets...")
    try:
        unresolved = database.get_unresolved_markets()
        if not unresolved:
            logger.debug("No unresolved markets to check")
            return

        kalshi_client = KalshiClient(
            config.KALSHI_API_KEY,
            config.KALSHI_API_SECRET,
            config.KALSHI_BASE_URL
        )

        for market_id in unresolved:
            result = kalshi_client.get_market_result(market_id)
            if result and result.get("status") in ["resolved", "finalized"]:
                result_outcome = result.get("result")
                win_loss = None

                if result_outcome:
                    conn = database.get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT predicted_outcome FROM predictions WHERE market_id = ? AND resolved = 0",
                        (market_id,)
                    )
                    for row in cursor.fetchall():
                        predicted_outcome = row[0]
                        if (result_outcome == "Yes" and predicted_outcome == "Yes") or \
                           (result_outcome == "No" and predicted_outcome == "No"):
                            win_loss = True
                        else:
                            win_loss = False
                        database.update_market_result(market_id, result_outcome, win_loss)
                    conn.close()

                logger.info(f"Updated market {market_id}: {result_outcome}")

    except Exception as e:
        logger.error(f"Error checking resolved markets: {e}")

def setup_scheduler():
    """Set up BackgroundScheduler with timezone-aware jobs."""
    global scheduler

    tz = pytz.timezone(config.TIMEZONE)
    hour, minute = parse_send_time(config.SEND_TIME)

    scheduler = BackgroundScheduler(timezone=tz)

    cron_trigger = CronTrigger(hour=hour, minute=minute, timezone=tz)
    scheduler.add_job(
        scheduled_fetch_markets,
        trigger=cron_trigger,
        id="fetch_markets",
        name="Fetch daily markets"
    )

    scheduler.add_job(
        check_and_resolve_markets,
        trigger="interval",
        hours=6,
        id="check_resolved",
        name="Check for resolved markets"
    )

    scheduler.start()
    logger.info(f"Scheduler started. Daily market fetch at {config.SEND_TIME} {config.TIMEZONE}")

def shutdown_handler(signum, frame):
    """Handle graceful shutdown."""
    logger.info("Shutdown signal received")
    if scheduler:
        scheduler.shutdown()
    sys.exit(0)

def main():
    """Main function to run the bot."""
    global app, handlers

    logger.info("Starting Kalshi NBA Playoffs Telegram Bot...")

    database.init_db()
    logger.info("Database initialized")

    kalshi_client = KalshiClient(
        config.KALSHI_API_KEY,
        config.KALSHI_API_SECRET,
        config.KALSHI_BASE_URL
    )

    app, handlers = build_application(config.TELEGRAM_BOT_TOKEN, kalshi_client)

    setup_scheduler()

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logger.info("Starting bot polling...")
    app.run_polling()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
