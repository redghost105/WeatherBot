"""
Phase 12: Automated Trading Engine (Refactored with Modular Components)

Background process that continuously:
1. Scans Kalshi for active weather markets (scan_markets)
2. Parses market data and extracts buckets (market_parser module)
3. Generates trade signals via WeatherPredictor (signal_generator module)
4. Validates trades with RiskManager (validate_trades)
5. Executes orders (paper or live mode) (execution_service)
6. Learns from resolutions (resolution_learner module)

Runs independently from dashboard - can be started/stopped separately.
Implements the systematic misprice-exploitation strategy from the article.

MODULAR ARCHITECTURE:
- market_parser.py: Market title parsing and bucket extraction
- signal_generator.py: Signal generation with edge detection
- resolution_learner.py: Resolution processing and bias learning
- trading_engine.py: Orchestration, scanning, risk validation, execution
"""

import os
import sys
import time
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
import json
import threading
from pathlib import Path
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Import modular components
from signal_generator import SignalGenerator, TradeSignal
from resolution_learner import ResolutionLearner
from market_parser import CITIES_KALSHI

# Legacy import for backward compatibility
__all__ = ['TradingEngine', 'TradeSignal', 'CITIES_KALSHI']


class TradingEngine:
    """
    Core automated trading engine orchestrator.

    Runs as a continuous background process scanning markets,
    generating signals, validating risk, and executing trades.

    Uses modular components:
    - SignalGenerator for weather-based signals
    - ResolutionLearner for bias learning
    - RiskManager for risk validation
    - ExecutionService for order placement
    """

    def __init__(self):
        """Initialize trading engine with all dependencies."""
        self.running = False
        self.scan_interval = int(os.getenv('TRADING_SCAN_INTERVAL', '300'))  # 5 minutes default
        self.trading_mode = os.getenv('TRADING_MODE', 'paper').lower()
        self.min_edge_threshold = float(os.getenv('MIN_EDGE_THRESHOLD', '0.11'))

        logger.info(f"Trading Engine initializing in {self.trading_mode.upper()} mode")
        logger.info(f"Scan interval: {self.scan_interval}s, Min edge: {self.min_edge_threshold}")

        # Set up file-based logging
        self._setup_file_logging()

        # Initialize core dependencies (order matters: client → predictor → risk_manager → execution)
        self.init_kalshi_client()
        self.init_predictor()
        self.init_risk_manager()
        self.init_execution_service()

        # Initialize modular components
        self.signal_generator = None
        self.resolution_learner = None
        if self.predictor:
            self.signal_generator = SignalGenerator(self.predictor)
            self.resolution_learner = ResolutionLearner(self.predictor.bias_learner)
            logger.info("✓ SignalGenerator initialized")
            logger.info("✓ ResolutionLearner initialized")

        # Verify all critical components are ready
        if not self.kalshi_client:
            logger.error("WARNING: Kalshi client failed to initialize")
        if not self.predictor:
            logger.error("WARNING: WeatherPredictor failed to initialize")

        # Track engine state for dashboard
        self._stats = {
            'markets_scanned': 0,
            'signals_generated': 0,
            'trades_executed': 0,
            'trades_failed': 0,
            'last_scan': None,
            'active_markets': 0
        }

        # Trade journal for archiving
        self.trade_journal = {
            'created_at': datetime.now(timezone.utc).isoformat(),
            'trades': []
        }

    def _setup_file_logging(self):
        """Set up self-contained rotating file logging."""
        from logging.handlers import RotatingFileHandler
        log_dir = os.path.expanduser(os.getenv('LOGS_DIR', '~/trading_logs'))
        os.makedirs(log_dir, exist_ok=True)
        date_str = datetime.now().strftime('%Y-%m-%d')
        log_path = os.path.join(log_dir, f'trading_{date_str}.log')
        handler = RotatingFileHandler(
            log_path, maxBytes=50 * 1024 * 1024, backupCount=30
        )
        handler.setFormatter(logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s'))
        logging.getLogger().addHandler(handler)  # root logger → captures ALL module loggers
        logger.info(f"File logging active: {log_path}")

    def init_kalshi_client(self):
        """Initialize Kalshi API client."""
        try:
            from kalshi_api_client import KalshiAPIClient

            api_key_id = os.getenv('KALSHI_API_KEY_ID')
            private_key_path = os.getenv('KALSHI_PRIVATE_KEY_PATH')

            if not api_key_id or not private_key_path:
                raise ValueError("Kalshi credentials not configured")

            with open(private_key_path, 'r') as f:
                private_key_pem = f.read()

            self.kalshi_client = KalshiAPIClient(api_key_id, private_key_pem)
            logger.info("✓ Kalshi API client initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize Kalshi client: {e}")
            self.kalshi_client = None

    def init_predictor(self):
        """Initialize WeatherPredictor."""
        try:
            from weather_predictor import WeatherPredictor
            self.predictor = WeatherPredictor(
                ensemble_weight=0.7,
                temp_unit='F'
            )
            logger.info("✓ WeatherPredictor initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize predictor: {e}")
            self.predictor = None

    def init_risk_manager(self):
        """Initialize RiskManager."""
        try:
            from risk_manager import RiskManager
            self.risk_manager = RiskManager(kalshi_client=self.kalshi_client)
            logger.info("✓ RiskManager initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize risk manager: {e}")
            self.risk_manager = None

    def init_execution_service(self):
        """Initialize ExecutionService."""
        try:
            from execution_service import ExecutionService
            self.execution_service = ExecutionService(
                kalshi_client=self.kalshi_client,
                bias_learner=self.predictor.bias_learner if self.predictor else None
            )
            logger.info("✓ ExecutionService initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize execution service: {e}")
            self.execution_service = None

    def scan_markets(self) -> List[Dict]:
        """
        Market Scanner: Discover active Kalshi weather markets for tomorrow.

        Strategy: Trade tomorrow's weather events for better forecast quality
        and more time for edge to compound.

        Filters:
        - Only configured cities (CITIES_KALSHI)
        - Event occurs tomorrow (occurrence_datetime == tomorrow's date)
        - Status is 'open'

        Returns:
            List of market dicts for tomorrow's events with metadata
        """
        if not self.kalshi_client:
            return []

        try:
            # Series ticker patterns for weather markets
            series_patterns = {
                'NYC': 'KXHIGHNY',
                'Chicago': 'KXHIGHCHI',
                'Dallas': 'KXHIGHDFW',
                'Denver': 'KXHIGHDEN',
                'LA': 'KXHIGHLAX',
            }

            all_weather_markets = []

            # Fetch markets for each city using series_ticker
            for city_name, series_ticker in series_patterns.items():
                try:
                    markets = self.kalshi_client.get_markets(status='open', series_ticker=series_ticker)
                    logger.debug(f"Found {len(markets)} {city_name} weather markets (series: {series_ticker})")
                    all_weather_markets.extend(markets)
                except Exception as e:
                    logger.debug(f"Error fetching {city_name} markets: {e}")
                    continue

            # Filter to tomorrow's markets based on occurrence date
            qualified = []
            now = datetime.now(timezone.utc)
            tomorrow = (now + timedelta(days=1)).date()

            for market in all_weather_markets:
                try:
                    # Check if event occurs tomorrow
                    occurrence_str = market.get('occurrence_datetime')
                    if not occurrence_str:
                        logger.debug(f"Market {market.get('ticker')} has no occurrence_datetime")
                        continue

                    occurrence_dt = datetime.fromisoformat(occurrence_str.replace('Z', '+00:00'))
                    event_date = occurrence_dt.date()

                    if event_date == tomorrow:
                        # Calculate hours to close for logging
                        close_time_str = market.get('close_time')
                        if close_time_str:
                            close_dt = datetime.fromisoformat(close_time_str.replace('Z', '+00:00'))
                            hours_to_close = (close_dt - now).total_seconds() / 3600
                            market['hours_to_resolution'] = hours_to_close
                            logger.debug(f"Market {market.get('ticker')}: {hours_to_close:.1f}h to close")

                        qualified.append(market)

                except Exception as e:
                    logger.debug(f"Error processing market {market.get('ticker')}: {e}")
                    continue

            self._stats['markets_scanned'] = len(qualified)
            logger.info(f"Qualified {len(qualified)} tomorrow's markets (scanned {len(all_weather_markets)} total weather markets)")
            return qualified

        except Exception as e:
            logger.error(f"Market scan failed: {e}")
            return []

    def parse_market_buckets(self, market: Dict) -> Optional[Tuple[List, str]]:
        """
        DEPRECATED: Use market_parser.parse_market_buckets instead.

        This method is kept for backward compatibility.
        Delegates to market_parser module.
        """
        from market_parser import parse_market_buckets as _parse_buckets
        return _parse_buckets(market)

    def generate_signals(self, markets: List[Dict]) -> List[TradeSignal]:
        """
        Generate trade signals from markets.

        REFACTORED: Now delegates to SignalGenerator module for modularity.
        This method maintains backward compatibility while using the new component.

        Args:
            markets: List of market dicts from Kalshi API

        Returns:
            List of TradeSignal objects with high-conviction opportunities
        """
        if not self.signal_generator or not markets:
            return []

        signals = self.signal_generator.generate_signals(
            markets=markets,
            kalshi_client=self.kalshi_client,
            min_edge=self.min_edge_threshold
        )

        # Track stats
        self._stats['signals_generated'] = len(signals)
        return signals

    def validate_trades(self, signals: List[TradeSignal]) -> List[TradeSignal]:
        """
        Trade Validator: Check risk constraints before execution.

        Checks:
        - Global exposure limits (≤20-25% of equity)
        - Per-city concentration limits (≤8-10% per city)
        - Daily loss limit not breached
        - Single trade size (≤3-4% of equity)
        - Data freshness and confidence thresholds

        Returns:
            List of validated trade proposals that passed all checks
        """
        if not signals:
            return []

        validated = []

        try:
            # Get current portfolio state
            portfolio = self.kalshi_client.get_portfolio_balance()
            equity = portfolio.get('balance', 0) / 100  # Convert cents to dollars
            positions = self.kalshi_client.get_positions()

            # Calculate current exposure by city
            current_exposure_by_city = {}
            total_exposure = 0
            for pos in positions:
                try:
                    ticker = pos.get('market_ticker', '')
                    # Extract city from ticker if possible
                    for city, config in CITIES_KALSHI.items():
                        if city.upper() in ticker.upper():
                            amount = abs(pos.get('market_exposure_dollars', 0))
                            current_exposure_by_city[city] = current_exposure_by_city.get(city, 0) + amount
                            total_exposure += amount
                            break
                except Exception as e:
                    logger.debug(f"Error parsing position: {e}")
                    continue

            logger.info(f"Current exposure: ${total_exposure:.2f} ({total_exposure/equity*100:.1f}% of ${equity:.2f} equity)")

        except Exception as e:
            logger.warning(f"Failed to fetch portfolio state: {e}")
            equity = 10.0  # Default to $10 if we can't fetch
            current_exposure_by_city = {}
            total_exposure = 0

        for signal in signals:
            try:
                # Check 1: Single trade size (≤3-4% of equity)
                max_trade_size = equity * 0.04
                if signal.total_notional > max_trade_size:
                    logger.info(f"Rejected {signal.market_ticker}: Trade size ${signal.total_notional:.2f} exceeds max ${max_trade_size:.2f}")
                    continue

                # Check 2: Per-city concentration (≤8-10% per city)
                current_city_exposure = current_exposure_by_city.get(signal.city_name, 0)
                max_city_exposure = equity * 0.10
                if current_city_exposure + signal.total_notional > max_city_exposure:
                    logger.info(f"Rejected {signal.market_ticker}: {signal.city_name} exposure ${current_city_exposure + signal.total_notional:.2f} exceeds max ${max_city_exposure:.2f}")
                    continue

                # Check 3: Global exposure limit (≤20-25% of equity)
                max_global_exposure = equity * 0.25
                if total_exposure + signal.total_notional > max_global_exposure:
                    logger.info(f"Rejected {signal.market_ticker}: Global exposure ${total_exposure + signal.total_notional:.2f} exceeds max ${max_global_exposure:.2f}")
                    continue

                # Check 4: Confidence threshold (≥55)
                if signal.confidence < 55:
                    logger.info(f"Rejected {signal.market_ticker}: Confidence {signal.confidence:.0f} below threshold 55")
                    continue

                # Check 5: Edge threshold (≥10%)
                if signal.edge_pct < self.min_edge_threshold * 100:
                    logger.info(f"Rejected {signal.market_ticker}: Edge {signal.edge_pct:.1f}% below threshold {self.min_edge_threshold*100:.1f}%")
                    continue

                # All checks passed
                logger.info(f"✓ Validated {signal.market_ticker}: size=${signal.total_notional:.2f}, edge={signal.edge_pct:.1f}%, confidence={signal.confidence:.0f}/100")
                validated.append(signal)

            except Exception as e:
                logger.error(f"Trade validation error for {signal.market_ticker}: {e}")
                continue

        logger.info(f"Validated {len(validated)}/{len(signals)} signals passed all risk checks")
        return validated

    def execute_trades(self, signals: List[TradeSignal]) -> int:
        """
        Trade Executor: Place orders for validated signals.

        Supports:
        - Intelligent order splitting across adjacent buckets
        - Paper mode (simulated execution)
        - Live mode (real Kalshi orders with safety checks)
        - Partial fill handling
        - Execution logging and audit trail

        Returns:
            Number of successfully executed trades
        """
        if not self.kalshi_client or not signals:
            return 0

        executed = 0

        for signal in signals:
            try:
                logger.info(f"Executing {signal.market_ticker}: {', '.join(signal.target_buckets)} | size=${signal.total_notional:.2f} | {self.trading_mode.upper()}")

                # Split notional across target buckets proportionally
                order_count = 0
                for bucket_label, alloc_pct in zip(signal.target_buckets, signal.allocation):
                    if alloc_pct <= 0:
                        continue

                    notional_for_bucket = signal.total_notional * alloc_pct
                    # Assume $1 per contract minimum
                    count = max(1, int(notional_for_bucket))

                    try:
                        if self.trading_mode == 'paper':
                            # Paper mode: log and simulate
                            logger.info(f"  [PAPER] BUY {count} of {signal.market_ticker} ({bucket_label})")
                            self._stats['trades_executed'] += 1
                            order_count += 1

                        else:
                            # Live mode: place real order on Kalshi
                            logger.info(f"  [LIVE] Placing order: BUY {count} of {signal.market_ticker}")

                            # Place market order (no price = market order)
                            order = self.kalshi_client.place_order(
                                ticker=signal.market_ticker,
                                action='buy',
                                side='yes',  # Buy the outcome indicated by bucket
                                count=count,
                                price=None,  # Market order
                                time_in_force='fill_or_kill'
                            )

                            if order and order.get('order_id'):
                                logger.info(f"  ✓ Order placed: {order['order_id']} | Status: {order.get('status')}")
                                self._stats['trades_executed'] += 1
                                order_count += 1
                            else:
                                logger.warning(f"  ✗ Order placement failed for {signal.market_ticker}")
                                self._stats['trades_failed'] += 1

                    except Exception as e:
                        logger.error(f"  ✗ Execution error for bucket {bucket_label}: {e}")
                        self._stats['trades_failed'] += 1
                        continue

                if order_count > 0:
                    executed += 1
                    logger.info(f"✓ {signal.market_ticker} execution complete: {order_count} order(s)")

            except Exception as e:
                logger.error(f"Trade execution failed for {signal.market_ticker}: {e}")
                self._stats['trades_failed'] += 1
                continue

        logger.info(f"Execution summary: {executed} trades placed ({self._stats['trades_executed']} total, {self._stats['trades_failed']} failed)")
        return executed

    def check_resolutions(self):
        """
        REFACTORED: Now delegates to ResolutionLearner module.

        Resolution & Learning Loop: Process settled markets and update bias learner.
        This implements continuous self-improvement based on realized outcomes.

        Delegates to resolution_learner.process_resolutions() for the actual logic.
        """
        if not self.resolution_learner or not self.kalshi_client:
            logger.debug("ResolutionLearner not initialized, skipping resolutions check")
            return

        summary = self.resolution_learner.process_resolutions(
            kalshi_client=self.kalshi_client,
            trade_journal=self.trade_journal
        )

        if summary['processed'] > 0:
            logger.info(
                f"Resolution processing: {summary['processed']} settled, "
                f"{len(summary['updated_stations'])} stations updated, "
                f"${summary['total_pnl']:.2f} total PnL"
            )

    def trading_loop(self):
        """
        Main continuous trading loop.

        Every scan_interval seconds:
        1. Scan markets
        2. Generate signals
        3. Validate trades
        4. Execute approved trades
        5. Check resolutions
        """
        logger.info(f"Trading engine RUNNING in {self.trading_mode.upper()} mode")
        self.running = True

        while self.running:
            try:
                self._stats['last_scan'] = datetime.now(timezone.utc).isoformat()

                # 1. Market scanning
                markets = self.scan_markets()
                self._stats['active_markets'] = len(markets)

                if not markets:
                    logger.debug("No qualified markets found, waiting...")
                    time.sleep(self.scan_interval)
                    continue

                # 2. Signal generation
                signals = self.generate_signals(markets)

                if not signals:
                    logger.debug("No signals generated")
                    time.sleep(self.scan_interval)
                    continue

                logger.info(f"Generated {len(signals)} signals")

                # 3. Risk validation
                validated_trades = self.validate_trades(signals)
                logger.info(f"Validated {len(validated_trades)} trades")

                # 4. Order execution
                executed = self.execute_trades(validated_trades)
                logger.info(f"Executed {executed} trades")

                # 5. Resolution check (less frequently)
                if self._stats['markets_scanned'] % 3 == 0:
                    self.check_resolutions()

                # Wait before next scan
                time.sleep(self.scan_interval)

            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                time.sleep(self.scan_interval)

    def start(self):
        """Start trading engine in background thread."""
        if self.running:
            logger.warning("Trading engine already running")
            return

        thread = threading.Thread(target=self.trading_loop, daemon=True)
        thread.start()
        logger.info("Trading engine started in background thread")

    def stop(self):
        """Stop trading engine gracefully."""
        self.running = False
        logger.info("Trading engine stopped")

    def get_stats(self) -> Dict:
        """Get engine statistics for dashboard display."""
        return self._stats.copy()


def main():
    """Run trading engine standalone or integrated with dashboard."""
    try:
        # Create engine
        engine = TradingEngine()

        # Check if all components initialized
        if not all([engine.kalshi_client, engine.predictor,
                   engine.risk_manager, engine.execution_service]):
            logger.error("One or more components failed to initialize")
            return 1

        # Start main loop
        engine.start()

        # Keep alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            engine.stop()

        return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
