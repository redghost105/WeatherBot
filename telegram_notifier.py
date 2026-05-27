#!/usr/bin/env python3
"""
Telegram notification service for trading events.
Sends messages to Telegram when trades are detected and executed.
"""

import logging
import requests
from typing import Optional
from signal_generator import TradeSignal

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send trading notifications to Telegram."""

    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier.

        Args:
            bot_token: Telegram bot token (from BotFather)
            chat_id: Telegram chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    def send_message(self, message: str) -> bool:
        """Send a message to Telegram chat."""
        try:
            response = requests.post(
                self.api_url,
                json={"chat_id": self.chat_id, "text": message},
                timeout=5
            )
            if response.status_code == 200:
                logger.debug(f"Telegram message sent successfully")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def notify_signal_detected(self, signal: TradeSignal) -> bool:
        """Notify when a trading signal is detected."""
        message = f"""
🎯 **SIGNAL DETECTED**

Market: {signal.market_ticker}
City: {signal.city_name}
Buckets: {', '.join(signal.target_buckets)}

Edge: {signal.edge_pct:.1f}%
Confidence: {signal.confidence:.0f}%
Notional: ${signal.total_notional:.2f}

Status: Awaiting validation...
"""
        return self.send_message(message)

    def notify_trade_executed(
        self,
        signal: TradeSignal,
        num_orders: int,
        mode: str = "PAPER"
    ) -> bool:
        """Notify when a trade is executed."""
        message = f"""
✅ **TRADE EXECUTED**

Market: {signal.market_ticker}
City: {signal.city_name}
Buckets: {', '.join(signal.target_buckets)}

Edge: {signal.edge_pct:.1f}%
Confidence: {signal.confidence:.0f}%
Size: ${signal.total_notional:.2f}
Orders: {num_orders}

Mode: [{mode}]
Reasoning: {signal.reasoning}
"""
        return self.send_message(message)

    def notify_validation_failed(self, signal: TradeSignal, reason: str) -> bool:
        """Notify when a signal fails validation."""
        message = f"""
❌ **SIGNAL REJECTED**

Market: {signal.market_ticker}
City: {signal.city_name}

Reason: {reason}
Edge: {signal.edge_pct:.1f}%
Confidence: {signal.confidence:.0f}%
"""
        return self.send_message(message)

    def notify_error(self, error_message: str) -> bool:
        """Notify about errors in the trading system."""
        message = f"""
⚠️ **TRADING ERROR**

{error_message}
"""
        return self.send_message(message)
