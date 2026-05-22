"""
Phase 12: Automated Trading Engine

Background process that continuously:
1. Scans Kalshi for active weather markets
2. Pulls fresh weather data from stations
3. Generates trade signals via WeatherPredictor
4. Validates trades with RiskManager
5. Executes orders (paper or live mode)
6. Learns from resolutions

Runs independently from dashboard - can be started/stopped separately.
Implements the systematic misprice-exploitation strategy from the article.
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
import json
import threading
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
from dotenv import load_dotenv
load_dotenv()


class TradingEngine:
    """
    Core automated trading engine.

    Runs as a continuous background process scanning markets,
    generating signals, validating risk, and executing trades.
    """

    def __init__(self):
        """Initialize trading engine with all dependencies."""
        self.running = False
        self.scan_interval = int(os.getenv('TRADING_SCAN_INTERVAL', '300'))  # 5 minutes default
        self.trading_mode = os.getenv('TRADING_MODE', 'paper').lower()
        self.min_edge_threshold = float(os.getenv('MIN_EDGE_THRESHOLD', '0.10'))

        logger.info(f"Trading Engine initializing in {self.trading_mode.upper()} mode")
        logger.info(f"Scan interval: {self.scan_interval}s, Min edge: {self.min_edge_threshold}")

        # Initialize components
        self.init_kalshi_client()
        self.init_predictor()
        self.init_risk_manager()
        self.init_execution_service()

        # Track engine state for dashboard
        self._stats = {
            'markets_scanned': 0,
            'signals_generated': 0,
            'trades_executed': 0,
            'trades_failed': 0,
            'last_scan': None,
            'active_markets': 0
        }

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
            self.risk_manager = RiskManager()
            logger.info("✓ RiskManager initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize risk manager: {e}")
            self.risk_manager = None

    def init_execution_service(self):
        """Initialize ExecutionService."""
        try:
            from execution_service import ExecutionService
            self.execution_service = ExecutionService(
                mode=self.trading_mode,
                kalshi_client=self.kalshi_client
            )
            logger.info("✓ ExecutionService initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize execution service: {e}")
            self.execution_service = None

    def scan_markets(self) -> List[Dict]:
        """
        Market Scanner: Discover active Kalshi weather markets.

        Filters:
        - Only configured cities (CITIES_KALSHI)
        - Time to resolution 18-30 hours (sweet spot)
        - Sufficient liquidity

        Returns:
            List of market dicts with metadata
        """
        if not self.kalshi_client:
            return []

        try:
            # Get all open markets
            markets = self.kalshi_client.get_markets(status='open')
            logger.debug(f"Found {len(markets)} open markets")

            # Filter to weather markets
            weather_markets = [
                m for m in markets
                if 'temp' in m.get('title', '').lower()
                or 'weather' in m.get('title', '').lower()
            ]

            # Filter by time window (18-30 hours to resolution)
            qualified = []
            now = datetime.now(timezone.utc)

            for market in weather_markets:
                try:
                    # Parse resolution time
                    resolution_ts = market.get('resolution_ts')
                    if not resolution_ts:
                        continue

                    # Convert to datetime (if in milliseconds)
                    if resolution_ts > 10**10:
                        resolution_dt = datetime.fromtimestamp(resolution_ts / 1000, tz=timezone.utc)
                    else:
                        resolution_dt = datetime.fromtimestamp(resolution_ts, tz=timezone.utc)

                    hours_to_resolution = (resolution_dt - now).total_seconds() / 3600

                    # 18-30 hour sweet spot
                    if 18 <= hours_to_resolution <= 30:
                        market['hours_to_resolution'] = hours_to_resolution
                        qualified.append(market)

                except Exception as e:
                    logger.debug(f"Error processing market {market.get('ticker')}: {e}")
                    continue

            self._stats['markets_scanned'] = len(qualified)
            logger.info(f"Qualified {len(qualified)} markets in 18-30 hour window")
            return qualified

        except Exception as e:
            logger.error(f"Market scan failed: {e}")
            return []

    def generate_signals(self, markets: List[Dict]) -> List[Dict]:
        """
        Signal Generator: Use WeatherPredictor to create trade signals.

        For each market:
        1. Get weather data for resolution station
        2. Generate probability distribution
        3. Calculate edge vs market prices
        4. Create signal if edge >= threshold

        Returns:
            List of signal dicts with trade recommendations
        """
        if not self.predictor or not markets:
            return []

        signals = []

        for market in markets:
            try:
                ticker = market.get('ticker')
                title = market.get('title', '')

                logger.debug(f"Generating signal for {ticker}")

                # TODO: Get weather data from weather_aggregator
                # TODO: Create buckets from market specifications
                # TODO: Call predictor.hybrid_bucket_probabilities()
                # TODO: Call predictor.calculate_edge()
                # TODO: Filter by min_edge_threshold

                # Placeholder: Signal generation not yet implemented
                # Will be wired when weather_aggregator is integrated

            except Exception as e:
                logger.error(f"Signal generation failed for {ticker}: {e}")
                continue

        self._stats['signals_generated'] = len(signals)
        return signals

    def validate_trades(self, signals: List[Dict]) -> List[Dict]:
        """
        Trade Validator: Use RiskManager to validate signals.

        Checks:
        - Global exposure limits
        - Per-city concentration limits
        - Daily loss limit not breached
        - Single trade size (3-4% of equity max)

        Returns:
            List of validated trade proposals
        """
        if not self.risk_manager or not signals:
            return []

        validated = []

        for signal in signals:
            try:
                # TODO: Call risk_manager.validate_trade(signal)
                # TODO: Check exposure limits
                # TODO: Check loss limits

                # Placeholder: Risk validation not yet implemented
                validated.append(signal)

            except Exception as e:
                logger.error(f"Trade validation failed: {e}")
                continue

        return validated

    def execute_trades(self, trades: List[Dict]) -> int:
        """
        Trade Executor: Place orders via ExecutionService.

        Handles:
        - Order construction
        - Paper mode simulation
        - Live mode safety checks
        - Execution logging

        Returns:
            Number of successfully executed trades
        """
        if not self.execution_service or not trades:
            return 0

        executed = 0

        for trade in trades:
            try:
                # TODO: Call execution_service.place_order()
                # TODO: Handle paper vs live mode
                # TODO: Log execution

                executed += 1
                self._stats['trades_executed'] += 1
                logger.info(f"Trade executed: {trade}")

            except Exception as e:
                logger.error(f"Trade execution failed: {e}")
                self._stats['trades_failed'] += 1
                continue

        return executed

    def check_resolutions(self):
        """
        Resolution & Learning Loop: Update from resolved markets.

        Periodically checks for resolved markets and:
        1. Fetches official outcome (NWS data)
        2. Calculates actual temperature
        3. Updates HistoricalBiasLearner
        4. Archives trade record with PnL
        """
        if not self.kalshi_client:
            return

        try:
            # TODO: Get settlements from portfolio
            # TODO: Match with trade records
            # TODO: Update bias learner
            # TODO: Log PnL

            logger.debug("Resolution check completed")

        except Exception as e:
            logger.error(f"Resolution check failed: {e}")

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
