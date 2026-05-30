import os
import requests
from dotenv import load_dotenv

load_dotenv()

class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.bot_token and self.chat_id)

    def _send_message(self, text):
        """Send message via Telegram Bot API."""
        if not self.enabled:
            return

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
        }

        try:
            requests.post(url, json=data, timeout=10)
        except Exception as e:
            print(f"Telegram send error: {e}")

    def notify_trade_placed(self, mode, city, target_date, bins, stakes):
        """Alert when trade is placed."""
        if not self.enabled:
            return

        bin_str = ", ".join([f"${int(b['bin_low'])}-{int(b['bin_high'])}" for b in bins])
        stake_str = ", ".join([f"${s:.2f}" for s in stakes])

        text = (
            f"<b>{mode.upper()} TRADE PLACED</b>\n"
            f"City: {city}\n"
            f"Date: {target_date}\n"
            f"Bins: {bin_str}\n"
            f"Stakes: {stake_str}"
        )
        self._send_message(text)

    def notify_trade_resolved(self, city, bin_range, won, pnl):
        """Alert when trade resolves."""
        if not self.enabled:
            return

        status = "WON" if won else "LOST"
        color = "✅" if won else "❌"

        text = (
            f"{color} <b>TRADE RESOLVED: {status}</b>\n"
            f"City: {city}\n"
            f"Bin: {bin_range}\n"
            f"PnL: ${pnl:+.2f}"
        )
        self._send_message(text)

    def notify_daily_summary(self, wins, losses, stake, pnl, roi):
        """Send daily summary."""
        if not self.enabled:
            return

        win_rate = wins / (wins + losses) * 100 if wins + losses > 0 else 0

        text = (
            f"<b>📊 DAILY SUMMARY</b>\n"
            f"Record: {wins}W - {losses}L\n"
            f"Win Rate: {win_rate:.1f}%\n"
            f"Total Stake: ${stake:.2f}\n"
            f"PnL: ${pnl:+.2f}\n"
            f"ROI: {roi:+.1f}%"
        )
        self._send_message(text)


if __name__ == "__main__":
    notifier = TelegramNotifier()
    print(f"Telegram enabled: {notifier.enabled}")

    # Test messages (will only send if tokens are set)
    notifier.notify_trade_placed(
        "paper",
        "NYC",
        "2026-05-30",
        [{"bin_low": 56, "bin_high": 57}, {"bin_low": 57, "bin_high": 58}],
        [2.0, 2.0]
    )
    notifier.notify_trade_resolved("NYC", "56-57°F", True, 14.0)
    notifier.notify_daily_summary(5, 2, 18, 12, 66.7)
