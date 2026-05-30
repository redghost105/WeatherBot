"""
Phase 11: Comprehensive Monitoring & Structured Logging

Centralized logging system for all trading activities with:
- Structured logs to rotating daily files
- SQLite searchable event store
- Rich context for every event (station, method, bias, confidence, edge, risk decision)
- Standard severity levels (DEBUG, INFO, WARNING, ERROR)
"""

import logging
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass, asdict
from typing import Dict, Optional, Any


@dataclass
class LogEvent:
    """Structured log event with rich context."""
    timestamp: str                  # ISO 8601 UTC timestamp
    severity: str                   # DEBUG, INFO, WARNING, ERROR
    component: str                  # weather_predictor, risk_manager, execution_service, etc.
    event_type: str                 # prediction, edge_detected, risk_check, order_placed, etc.

    # Context fields
    station_id: Optional[str] = None
    city: Optional[str] = None
    message: str = ""

    # Prediction context
    prediction_method: Optional[str] = None  # ensemble, statistical, hybrid
    bias_applied: Optional[float] = None
    ensemble_std: Optional[float] = None
    confidence_score: Optional[float] = None

    # Edge context
    model_prob: Optional[float] = None
    market_price: Optional[float] = None
    edge_pct: Optional[float] = None

    # Risk context
    risk_decision: Optional[str] = None      # APPROVED, REJECTED, reason
    exposure_check: Optional[str] = None
    daily_loss_pct: Optional[float] = None

    # Execution context
    order_id: Optional[str] = None
    ticker: Optional[str] = None
    size: Optional[int] = None
    fill_price: Optional[float] = None
    pnl_cents: Optional[int] = None

    # Metadata
    metadata: Dict[str, Any] = None


class StructuredLogger:
    """
    Centralized logging system with multiple backends.

    Logs to:
    - Rotating daily files (JSON format)
    - SQLite searchable database
    - Console (for real-time monitoring)
    """

    def __init__(self, log_dir: str = "logs", db_path: str = "logs/events.db"):
        """Initialize structured logger."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)

        # Initialize standard Python logging
        self._setup_file_logging()

        # Initialize SQLite event store
        self._init_database()

        self.logger = logging.getLogger("weatherbot")
        self.logger.info("StructuredLogger initialized")

    def _setup_file_logging(self):
        """Configure rotating daily log files."""
        log_file = self.log_dir / "weatherbot.log"

        handler = RotatingFileHandler(
            str(log_file),
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=30,  # Keep 30 days
            encoding='utf-8'
        )

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)

        logger = logging.getLogger("weatherbot")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    def _init_database(self):
        """Initialize SQLite event database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                severity TEXT NOT NULL,
                component TEXT NOT NULL,
                event_type TEXT NOT NULL,
                station_id TEXT,
                city TEXT,
                message TEXT,
                prediction_method TEXT,
                bias_applied REAL,
                confidence_score REAL,
                edge_pct REAL,
                risk_decision TEXT,
                order_id TEXT,
                ticker TEXT,
                pnl_cents INTEGER,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_timestamp (timestamp),
                INDEX idx_component (component),
                INDEX idx_event_type (event_type),
                INDEX idx_city (city),
                INDEX idx_severity (severity)
            )
            """)
            conn.commit()

    def log_event(self, event: LogEvent) -> None:
        """
        Log a structured event to all backends.

        Args:
            event: LogEvent with rich context
        """
        # Log to standard logger
        self.logger.log(
            getattr(logging, event.severity),
            f"[{event.component}] {event.event_type}: {event.message}",
            extra={
                'station': event.station_id,
                'city': event.city,
                'edge': event.edge_pct,
                'confidence': event.confidence_score
            }
        )

        # Store in SQLite
        self._store_in_database(event)

    def _store_in_database(self, event: LogEvent) -> None:
        """Store event in SQLite database."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("""
                    INSERT INTO events (
                        timestamp, severity, component, event_type, station_id, city,
                        message, prediction_method, bias_applied, confidence_score,
                        edge_pct, risk_decision, order_id, ticker, pnl_cents, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.timestamp,
                    event.severity,
                    event.component,
                    event.event_type,
                    event.station_id,
                    event.city,
                    event.message,
                    event.prediction_method,
                    event.bias_applied,
                    event.confidence_score,
                    event.edge_pct,
                    event.risk_decision,
                    event.order_id,
                    event.ticker,
                    event.pnl_cents,
                    json.dumps(event.metadata or {})
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to store event in database: {e}")

    def query_events(
        self,
        component: Optional[str] = None,
        event_type: Optional[str] = None,
        city: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """Query events from SQLite database."""
        query = "SELECT * FROM events WHERE 1=1"
        params = []

        if component:
            query += " AND component = ?"
            params.append(component)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if city:
            query += " AND city = ?"
            params.append(city)
        if severity:
            query += " AND severity = ?"
            params.append(severity)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Failed to query events: {e}")
            return []

    def get_daily_summary(self) -> Dict[str, Any]:
        """Get summary of today's events."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute("""
                    SELECT
                        COUNT(*) as total_events,
                        SUM(CASE WHEN severity='ERROR' THEN 1 ELSE 0 END) as errors,
                        SUM(CASE WHEN severity='WARNING' THEN 1 ELSE 0 END) as warnings,
                        COUNT(DISTINCT component) as components_active,
                        COUNT(DISTINCT city) as cities_traded
                    FROM events
                    WHERE DATE(timestamp) = DATE('now')
                """)
                result = dict(cursor.fetchone() or {})
                return result
        except Exception as e:
            self.logger.error(f"Failed to get daily summary: {e}")
            return {}


# Global logger instance
_logger_instance = None


def get_logger() -> StructuredLogger:
    """Get or create global logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = StructuredLogger()
    return _logger_instance


def log_prediction(
    station_id: str,
    city: str,
    method: str,
    bias: float,
    std: float,
    confidence: float,
    message: str = ""
) -> None:
    """Log a prediction event."""
    logger = get_logger()
    event = LogEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        severity="INFO",
        component="weather_predictor",
        event_type="prediction_generated",
        station_id=station_id,
        city=city,
        message=message,
        prediction_method=method,
        bias_applied=bias,
        ensemble_std=std,
        confidence_score=confidence
    )
    logger.log_event(event)


def log_edge_detected(
    station_id: str,
    city: str,
    model_prob: float,
    market_price: float,
    edge: float,
    confidence: float,
    message: str = ""
) -> None:
    """Log edge detection event."""
    logger = get_logger()
    event = LogEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        severity="INFO",
        component="weather_predictor",
        event_type="edge_detected",
        station_id=station_id,
        city=city,
        message=message,
        model_prob=model_prob,
        market_price=market_price,
        edge_pct=edge,
        confidence_score=confidence
    )
    logger.log_event(event)


def log_risk_decision(
    station_id: str,
    city: str,
    decision: str,
    reason: str,
    exposure_check: Optional[str] = None,
    daily_loss: Optional[float] = None
) -> None:
    """Log risk management decision."""
    logger = get_logger()
    event = LogEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        severity="INFO" if decision == "APPROVED" else "WARNING",
        component="risk_manager",
        event_type="risk_decision",
        station_id=station_id,
        city=city,
        message=reason,
        risk_decision=decision,
        exposure_check=exposure_check,
        daily_loss_pct=daily_loss
    )
    logger.log_event(event)


def log_execution(
    order_id: str,
    ticker: str,
    city: str,
    size: int,
    fill_price: float,
    message: str = ""
) -> None:
    """Log order execution."""
    logger = get_logger()
    event = LogEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        severity="INFO",
        component="execution_service",
        event_type="order_executed",
        city=city,
        message=message,
        order_id=order_id,
        ticker=ticker,
        size=size,
        fill_price=fill_price
    )
    logger.log_event(event)


def log_resolution(
    ticker: str,
    city: str,
    pnl_cents: int,
    message: str = ""
) -> None:
    """Log trade resolution."""
    logger = get_logger()
    event = LogEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        severity="INFO",
        component="execution_service",
        event_type="trade_resolved",
        city=city,
        message=message,
        ticker=ticker,
        pnl_cents=pnl_cents
    )
    logger.log_event(event)


def log_error(component: str, error_msg: str, metadata: Dict = None) -> None:
    """Log an error event."""
    logger = get_logger()
    event = LogEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        severity="ERROR",
        component=component,
        event_type="error",
        message=error_msg,
        metadata=metadata or {}
    )
    logger.log_event(event)


if __name__ == "__main__":
    logger = get_logger()

    # Test logging
    log_prediction(
        "KNYC", "NYC", "hybrid",
        bias=1.5, std=2.0, confidence=82.5,
        message="Generated hybrid probability distribution"
    )

    log_edge_detected(
        "KNYC", "NYC",
        model_prob=0.68, market_price=0.55, edge=0.13, confidence=82.5,
        message="Strong edge detected on 75+ bucket"
    )

    log_risk_decision(
        "KNYC", "NYC", "APPROVED", "All risk checks passed",
        exposure_check="OK", daily_loss=-2.5
    )

    print("✓ Logging system initialized and tested")
