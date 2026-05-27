#!/usr/bin/env python3
"""
Telegram notification service for trading events.
Sends messages to Telegram when trades are detected and executed.
Handles incoming /stats and /trades commands via polling.
"""

import logging
import requests
import threading
import time
from typing import Optional
from signal_generator import TradeSignal

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send trading notifications and handle commands via Telegram."""

    def __init__(self, bot_token: str, chat_id: str, trading_engine=None):
        """
        Initialize Telegram notifier.

        Args:
            bot_token: Telegram bot token (from BotFather)
            chat_id: Telegram chat ID to send messages to
            trading_engine: Reference to TradingEngine for stats/trades queries
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self.get_updates_url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        self.trading_engine = trading_engine
        self.last_update_id = 0
        self.polling_active = False
        self.polling_thread = None

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

    def start_polling(self):
        """Start polling for incoming Telegram commands."""
        if self.polling_active:
            logger.warning("Telegram polling already active")
            return

        self.polling_active = True
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        logger.info("✓ Telegram command polling started")

    def stop_polling(self):
        """Stop polling for incoming Telegram commands."""
        self.polling_active = False
        if self.polling_thread:
            self.polling_thread.join(timeout=2)
        logger.info("Telegram command polling stopped")

    def _polling_loop(self):
        """Poll Telegram API for incoming messages every 2 seconds."""
        while self.polling_active:
            try:
                response = requests.get(
                    self.get_updates_url,
                    params={"offset": self.last_update_id + 1, "timeout": 1},
                    timeout=5
                )
                if response.status_code != 200:
                    time.sleep(2)
                    continue

                updates = response.json().get('result', [])
                for update in updates:
                    self.last_update_id = update.get('update_id', self.last_update_id)
                    self._handle_message(update)

                time.sleep(2)
            except Exception as e:
                logger.debug(f"Polling error: {e}")
                time.sleep(2)

    def _handle_message(self, update: dict):
        """Handle incoming Telegram message."""
        message = update.get('message', {})
        text = message.get('text', '').strip()

        if not text or not text.startswith('/'):
            return

        command = text.split()[0].lower()

        if command == '/stats':
            self._handle_stats_command()
        elif command == '/trades':
            self._handle_trades_command()
        elif command == '/help':
            self._handle_help_command()

    def _handle_stats_command(self):
        """Handle /stats command - show performance metrics."""
        if not self.trading_engine:
            self.send_message("⚠️ Trading engine not connected")
            return

        try:
            stats = self.trading_engine.get_performance_stats()
            message = f"""
📊 **PERFORMANCE STATS**

Total P&L: ${stats['total_pnl']:.2f}
Win Rate: {stats['win_rate']:.1f}%
Total Trades: {stats['total_trades']}
Winning Trades: {stats['winning_trades']}
Losing Trades: {stats['losing_trades']}

Avg Edge: {stats['avg_edge']:.1f}%
Avg Confidence: {stats['avg_confidence']:.0f}%
Avg Trade Size: ${stats['avg_size']:.2f}

Active Trades: {stats['active_trades']}
Resolved Trades: {stats['resolved_trades']}

Last Scan: {stats['last_scan']}
"""
            self.send_message(message)
        except Exception as e:
            logger.error(f"Error formatting stats: {e}")
            self.send_message(f"⚠️ Error fetching stats: {e}")

    def _handle_trades_command(self):
        """Handle /trades command - show active and recent resolved trades."""
        if not self.trading_engine:
            self.send_message("⚠️ Trading engine not connected")
            return

        try:
            trades_data = self.trading_engine.get_trades_summary()

            # Format active trades
            active_section = "**ACTIVE TRADES**\n"
            if trades_data['active']:
                for trade in trades_data['active'][:5]:
                    # Parse close_time if available
                    close_time_str = ""
                    if trade['close_time']:
                        try:
                            from datetime import datetime
                            close_dt = datetime.fromisoformat(trade['close_time'].replace('Z', '+00:00'))
                            close_time_str = f"\nResolves: {close_dt.strftime('%Y-%m-%d %H:%M UTC')}"
                        except:
                            close_time_str = f"\nResolves: {trade['close_time']}"

                    active_section += f"""
Market: {trade['ticker']}
City: {trade['city']}
Buckets: {trade['buckets']}
Entry: ${trade['notional']:.2f} @ {trade['entry_time']}{close_time_str}
Edge: {trade['edge']:.1f}% | Confidence: {trade['confidence']:.0f}%
---"""
            else:
                active_section += "No active trades"

            # Format resolved trades
            resolved_section = "\n**RECENT RESOLVED TRADES** (last 5)\n"
            if trades_data['resolved']:
                for trade in trades_data['resolved'][:5]:
                    pnl_symbol = "✅" if trade['pnl'] >= 0 else "❌"
                    resolved_section += f"""
{pnl_symbol} {trade['ticker']}
City: {trade['city']}
Entry: ${trade['notional']:.2f} | P&L: ${trade['pnl']:.2f}
Resolved: {trade['resolution_time']}
---"""
            else:
                resolved_section += "No resolved trades yet"

            message = f"{active_section}{resolved_section}"
            # Split if too long
            if len(message) > 4000:
                self.send_message(active_section)
                self.send_message(resolved_section)
            else:
                self.send_message(message)

        except Exception as e:
            logger.error(f"Error formatting trades: {e}")
            self.send_message(f"⚠️ Error fetching trades: {e}")

    def _handle_help_command(self):
        """Handle /help command."""
        message = """
📖 **AVAILABLE COMMANDS**

/stats - Show performance metrics (P&L, win rate, avg edge, etc.)
/trades - Show active trades and recent resolved trades
/help - Show this help message
"""
        self.send_message(message)
