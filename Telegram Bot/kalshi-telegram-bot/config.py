import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env file")

KALSHI_API_KEY = os.getenv("KALSHI_API_KEY", "")
KALSHI_API_SECRET = os.getenv("KALSHI_API_SECRET", "")
KALSHI_BASE_URL = os.getenv("KALSHI_BASE_URL", "https://api.kalshi.com/v1")

TIMEZONE = os.getenv("TIMEZONE", "America/Phoenix")
SEND_TIME = os.getenv("SEND_TIME", "09:00")

DB_PATH = os.getenv("DB_PATH", "./kalshi_predictions.db")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
