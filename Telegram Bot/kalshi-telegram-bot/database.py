import sqlite3
from datetime import datetime
from config import DB_PATH, TELEGRAM_CHAT_ID

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            display_name TEXT NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_id TEXT NOT NULL,
            market_date DATETIME NOT NULL,
            team_a TEXT NOT NULL,
            team_b TEXT NOT NULL,
            predicted_team TEXT NOT NULL,
            predicted_outcome TEXT NOT NULL CHECK(predicted_outcome IN ('Yes', 'No')),
            prediction_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            resolved BOOLEAN NOT NULL DEFAULT 0,
            result_outcome TEXT CHECK(result_outcome IN ('Yes', 'No') OR result_outcome IS NULL),
            win_loss BOOLEAN,
            user_id INTEGER,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS markets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_id TEXT UNIQUE NOT NULL,
            team_a TEXT NOT NULL,
            team_b TEXT NOT NULL,
            sent_date DATETIME NOT NULL,
            kalshi_status TEXT,
            display_position INTEGER,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_id ON predictions(market_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_date ON predictions(market_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_resolved ON predictions(resolved)")

    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN user_id INTEGER")
    except sqlite3.OperationalError:
        pass

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON predictions(user_id)")

    # Migration: Backfill orphaned predictions (from before multi-user support)
    # This ensures data is never lost due to schema changes
    cursor.execute("SELECT COUNT(*) FROM predictions WHERE user_id IS NULL")
    orphaned_count = cursor.fetchone()[0]

    if orphaned_count > 0:
        # Backfill orphaned predictions to the bot's chat ID (original single-user mode)
        cursor.execute(
            "UPDATE predictions SET user_id = ? WHERE user_id IS NULL",
            (TELEGRAM_CHAT_ID,)
        )
        conn.commit()
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Migration: Backfilled {orphaned_count} orphaned predictions to user {TELEGRAM_CHAT_ID}")

    conn.commit()
    conn.close()

def log_prediction(market_id, market_date, team_a, team_b, predicted_team, outcome, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    # Ensure user_id is never NULL - fallback to TELEGRAM_CHAT_ID
    safe_user_id = user_id if user_id is not None else TELEGRAM_CHAT_ID
    cursor.execute("""
        INSERT INTO predictions
        (market_id, market_date, team_a, team_b, predicted_team, predicted_outcome, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (market_id, market_date, team_a, team_b, predicted_team, outcome, safe_user_id))
    conn.commit()
    conn.close()

def clear_old_markets():
    """Delete markets older than today."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM markets WHERE DATE(sent_date) < DATE('now')")
    conn.commit()
    conn.close()

def clear_todays_markets():
    """Delete all markets from today to refresh with new fetch."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM markets WHERE DATE(sent_date) = DATE('now')")
    conn.commit()
    conn.close()

def save_market(market_id, team_a, team_b, sent_date, status, position=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO markets
        (market_id, team_a, team_b, sent_date, kalshi_status, display_position)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (market_id, team_a, team_b, sent_date, status, position))
    conn.commit()
    conn.close()

def get_todays_markets():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM markets
        WHERE DATE(sent_date) = DATE('now')
        ORDER BY display_position ASC, id ASC
    """)
    markets = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return markets

def get_unresolved_markets():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT market_id FROM predictions
        WHERE resolved = 0
    """)
    market_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return market_ids

def update_market_result(market_id, result_outcome, win_loss):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE predictions
        SET resolved = 1, result_outcome = ?, win_loss = ?
        WHERE market_id = ?
    """, (result_outcome, win_loss, market_id))
    conn.commit()
    conn.close()

def get_user_stats(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM predictions WHERE user_id = ?", (user_id,))
    total_predictions = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM predictions WHERE user_id = ? AND win_loss = 1", (user_id,))
    wins = cursor.fetchone()[0]

    accuracy = round((wins / total_predictions * 100), 1) if total_predictions > 0 else 0

    conn.close()

    return {
        "total_predictions": total_predictions,
        "wins": wins,
        "accuracy": accuracy,
        "current_streak": 0,
        "longest_streak": 0
    }

def get_all_predictions(user_id):
    """Get all predictions for a user with their results ordered by date."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            team_a,
            team_b,
            predicted_team,
            predicted_outcome,
            resolved,
            win_loss,
            prediction_timestamp
        FROM predictions
        WHERE user_id = ?
        ORDER BY prediction_timestamp DESC
    """, (user_id,))
    predictions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return predictions

def get_or_create_user(telegram_id, display_name):
    """Create a user if they don't exist, then return their record."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO users (telegram_id, display_name)
        VALUES (?, ?)
    """, (telegram_id, display_name))
    conn.commit()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = dict(cursor.fetchone())
    conn.close()
    return user

def set_user_name(telegram_id, display_name):
    """Update a user's display name."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO users (telegram_id, display_name)
        VALUES (?, ?)
    """, (telegram_id, display_name))
    cursor.execute("""
        UPDATE users SET display_name = ? WHERE telegram_id = ?
    """, (display_name, telegram_id))
    conn.commit()
    conn.close()

def get_all_users():
    """Get all registered telegram user IDs."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id FROM users ORDER BY created_at ASC")
    user_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return user_ids

def get_user(telegram_id):
    """Get a user by telegram_id, returns None if not found."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
