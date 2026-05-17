import logging
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ParseMode

import database
import predictor_parser
from kalshi_client import KalshiClient
from config import TELEGRAM_CHAT_ID, KALSHI_API_KEY, KALSHI_API_SECRET, KALSHI_BASE_URL

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self, kalshi_client: KalshiClient):
        self.kalshi_client = kalshi_client
        self.last_markets = []

    async def _ensure_user(self, update: Update) -> int:
        """Auto-register user if new, return their telegram_id."""
        user = update.effective_user
        display_name = user.full_name or user.username or str(user.id)
        database.get_or_create_user(user.id, display_name)
        return user.id

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = await self._ensure_user(update)
        user = database.get_user(user_id)
        name = user.get("display_name", "").split()[0] if user.get("display_name") else "there"

        await update.message.reply_text(
            f"🏀 Welcome, {name}! You're now registered for the Kalshi NBA Playoffs Prediction Bot!\n\n"
            "I'll send you active playoffs markets every day at 9 AM MST.\n"
            "Reply with your predictions using the market number:\n"
            "  - Format: '#Number TeamName Yes/No'\n"
            "  - Example: '19 Atlanta Yes' or '10 philadelphia no'\n"
            "  - Multiple: '19 Atlanta Yes, 20 Los Angeles No'\n\n"
            "Commands:\n"
            "/stats - View your prediction accuracy\n"
            "/setname NewName - Change your display name\n"
            "/refresh - Fetch markets now (instead of waiting for 9 AM)\n"
            "/help - Show detailed instructions"
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📋 **How to Use**\n\n"
            "Markets are numbered 1-N in the list. Use the number to specify which game.\n\n"
            "**Prediction Format:**\n"
            "`#Number TeamName Yes/No`\n\n"
            "**Examples:**\n"
            "• `19 Atlanta Yes` - Market 19, Atlanta wins\n"
            "• `20 los angeles no` - Market 20, LA loses (case-insensitive)\n"
            "• `19 Atlanta Yes, 20 Los Angeles No` - Multiple on one line\n\n"
            "**How It Works:**\n"
            "1. I send 20+ markets with numbers (1, 2, 3...)\n"
            "2. Reply with `#Number Team Yes/No` format\n"
            "3. Team names are fuzzy-matched\n"
            "4. Markets resolve automatically\n"
            "5. Use /stats to track your accuracy\n\n"
            "**Commands:**\n"
            "/start - Register and show welcome message\n"
            "/refresh - Fetch markets now\n"
            "/stats - View your stats\n"
            "/setname <name> - Change your display name\n"
            "/help - Show this message"
        )

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = await self._ensure_user(update)
        user = database.get_user(user_id)
        stats = database.get_user_stats(user_id)
        predictions = database.get_all_predictions(user_id)

        stats_text = (
            f"📊 **Stats for {user['display_name']}**\n\n"
            f"Total: {stats['total_predictions']} | Wins: {stats['wins']} | Accuracy: {stats['accuracy']}%\n\n"
        )

        if predictions:
            stats_text += "**Recent Predictions:**\n"
            for i, pred in enumerate(predictions[:20], 1):
                market = f"{pred['team_a']} vs {pred['team_b']}"
                outcome = "✅ Win" if pred['win_loss'] == 1 else "❌ Loss" if pred['resolved'] and pred['win_loss'] == 0 else "⏳ Pending"
                stats_text += f"{i}. {market} — {pred['predicted_team']} {pred['predicted_outcome']} ({outcome})\n"

                if len(stats_text) > 3500:
                    stats_text += "\n_(showing last 20 predictions)_"
                    break
        else:
            stats_text += "No predictions yet. Use /refresh to fetch markets!"

        await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)

    async def refresh(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manually fetch and send markets immediately."""
        try:
            await update.message.reply_text("🔄 Fetching markets from Kalshi...")
            logger.info("Manual refresh triggered")
            await self.send_daily_markets(context)
        except Exception as e:
            logger.error(f"Error in refresh command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def setname(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set or change the user's display name."""
        user_id = await self._ensure_user(update)
        name = " ".join(context.args).strip() if context.args else ""

        if not name:
            await update.message.reply_text("Usage: /setname YourName\nExample: /setname John")
            return

        database.set_user_name(user_id, name)
        await update.message.reply_text(f"✅ Display name changed to: **{name}**", parse_mode=ParseMode.MARKDOWN)

    def _chunk_markets(self, markets, max_chunk_size=4070):
        """Split markets into chunks that fit within Telegram's message limit (4096 chars max)."""
        chunks = []
        current_chunk = []

        # Account for header, footer, and formatting overhead (~400 chars)
        overhead = len(self.kalshi_client.format_market_display([]))
        available_size = max_chunk_size - overhead - 50  # Extra 50 char buffer

        for market in markets:
            # Test chunk with this market added
            test_chunk = current_chunk + [market]
            formatted = self.kalshi_client.format_market_display(test_chunk)

            # If formatted message exceeds limit, start new chunk
            if len(formatted) > max_chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [market]
            else:
                current_chunk = test_chunk

        # Add remaining markets
        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [[]]

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return

        text = update.message.text.strip()
        user_id = await self._ensure_user(update)

        todays_markets = database.get_todays_markets()
        if not todays_markets:
            await update.message.reply_text(
                "❌ No markets sent today yet. Check back at 9 AM MST or use /refresh."
            )
            return

        try:
            predictions = predictor_parser.parse_predictions(text, todays_markets)

            market_date = todays_markets[0]["sent_date"]
            for market_idx, predicted_team, outcome in predictions:
                market = todays_markets[market_idx]
                database.log_prediction(
                    market["market_id"],
                    market_date,
                    market["team_a"],
                    market["team_b"],
                    predicted_team,
                    outcome,
                    user_id
                )

            confirmation = "✅ Logged {} predictions:\n".format(len(predictions))
            for market_idx, team, outcome in predictions:
                market = todays_markets[market_idx]
                confirmation += f"{market_idx + 1}. {market['team_a']} vs {market['team_b']} — {team} {outcome}\n"

            await update.message.reply_text(confirmation)

        except ValueError as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def send_daily_markets(self, context: ContextTypes.DEFAULT_TYPE):
        """Called by scheduler to fetch and send daily markets."""
        try:
            logger.info("Fetching daily markets from Kalshi...")
            database.clear_old_markets()
            database.clear_todays_markets()  # Start fresh for today
            markets = self.kalshi_client.get_playoff_markets()

            if not markets:
                logger.warning("No active markets found")
                recipients = database.get_all_users()
                if not recipients:
                    recipients = [TELEGRAM_CHAT_ID]
                for chat_id in recipients:
                    try:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text="⚠️ No active NBA Playoffs markets at the moment."
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send 'no markets' message to {chat_id}: {e}")
                return

            # Deduplicate: keep only first occurrence of each team pair (normalized)
            seen_pairs = set()
            deduped_markets = []
            for market in markets:
                # Normalize team pair by sorting (so "A vs B" and "B vs A" are same)
                teams = tuple(sorted([market["team_a"].lower(), market["team_b"].lower()]))
                if teams not in seen_pairs:
                    seen_pairs.add(teams)
                    deduped_markets.append(market)

            logger.info(f"Deduplicated {len(markets)} API markets to {len(deduped_markets)} unique matchups")
            markets = deduped_markets

            now = datetime.now(timezone.utc).isoformat()
            for position, market in enumerate(markets, 1):
                database.save_market(
                    market["market_id"],
                    market["team_a"],
                    market["team_b"],
                    now,
                    market.get("status", "active"),
                    position
                )

            # Split markets into chunks to avoid message length limit (4096 chars)
            market_chunks = self._chunk_markets(markets)
            logger.info(f"Split {len(markets)} markets into {len(market_chunks)} chunk(s)")

            # Get all registered users, fallback to TELEGRAM_CHAT_ID if none registered
            recipients = database.get_all_users()
            if not recipients:
                recipients = [TELEGRAM_CHAT_ID]

            for chat_id in recipients:
                market_number = 1
                for i, chunk in enumerate(market_chunks, 1):
                    message_text = self.kalshi_client.format_market_display(chunk, start_number=market_number)

                    if len(market_chunks) > 1:
                        message_text = f"📌 Markets ({i}/{len(market_chunks)})\n\n" + message_text

                    market_number += len(chunk)

                    # Verify message length before sending (Telegram limit is 4096, we stay at 4094)
                    if len(message_text) > 4094:
                        logger.error(f"Message chunk {i} for user {chat_id} is {len(message_text)} chars (exceeds 4094 limit)")
                        try:
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"⚠️ Error: Message chunk {i} too long ({len(message_text)}/4095 chars). Please try again."
                            )
                        except Exception as e:
                            logger.warning(f"Failed to send error message to {chat_id}: {e}")
                        continue

                    try:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=message_text,
                            parse_mode=ParseMode.MARKDOWN
                        )
                        logger.info(f"Sent chunk {i}/{len(market_chunks)} to user {chat_id} ({len(chunk)} markets, {len(message_text)} chars)")
                    except Exception as chunk_error:
                        logger.error(f"Failed to send chunk {i} to user {chat_id}: {chunk_error}")
                        try:
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"⚠️ Error sending markets chunk {i}: {str(chunk_error)}"
                            )
                        except Exception as e:
                            logger.warning(f"Failed to send error message to {chat_id}: {e}")

            logger.info(f"Sent {len(markets)} markets to {len(recipients)} user(s)")
            self.last_markets = markets

        except Exception as e:
            logger.error(f"Failed to send daily markets: {e}")
            recipients = database.get_all_users()
            if not recipients:
                recipients = [TELEGRAM_CHAT_ID]
            for chat_id in recipients:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ Error fetching markets: {str(e)}"
                    )
                except Exception as send_error:
                    logger.warning(f"Failed to send error message to {chat_id}: {send_error}")

def build_application(token: str, kalshi_client: KalshiClient):
    """Build and configure the Telegram bot application."""
    app = Application.builder().token(token).build()
    handlers = BotHandlers(kalshi_client)

    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help))
    app.add_handler(CommandHandler("stats", handlers.stats))
    app.add_handler(CommandHandler("refresh", handlers.refresh))
    app.add_handler(CommandHandler("setname", handlers.setname))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.message_handler))

    return app, handlers
