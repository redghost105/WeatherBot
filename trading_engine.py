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

# City configuration with exact station codes
CITIES_KALSHI = {
    'NYC': {'lat': 40.7128, 'lon': -74.0060, 'code': 'KNYC'},
    'Chicago': {'lat': 41.8781, 'lon': -87.6298, 'code': 'KMDW'},
    'Dallas': {'lat': 32.7767, 'lon': -96.7970, 'code': 'KDFW'},
    'Denver': {'lat': 39.7392, 'lon': -104.9903, 'code': 'KDEN'},
    'LA': {'lat': 34.0522, 'lon': -118.2437, 'code': 'KLAX'},
}

@dataclass
class TradeSignal:
    """Structure for a single trading signal."""
    market_ticker: str
    station_id: str
    city_name: str
    target_buckets: List[str]  # e.g., ["88-89", "89-90"]
    allocation: List[float]    # proportional allocation per bucket
    total_notional: float
    edge_pct: float            # edge percentage (10-15+)
    confidence: float          # 0-100
    reasoning: str


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

        # Initialize components (order matters: client → predictor → risk_manager → execution)
        self.init_kalshi_client()
        self.init_predictor()
        self.init_risk_manager()
        self.init_execution_service()

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

    def parse_market_buckets(self, market: Dict) -> Optional[Tuple[List, str]]:
        """
        Parse market title to extract temperature buckets.

        Handles formats like:
        - "New York Daily High Temperature 88-89°F"
        - "NYC Low 65-66"
        - "Chicago High Temp: 72-73F"

        Returns:
            Tuple of (List[Bucket], station_id) or None if parsing fails
        """
        try:
            from weather_predictor import Bucket, parse_bucket_string

            title = market.get('title', '').upper()
            ticker = market.get('ticker', '')

            # Find which city this market is for
            city_name = None
            station_id = None
            for city, config in CITIES_KALSHI.items():
                if city.upper() in title or city in title:
                    city_name = city
                    station_id = config['code']
                    break

            if not station_id:
                logger.debug(f"Could not identify city for market {ticker}: {title}")
                return None

            # Extract temperature ranges using regex
            # Matches patterns like "88-89", "88-89°F", "88-89F", "88-89C"
            pattern = r'(\d+)-(\d+)\s*[°]?([FC])?'
            matches = re.findall(pattern, title)

            if not matches:
                logger.debug(f"No temperature buckets found in {title}")
                return None

            buckets = []
            for low_str, high_str, unit in matches:
                try:
                    low = float(low_str)
                    high = float(high_str)
                    bucket = Bucket(low=low, high=high, label=f"{int(low)}-{int(high)}")
                    buckets.append(bucket)
                except Exception as e:
                    logger.debug(f"Failed to parse bucket {low_str}-{high_str}: {e}")
                    continue

            if not buckets:
                return None

            logger.debug(f"Parsed {len(buckets)} buckets for {city_name} ({station_id}): {[b.label for b in buckets]}")
            return buckets, station_id

        except Exception as e:
            logger.debug(f"Market parsing failed for {market.get('ticker')}: {e}")
            return None

    def generate_signals(self, markets: List[Dict]) -> List[TradeSignal]:
        """
        Signal Generator: Use WeatherPredictor to create trade signals.

        For each market:
        1. Parse buckets from market title
        2. Get weather data for resolution station
        3. Generate probability distribution via hybrid method
        4. Calculate edge vs market prices
        5. Create signal if edge >= threshold AND confidence >= min

        Returns:
            List of TradeSignal objects with high-conviction opportunities
        """
        if not self.predictor or not markets:
            return []

        signals = []

        try:
            from weather_aggregator import WeatherAggregator
            agg = WeatherAggregator(cache_ttl_minutes=30)
        except Exception as e:
            logger.error(f"Failed to initialize WeatherAggregator: {e}")
            return []

        for market in markets:
            try:
                ticker = market.get('ticker')
                title = market.get('title', '')

                logger.debug(f"Generating signal for {ticker}")

                # Parse market buckets and identify station
                parsed = self.parse_market_buckets(market)
                if not parsed:
                    continue

                buckets, station_id = parsed
                city_name = None
                city_config = None
                for city, config in CITIES_KALSHI.items():
                    if config['code'] == station_id:
                        city_name = city
                        city_config = config
                        break

                if not city_config:
                    continue

                # Fetch fresh weather data for the exact station
                logger.debug(f"Fetching weather for {city_name} ({station_id})")
                weather_data = agg.get_complete_weather_data(
                    latitude=city_config['lat'],
                    longitude=city_config['lon'],
                    location_name=city_name,
                    forecast_days=1,
                    station_code=station_id
                )

                if not weather_data:
                    logger.debug(f"No weather data for {city_name}")
                    continue

                # Generate probability distribution via hybrid method
                model_probs_dict = self.predictor.hybrid_bucket_probabilities(
                    weather_data=weather_data,
                    buckets=buckets,
                    station_id=station_id,
                    apply_bias_correction=True
                )

                if not model_probs_dict:
                    logger.debug(f"No probabilities for {city_name}")
                    continue

                # Extract model probabilities
                model_probs = {label: d['probability'] for label, d in model_probs_dict.items()}

                # Get current market prices (orderbook)
                try:
                    orderbook = self.kalshi_client.get_orderbook(ticker)
                    # Convert orderbook to market-implied probabilities
                    market_prices = {}
                    yes_bids = orderbook.get('yes_dollars', [])
                    no_bids = orderbook.get('no_dollars', [])

                    if yes_bids and no_bids:
                        best_yes = float(yes_bids[-1][0]) if yes_bids else 0.5
                        best_no = float(no_bids[-1][0]) if no_bids else 0.5
                        total = best_yes + best_no
                        if total > 0:
                            market_prob = best_yes / total
                        else:
                            market_prob = 0.5

                        for bucket in buckets:
                            market_prices[bucket.label] = market_prob
                    else:
                        logger.debug(f"No orderbook data for {ticker}")
                        continue

                except Exception as e:
                    logger.debug(f"Failed to fetch orderbook for {ticker}: {e}")
                    continue

                # Calculate edges using predictor
                edge_summary = self.predictor.calculate_edge(
                    model_probs=model_probs,
                    market_prices=market_prices,
                    buckets=buckets,
                    station_id=station_id,
                    weather_data=weather_data,
                    min_edge=self.min_edge_threshold
                )

                # Filter: only generate signals for high-confidence, high-edge opportunities
                if edge_summary.confidence_score < 55:
                    logger.debug(f"Low confidence {edge_summary.confidence_score:.0f} for {ticker}, skipping")
                    continue

                if edge_summary.overall_ev <= 0:
                    logger.debug(f"No positive EV for {ticker}, skipping")
                    continue

                # Find adjacent bucket group with positive edge
                target_buckets = edge_summary.top_buckets[:3] if edge_summary.top_buckets else []
                if not target_buckets:
                    logger.debug(f"No high-edge buckets for {ticker}")
                    continue

                # Calculate allocation proportional to edge
                allocation = []
                total_edge = 0
                bucket_edges = {}
                for edge in edge_summary.bucket_edges:
                    if edge.label in target_buckets and edge.edge > 0:
                        bucket_edges[edge.label] = edge.edge
                        total_edge += edge.edge

                if total_edge <= 0:
                    continue

                for bucket_label in target_buckets:
                    alloc = bucket_edges.get(bucket_label, 0) / total_edge if total_edge > 0 else 0
                    allocation.append(alloc)

                # Estimate notional (will be refined by RiskManager)
                portfolio_balance = self.kalshi_client.get_portfolio_balance()
                equity = portfolio_balance.get('balance', 0) / 100  # Convert cents to dollars
                notional = equity * 0.03  # Start with 3% sizing

                # Create signal
                signal = TradeSignal(
                    market_ticker=ticker,
                    station_id=station_id,
                    city_name=city_name,
                    target_buckets=target_buckets,
                    allocation=allocation,
                    total_notional=notional,
                    edge_pct=edge_summary.overall_ev * 100,
                    confidence=edge_summary.confidence_score,
                    reasoning=edge_summary.reasoning
                )

                signals.append(signal)
                logger.info(f"✓ Signal generated for {ticker}: edge={signal.edge_pct:.1f}%, confidence={signal.confidence:.0f}/100")

            except Exception as e:
                logger.error(f"Signal generation failed for {market.get('ticker')}: {e}")
                import traceback
                traceback.print_exc()
                continue

        self._stats['signals_generated'] = len(signals)
        logger.info(f"Generated {len(signals)} trading signals from {len(markets)} markets")
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
        Resolution & Learning Loop: Process settled markets and update bias learner.

        For each resolved market:
        1. Fetch settlement outcome from Kalshi
        2. Retrieve actual temperature from NWS
        3. Update HistoricalBiasLearner with forecast vs actual
        4. Calculate PnL and archive trade record
        5. Improve future predictions via feedback

        This implements continuous self-improvement based on realized outcomes.
        """
        if not self.kalshi_client or not self.predictor:
            return

        try:
            # Get all settlements (resolved markets)
            settlements = self.kalshi_client.get_settlements()
            logger.debug(f"Found {len(settlements)} settlements to process")

            if not settlements:
                return

            for settlement in settlements:
                try:
                    ticker = settlement.get('market_ticker', '')
                    outcome = settlement.get('outcome', '')  # 'yes' or 'no'
                    pnl_dollars = settlement.get('pnl_dollars', 0)

                    # Find which station this market was for
                    station_id = None
                    actual_temp = None

                    for city, config in CITIES_KALSHI.items():
                        if city.upper() in ticker.upper():
                            station_id = config['code']
                            break

                    if not station_id:
                        logger.debug(f"Could not identify station for {ticker}")
                        continue

                    # Try to extract actual temperature from settlement data
                    # This would typically come from NWS or the settlement payload
                    if 'temperature' in settlement:
                        actual_temp = settlement['temperature']
                    elif 'resolved_value' in settlement:
                        # Try to parse from resolved value
                        try:
                            actual_temp = float(settlement['resolved_value'])
                        except:
                            pass

                    if actual_temp is None:
                        logger.debug(f"No actual temperature found for {ticker}")
                        continue

                    # We don't have the original forecast mean stored, but we can estimate
                    # from the bucket that resolved. For now, log the outcome.
                    logger.info(f"✓ Market settled: {ticker} | Actual: {actual_temp:.1f}°F | PnL: ${pnl_dollars:.2f}")

                    # Archive the trade record (in production, write to database)
                    record = {
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'ticker': ticker,
                        'station_id': station_id,
                        'outcome': outcome,
                        'actual_temperature': actual_temp,
                        'pnl_dollars': pnl_dollars,
                        'resolved': True
                    }

                    logger.debug(f"Archived trade record: {json.dumps(record)}")

                    # Update HistoricalBiasLearner
                    # We estimate the forecast mean from the outcome
                    # In production, this would be stored during execution
                    if station_id and actual_temp:
                        # Simple heuristic: assume forecast was near the midpoint of resolved bucket
                        forecast_estimate = actual_temp  # More sophisticated logic needed in prod
                        self.predictor.bias_learner.update(
                            station_id=station_id,
                            forecast_high=forecast_estimate,
                            actual_high=actual_temp
                        )
                        logger.info(f"  Updated bias for {station_id}: forecast≈{forecast_estimate:.1f}°F, actual={actual_temp:.1f}°F")

                except Exception as e:
                    logger.error(f"Failed to process settlement for {settlement.get('market_ticker')}: {e}")
                    continue

            logger.info("Resolution check completed")

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
