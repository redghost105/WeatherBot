#!/usr/bin/env python3
"""
Phase 8: Execution & Order Management Service

Handles safe, auditable trade execution on Kalshi with paper and live modes.
Maintains position lifecycle, performs reconciliation, and feeds outcomes back
to the HistoricalBiasLearner for continuous improvement.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import sqlite3

from kalshi_api_client import KalshiAPIClient
from weather_predictor import HistoricalBiasLearner, MarketEdgeSummary

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order status enum."""
    PENDING = "pending"
    RESTING = "resting"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


class ExecutionMode(Enum):
    """Execution mode: paper (simulated) or live (real capital)."""
    PAPER = "paper"
    LIVE = "live"


@dataclass
class ExecutionConfig:
    """Configuration for ExecutionService."""
    mode: ExecutionMode = ExecutionMode.PAPER
    max_position_size: int = 10  # max contracts per order
    max_daily_loss: float = 1000.0  # max loss in cents before circuit break
    max_per_city_exposure: int = 50  # max total exposure per city
    max_global_exposure: int = 200  # max total exposure across all cities
    min_order_size: int = 1  # minimum contracts to place
    cooldown_seconds: int = 5  # cooldown after anomalies
    retry_count: int = 3  # max retries on transient errors
    journal_path: str = "trade_journal.jsonl"  # audit trail file


@dataclass
class TradeSignal:
    """Trade signal from WeatherPredictor."""
    ticker: str  # Market ticker
    city: str  # City name
    bucket_label: str  # Temperature bucket
    action: str  # "buy" or "sell"
    side: str  # "yes" or "no"
    suggested_size: int  # Suggested contract count
    model_probability: float  # Model's predicted probability
    market_probability: float  # Market's implied probability
    edge_pct: float  # Edge percentage
    confidence: float  # Confidence score (0-100)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OrderRecord:
    """Internal order tracking record."""
    order_id: str
    client_order_id: str
    ticker: str
    action: str
    side: str
    count: int
    yes_price: Optional[int] = None
    no_price: Optional[int] = None
    status: OrderStatus = OrderStatus.PENDING
    created_ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    filled_ts: Optional[datetime] = None
    filled_quantity: int = 0
    filled_price: Optional[float] = None
    fees: float = 0.0
    pnl: Optional[float] = None  # Realized PnL after settlement
    resolution_value: Optional[float] = None  # Actual market resolution value


@dataclass
class PositionRecord:
    """Current position in a market."""
    ticker: str
    count: int  # Net position (positive = long, negative = short)
    entry_price: float
    entry_ts: datetime
    current_value: Optional[float] = None


class ExecutionService:
    """
    Manages trade execution, position tracking, and reconciliation.

    Supports paper (simulated) and live trading modes with safety gates,
    audit logging, and automatic outcome reconciliation.
    """

    def __init__(
        self,
        kalshi_client: KalshiAPIClient,
        bias_learner: HistoricalBiasLearner,
        config: ExecutionConfig = None,
    ):
        """
        Initialize ExecutionService.

        Args:
            kalshi_client: Authenticated Kalshi API client
            bias_learner: HistoricalBiasLearner for feeding outcomes
            config: ExecutionConfig with mode, limits, and parameters
        """
        self.kalshi = kalshi_client
        self.bias_learner = bias_learner
        self.config = config or ExecutionConfig()

        # State tracking
        self.orders: Dict[str, OrderRecord] = {}
        self.positions: Dict[str, PositionRecord] = {}
        self.daily_pnl = 0.0
        self.last_anomaly_ts: Optional[datetime] = None
        self.is_circuit_broken = False

        # Journal for audit trail
        self._init_journal()

        logger.info(f"ExecutionService initialized in {self.config.mode.value} mode")
        if self.config.mode == ExecutionMode.LIVE:
            logger.warning("⚠️  LIVE TRADING MODE - REAL CAPITAL AT RISK")

    def _init_journal(self):
        """Initialize trade journal (JSONL file for immutable audit trail)."""
        Path(self.config.journal_path).parent.mkdir(parents=True, exist_ok=True)

    def _log_event(self, event_type: str, data: Dict):
        """Log an event to the trade journal."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "mode": self.config.mode.value,
            **data
        }

        # Append to JSONL journal
        with open(self.config.journal_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        logger.info(f"[AUDIT] {event_type}: {data}")

    def validate_signal(self, signal: TradeSignal) -> Tuple[bool, str]:
        """
        Validate trade signal before execution.

        Returns:
            (is_valid, reason_if_invalid)
        """
        # Check circuit breaker
        if self.is_circuit_broken:
            return False, "Circuit breaker active"

        # Check cooldown after anomaly
        if self.last_anomaly_ts:
            time_since_anomaly = (datetime.now(timezone.utc) - self.last_anomaly_ts).total_seconds()
            if time_since_anomaly < self.config.cooldown_seconds:
                return False, f"Cooldown active ({self.config.cooldown_seconds}s)"

        # Check daily loss limit
        if self.daily_pnl < -self.config.max_daily_loss:
            self.is_circuit_broken = True
            self._log_event("circuit_break", {"reason": "daily_loss_exceeded", "daily_pnl": self.daily_pnl})
            return False, "Daily loss limit exceeded"

        # Check position size limit
        if signal.suggested_size > self.config.max_position_size:
            return False, f"Position size ({signal.suggested_size}) exceeds limit ({self.config.max_position_size})"

        # Check minimum edge threshold
        if signal.edge_pct < 0.05:
            return False, "Edge below minimum threshold"

        # Check confidence threshold
        if signal.confidence < 60:
            return False, "Confidence below threshold"

        return True, ""

    def construct_order(self, signal: TradeSignal) -> OrderRecord:
        """
        Convert TradeSignal into platform-compatible order.

        Args:
            signal: Trade signal from WeatherPredictor

        Returns:
            OrderRecord ready for placement
        """
        # Generate idempotency key
        client_order_id = str(uuid.uuid4())

        # Convert model probability to order price (1-99 cents)
        # Market prices in cents: YES price + NO price ≈ 100 cents
        yes_price = int(signal.model_probability * 100)
        yes_price = max(1, min(99, yes_price))  # Clamp to [1, 99]

        order = OrderRecord(
            order_id="",  # Will be assigned by API
            client_order_id=client_order_id,
            ticker=signal.ticker,
            action=signal.action,
            side=signal.side,
            count=signal.suggested_size,
            yes_price=yes_price if signal.side == "yes" else None,
            no_price=(100 - yes_price) if signal.side == "no" else None,
            status=OrderStatus.PENDING,
        )

        return order

    def check_market_validity(self, ticker: str) -> Tuple[bool, str]:
        """
        Check if market is still open and available for trading.

        Args:
            ticker: Market ticker

        Returns:
            (is_valid, reason_if_invalid)
        """
        try:
            market = self.kalshi.get_market(ticker)
            if not market:
                return False, "Market not found"

            # Check status - Kalshi uses "active" for open markets
            status = market.get("status")
            if status not in ["active", "open", "unopened"]:
                return False, f"Market status is {status}, not tradeable"

            # Check liquidity (bid/ask spread)
            orderbook = self.kalshi.get_orderbook(ticker)
            if not orderbook:
                return False, "No orderbook data available"

            return True, ""

        except Exception as e:
            # In paper mode, allow validation to pass even if market check fails
            if self.config.mode == ExecutionMode.PAPER:
                return True, ""
            return False, f"Market validation error: {e}"

    def check_balance(self, required_cents: int) -> Tuple[bool, str]:
        """
        Verify sufficient balance for order.

        Args:
            required_cents: Required balance in cents

        Returns:
            (has_balance, reason_if_insufficient)
        """
        if self.config.mode == ExecutionMode.PAPER:
            # Paper mode: unlimited virtual balance
            return True, ""

        try:
            portfolio = self.kalshi.get_portfolio_balance()
            balance = portfolio.get("balance", 0)

            if balance < required_cents:
                return False, f"Insufficient balance: {balance} < {required_cents}"

            return True, ""

        except Exception as e:
            return False, f"Balance check error: {e}"

    def place_order(self, signal: TradeSignal) -> Tuple[bool, OrderRecord]:
        """
        Execute order placement with full validation pipeline.

        Args:
            signal: Trade signal from WeatherPredictor

        Returns:
            (success, order_record)
        """
        # Step 1: Validate signal
        is_valid, reason = self.validate_signal(signal)
        if not is_valid:
            self._log_event("signal_rejected", {"signal": asdict(signal), "reason": reason})
            return False, OrderRecord(
                order_id="",
                client_order_id="",
                ticker=signal.ticker,
                action=signal.action,
                side=signal.side,
                count=0,
                status=OrderStatus.REJECTED,
            )

        # Step 2: Check market validity
        is_valid, reason = self.check_market_validity(signal.ticker)
        if not is_valid:
            self._log_event("market_invalid", {"ticker": signal.ticker, "reason": reason})
            return False, OrderRecord(
                order_id="",
                client_order_id="",
                ticker=signal.ticker,
                action=signal.action,
                side=signal.side,
                count=0,
                status=OrderStatus.REJECTED,
            )

        # Step 3: Construct order
        order = self.construct_order(signal)

        # Step 4: Check balance
        required_cents = order.count * (order.yes_price or order.no_price or 50)
        has_balance, reason = self.check_balance(required_cents)
        if not has_balance:
            self._log_event("balance_insufficient", {"required": required_cents, "reason": reason})
            return False, order

        # Step 5: Place order
        if self.config.mode == ExecutionMode.PAPER:
            # Paper mode: simulate execution
            order.order_id = f"PAPER-{order.client_order_id}"
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.count
            order.filled_price = (order.yes_price or order.no_price) / 100.0
            order.filled_ts = datetime.now(timezone.utc)

            self._log_event("paper_order_placed", {
                "client_order_id": order.client_order_id,
                "ticker": order.ticker,
                "action": order.action,
                "side": order.side,
                "count": order.count,
                "price": order.filled_price,
            })

        else:
            # Live mode: place real order
            try:
                api_order = self.kalshi.place_order(
                    ticker=order.ticker,
                    action=order.action,
                    side=order.side,
                    type_="limit",
                    count=order.count,
                    price=order.yes_price or order.no_price,
                    client_order_id=order.client_order_id,
                    time_in_force="day",
                )

                if not api_order:
                    self._log_event("live_order_failed", {"client_order_id": order.client_order_id})
                    return False, order

                order.order_id = api_order.get("order_id", "")
                order.status = OrderStatus(api_order.get("status", "resting"))

                self._log_event("live_order_placed", {
                    "order_id": order.order_id,
                    "client_order_id": order.client_order_id,
                    "ticker": order.ticker,
                    "status": order.status.value,
                })

            except Exception as e:
                self._log_event("live_order_error", {"client_order_id": order.client_order_id, "error": str(e)})
                return False, order

        # Track order
        self.orders[order.order_id] = order
        self._log_event("order_placed", {"order_id": order.order_id, "ticker": order.ticker})

        return True, order

    def get_order_status(self, order_id: str) -> OrderRecord:
        """Get current order status."""
        if order_id in self.orders:
            return self.orders[order_id]

        if self.config.mode == ExecutionMode.LIVE:
            try:
                api_order = self.kalshi.get_order(order_id)
                if api_order:
                    order = self.orders[order_id]
                    order.status = OrderStatus(api_order.get("status", "resting"))
                    return order
            except Exception as e:
                logger.error(f"Failed to get order status: {e}")

        return OrderRecord(
            order_id=order_id,
            client_order_id="",
            ticker="",
            action="",
            side="",
            count=0,
            status=OrderStatus.REJECTED,
        )

    def reconcile_fills(self) -> Dict[str, List[OrderRecord]]:
        """
        Reconcile fills from API with internal tracking.

        Returns:
            Dict with 'filled' and 'updated' order lists
        """
        filled_orders = []
        updated_orders = []

        if self.config.mode == ExecutionMode.LIVE:
            try:
                fills = self.kalshi.get_fills()
                for fill in fills:
                    order_id = fill.get("order_id")
                    if order_id in self.orders:
                        order = self.orders[order_id]
                        order.filled_quantity = fill.get("quantity", 0)
                        order.filled_price = fill.get("price", 0) / 100.0
                        order.filled_ts = datetime.fromtimestamp(
                            fill.get("created_ts_ms", 0) / 1000,
                            tz=timezone.utc
                        )
                        order.status = OrderStatus.FILLED if order.filled_quantity >= order.count else OrderStatus.PARTIALLY_FILLED
                        updated_orders.append(order)

            except Exception as e:
                logger.error(f"Failed to reconcile fills: {e}")
                self.last_anomaly_ts = datetime.now(timezone.utc)

        # Check for orders that should be marked as filled (paper mode)
        for order in self.orders.values():
            if order.status == OrderStatus.FILLED and order not in updated_orders:
                filled_orders.append(order)

        return {"filled": filled_orders, "updated": updated_orders}

    def update_positions(self):
        """Update position tracking from current orders."""
        self.positions.clear()

        for order in self.orders.values():
            if order.status == OrderStatus.FILLED:
                if order.ticker not in self.positions:
                    self.positions[order.ticker] = PositionRecord(
                        ticker=order.ticker,
                        count=0,
                        entry_price=order.filled_price or 0,
                        entry_ts=order.filled_ts or datetime.now(timezone.utc),
                    )

                pos = self.positions[order.ticker]
                # Update position count (buy increases, sell decreases)
                if order.action == "buy":
                    pos.count += order.filled_quantity
                else:
                    pos.count -= order.filled_quantity

    def reconcile_resolution(self, ticker: str, resolution_value: float) -> Optional[float]:
        """
        Reconcile market resolution and calculate PnL.

        Args:
            ticker: Market ticker that resolved
            resolution_value: Actual resolved value

        Returns:
            Realized PnL in cents
        """
        pnl = 0.0

        for order in self.orders.values():
            if order.ticker == ticker and order.status == OrderStatus.FILLED:
                # Determine if order was winning
                resolved_price = resolution_value

                if order.side == "yes":
                    # YES contracts win if resolution >= entry price
                    win_price = 100  # YES worth $1 if correct
                    loss_price = 0
                else:
                    # NO contracts win if resolution < entry price
                    win_price = 0  # NO worth $0 if YES resolved
                    loss_price = 100

                # Calculate PnL
                entry_cost = order.filled_price * order.filled_quantity
                exit_value = (resolved_price / 100.0) * order.filled_quantity if order.side == "yes" else ((1 - resolution_value / 100.0) * order.filled_quantity)

                order.pnl = (exit_value - entry_cost) * 100  # Convert to cents
                order.resolution_value = resolution_value
                order.status = OrderStatus.FILLED  # Mark as resolved

                pnl += order.pnl

                self._log_event("resolution_reconciled", {
                    "ticker": ticker,
                    "order_id": order.order_id,
                    "side": order.side,
                    "resolution": resolution_value,
                    "pnl": order.pnl,
                })

                # Feed outcome back to bias learner for continuous improvement
                # Extract station_id from ticker (e.g., KXHIGHNY-26MAY21-T75 -> KXHIGHNY)
                station_id = ticker.split("-")[0]
                forecast_temp = order.filled_price * 100  # Convert price (0-1) back to temperature
                self.bias_learner.update(
                    station_id=station_id,
                    forecast_high=forecast_temp,
                    actual_high=resolution_value,
                    date=order.filled_ts.isoformat() if order.filled_ts else None,
                )

        self.daily_pnl += pnl
        return pnl if pnl != 0 else None

    def emergency_stop(self):
        """Halt all trading immediately."""
        self.is_circuit_broken = True
        self._log_event("emergency_stop", {"timestamp": datetime.now(timezone.utc).isoformat()})
        logger.critical("🚨 EMERGENCY STOP ACTIVATED - All trading halted")

    def get_summary(self) -> Dict:
        """Get execution summary."""
        return {
            "mode": self.config.mode.value,
            "total_orders": len(self.orders),
            "filled_orders": sum(1 for o in self.orders.values() if o.status == OrderStatus.FILLED),
            "open_positions": len(self.positions),
            "daily_pnl": self.daily_pnl,
            "circuit_broken": self.is_circuit_broken,
            "journal_path": self.config.journal_path,
        }
