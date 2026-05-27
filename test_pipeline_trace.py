#!/usr/bin/env python3
"""
Comprehensive pipeline trace test for autonomous trading system.

Verifies end-to-end flow:
- Real Open-Meteo weather API (no auth required)
- MockKalshiClient with deterministic market data (20% edge baked in)
- Full signal generation, validation, and paper execution
- Detailed logging at each stage to console and file

Three test scenarios:
1. Full autonomous loop (real weather, real market scanning logic)
2. Forced execution (synthetic signal guaranteed to pass all checks)
3. Stage-by-stage data trace (raw values at each transformation)
"""

import os
import sys
import logging
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import asdict

from dotenv import load_dotenv

# Local imports
from trading_engine import TradingEngine
from signal_generator import TradeSignal
from weather_aggregator import WeatherAggregator
from market_parser import parse_market_buckets, CITIES_KALSHI, get_city_for_station
from weather_predictor import WeatherPredictor

load_dotenv()

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_trace_logging():
    """Configure logging to both console and file."""
    log_dir = Path.home() / "trading_logs"
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"pipeline_trace_{datetime.now().strftime('%Y-%m-%d')}.log"

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_fmt = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_fmt)
    root_logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_fmt)
    root_logger.addHandler(file_handler)

    return logging.getLogger(__name__), log_file


logger, log_file = setup_trace_logging()


def banner(title: str):
    """Print a section banner."""
    line = "=" * 100
    logger.info(line)
    logger.info(f"  {title}")
    logger.info(line)


# ============================================================================
# MOCK KALSHI CLIENT
# ============================================================================

class MockKalshiClient:
    """
    Deterministic mock Kalshi client for testing.

    Returns markets with ~37% market probability, which creates an 18%+ edge
    if our model predicts 55%+ on those buckets (well above 10% threshold).
    """

    def __init__(self):
        self.base_time = datetime.now(timezone.utc)

    def get_markets(self, **kwargs):
        """Return 2 test markets: NYC and Chicago high-temp buckets."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        return [
            {
                'ticker': 'KXHIGHNY-26MAY24-B88',
                'title': 'NYC Daily High Temperature 88-89F',
                'occurrence_datetime': tomorrow.isoformat(),
                'close_time': (tomorrow - timedelta(hours=2)).isoformat(),
                'status': 'open',
                'yes_bid': 35,
                'no_bid': 65,
            },
            {
                'ticker': 'KXHIGHCHI-26MAY24-B82',
                'title': 'Chicago High Temperature 82-83F',
                'occurrence_datetime': tomorrow.isoformat(),
                'close_time': (tomorrow - timedelta(hours=2)).isoformat(),
                'status': 'open',
                'yes_bid': 40,
                'no_bid': 60,
            }
        ]

    def get_orderbook(self, ticker):
        """Return orderbook with consistent ~37% market price."""
        return {
            'yes_dollars': [['37', '100']],
            'no_dollars': [['63', '100']],
        }

    def get_portfolio_balance(self):
        """Return mock portfolio with $1000 balance."""
        return {'balance': 100000, 'portfolio_value': 0}  # cents -> $1000

    def get_positions(self):
        """Return empty positions."""
        return []

    def get_account(self):
        """Return minimal account info."""
        return {
            'username': 'test_user',
            'email': 'test@example.com',
            'balance': 100000,
        }


# ============================================================================
# TEST 1: FULL AUTONOMOUS PIPELINE
# ============================================================================

def test_full_pipeline():
    """Test the complete autonomous pipeline with real weather and mock markets."""
    banner("TEST 1: FULL AUTONOMOUS PIPELINE")

    # Initialize engine with mock client
    logger.info("Initializing TradingEngine...")
    engine = TradingEngine()
    engine.kalshi_client = MockKalshiClient()
    logger.info(f"✓ Engine initialized with MockKalshiClient")

    # STAGE 1: Market Scanning
    banner("STAGE 1: MARKET SCANNING")
    logger.info("Scanning for markets in 18-30 hour window...")
    markets = engine.scan_markets()
    logger.info(f"Found {len(markets)} markets")
    for market in markets:
        ticker = market.get('ticker', 'UNKNOWN')
        close_time = market.get('close_time', 'UNKNOWN')
        logger.info(f"  • {ticker}: closes {close_time}")

    if not markets:
        logger.warning("No markets found, skipping remaining stages")
        return 0

    # STAGE 2: Signal Generation
    banner("STAGE 2: SIGNAL GENERATION")
    logger.info(f"Generating signals for {len(markets)} markets...")
    signals = engine.generate_signals(markets)
    logger.info(f"Generated {len(signals)} signal(s)")

    for signal in signals:
        logger.info(f"\n  Signal for {signal.market_ticker}:")
        logger.info(f"    City: {signal.city_name}")
        logger.info(f"    Buckets: {signal.target_buckets}")
        logger.info(f"    Edge: {signal.edge_pct:.1f}%")
        logger.info(f"    Confidence: {signal.confidence:.0f}%")
        logger.info(f"    Notional: ${signal.total_notional:.2f}")
        logger.info(f"    Reasoning: {signal.reasoning}")

    if not signals:
        logger.warning("No signals generated")
        return 0

    # STAGE 3: Risk Validation
    banner("STAGE 3: RISK VALIDATION")
    logger.info(f"Validating {len(signals)} signal(s)...")
    logger.info("  • Single trade size check (≤4% equity)")
    logger.info("  • Per-city concentration check (≤10% per city)")
    logger.info("  • Global exposure limit (≤25% total)")
    logger.info("  • Confidence threshold (≥55%)")
    logger.info("  • Edge threshold (≥10%)")

    validated = engine.validate_trades(signals)
    logger.info(f"✓ Passed all risk checks: {len(validated)} signal(s)")

    for signal in validated:
        logger.info(f"\n  ✓ {signal.market_ticker}")
        logger.info(f"    City: {signal.city_name}")
        logger.info(f"    Notional: ${signal.total_notional:.2f}")
        logger.info(f"    Confidence: {signal.confidence:.0f}%")
        logger.info(f"    Edge: {signal.edge_pct:.1f}%")

    if not validated:
        logger.warning("No signals passed validation")
        return 0

    # STAGE 4: Paper Trade Execution
    banner("STAGE 4: PAPER TRADE EXECUTION")
    logger.info(f"Executing {len(validated)} validated trade(s)...")
    executed = engine.execute_trades(validated)
    logger.info(f"Executed {executed} paper trade(s)")

    # STAGE 5: Summary
    banner("STAGE 5: SUMMARY")
    logger.info(f"Pipeline Complete:")
    logger.info(f"  • Markets scanned: {len(markets)}")
    logger.info(f"  • Signals generated: {len(signals)}")
    logger.info(f"  • Signals validated: {len(validated)}")
    logger.info(f"  • Trades executed: {executed}")

    return executed


# ============================================================================
# TEST 2: FORCED EXECUTION
# ============================================================================

def test_forced_execution():
    """Test execution of a hand-crafted signal that passes all checks."""
    banner("TEST 2: FORCED PAPER TRADE EXECUTION")

    # Create a signal with known-good values
    logger.info("Creating synthetic signal with guaranteed edge...")
    signal = TradeSignal(
        market_ticker='KXHIGHNY-26MAY24-B88',
        station_id='KNYC',
        city_name='NYC',
        target_buckets=['88-89', '89-90', '90-91'],
        allocation=[1.0/3.0, 1.0/3.0, 1.0/3.0],
        total_notional=5.0,           # $5, well under 4% of $1000
        edge_pct=18.5,                # 18.5% edge >> 10% threshold
        confidence=72.0,              # 72% confidence >> 55% threshold
        reasoning='Forced test: ensemble 60%, market 37% → 23% EV edge'
    )
    logger.info(f"Signal created: {signal.market_ticker}")
    logger.info(f"  Buckets: {signal.target_buckets}")
    logger.info(f"  Edge: {signal.edge_pct:.1f}%")
    logger.info(f"  Confidence: {signal.confidence:.0f}%")

    # Initialize engine with mock client
    logger.info("\nInitializing TradingEngine with mock Kalshi client...")
    engine = TradingEngine()
    engine.kalshi_client = MockKalshiClient()

    # Risk validation
    banner("RISK VALIDATION (forced signal)")
    logger.info("Validating forced signal against all 5 risk checks...")
    logger.info("  • Single trade size (≤4% equity)")
    logger.info("  • Per-city concentration (≤10%)")
    logger.info("  • Global exposure limit (≤25%)")
    logger.info("  • Confidence threshold (≥55%)")
    logger.info("  • Edge threshold (≥10%)")

    validated = engine.validate_trades([signal])

    if validated:
        result = validated[0]
        logger.info(f"\n✓ Signal passed all risk checks")
        logger.info(f"  Ticker: {result.market_ticker}")
        logger.info(f"  Confidence: {result.confidence:.0f}%")
        logger.info(f"  Edge: {result.edge_pct:.1f}%")
        logger.info(f"  Notional: ${result.total_notional:.2f}")
    else:
        logger.error("✗ Validation failed — signal rejected")
        return 0

    # Paper execution
    banner("PAPER EXECUTION (forced signal)")
    logger.info("Executing paper trade...")
    executed = engine.execute_trades(validated)

    if executed >= 1:
        logger.info(f"✓ Forced execution test PASSED — {executed} paper trade(s) confirmed")
        return executed
    else:
        logger.error("✗ Forced execution test FAILED — no paper trade executed")
        return 0


# ============================================================================
# TEST 3: STAGE-BY-STAGE DATA TRACE
# ============================================================================

def test_data_trace():
    """Detailed trace of data transformations through each stage."""
    banner("TEST 3: STAGE-BY-STAGE DATA TRACE")

    # Pick a city for detailed analysis (NYC)
    city_name = 'NYC'
    city_config = CITIES_KALSHI.get(city_name)
    station_id = 'KNYC'

    if not city_config:
        logger.error(f"Unknown city: {city_name}")
        return

    logger.info(f"Detailed trace for {city_name} (station: {station_id})")

    # STAGE A: Raw Weather Data
    banner("STAGE A: RAW WEATHER DATA (Open-Meteo)")
    logger.info("Fetching weather data from Open-Meteo API (free, no auth)...")
    agg = WeatherAggregator(cache_ttl_minutes=0)

    try:
        weather = agg.get_complete_weather_data(
            latitude=city_config['lat'],
            longitude=city_config['lon'],
            location_name=city_name,
            forecast_days=1,
            station_code=station_id
        )
    except Exception as e:
        logger.error(f"Failed to fetch weather: {e}")
        return

    if not weather or not weather.daily_forecast:
        logger.error("No weather data available")
        return

    daily = weather.daily_forecast[0]
    logger.info(f"\nDaily forecast:")
    logger.info(f"  Temperature (max): {daily.temperature_max:.1f}°C")
    logger.info(f"  Temperature (°F): {(daily.temperature_max * 9/5) + 32:.1f}°F")

    if weather.ensemble_forecast:
        ensemble = weather.ensemble_forecast[0]
        logger.info(f"\nEnsemble statistics:")
        logger.info(f"  Mean: {ensemble.temperature_mean:.1f}°C")
        logger.info(f"  Std dev: {ensemble.temperature_std:.2f}°C")
        logger.info(f"  Min: {ensemble.temperature_min:.1f}°C")
        logger.info(f"  Max: {ensemble.temperature_max:.1f}°C")

    # STAGE B: Market Buckets
    banner("STAGE B: AVAILABLE MARKET BUCKETS")
    mock_market = {
        'ticker': f'KXH{station_id[-2:]}-B',
        'title': f'{city_name} Daily High Temperature'
    }

    # Create sample buckets (88-89, 89-90, 90-91, etc. for NYC)
    from weather_predictor import Bucket
    sample_buckets = [
        Bucket(87.0, 88.0, '87-88'),
        Bucket(88.0, 89.0, '88-89'),
        Bucket(89.0, 90.0, '89-90'),
        Bucket(90.0, 91.0, '90-91'),
        Bucket(91.0, 92.0, '91-92'),
    ]

    logger.info(f"Available buckets in {city_name}:")
    for b in sample_buckets:
        logger.info(f"  {b.label}: {b.low:.1f}°F - {b.high:.1f}°F")

    # STAGE C: 3-Bin Selection Logic
    banner("STAGE C: 3-BIN STRATEGY SELECTION")
    predicted_temp_f = (daily.temperature_max * 9/5) + 32
    logger.info(f"Predicted max: {predicted_temp_f:.1f}°F")

    center_bucket = None
    center_index = None
    for i, bucket in enumerate(sample_buckets):
        if bucket.contains(predicted_temp_f):
            center_bucket = bucket
            center_index = i
            logger.info(f"  Center bucket: {bucket.label} (contains {predicted_temp_f:.1f}°F)")
            break

    if center_bucket and center_index is not None:
        bins_to_use = []
        if center_index > 0:
            bins_to_use.append(sample_buckets[center_index - 1].label)
        bins_to_use.append(center_bucket.label)
        if center_index < len(sample_buckets) - 1:
            bins_to_use.append(sample_buckets[center_index + 1].label)

        logger.info(f"  3-bin selection: {bins_to_use}")
    else:
        logger.warning(f"  Predicted temp {predicted_temp_f:.1f}°F not in any bucket")

    # STAGE D: Model Agreement Score
    banner("STAGE D: MODEL AGREEMENT CONFIDENCE")
    confidence_score = 95.0 if weather.ensemble_forecast[0].temperature_std <= 1.0 else \
                      85.0 if weather.ensemble_forecast[0].temperature_std <= 2.0 else \
                      75.0 if weather.ensemble_forecast[0].temperature_std <= 3.0 else 60.0

    logger.info(f"Confidence scoring based on ensemble std dev:")
    logger.info(f"  Ensemble std: {weather.ensemble_forecast[0].temperature_std:.2f}°C")
    logger.info(f"  Confidence score: {confidence_score:.0f}/100")

    # STAGE E: Price Filtering
    banner("STAGE E: PRICE FILTER VALIDATION")
    mock_market_prob = 0.37  # From MockKalshiClient
    logger.info(f"Market prices (from orderbook):")
    logger.info(f"  All bins at: ${mock_market_prob:.2f} each")

    sum_prices = mock_market_prob * 3 if center_bucket else 0
    logger.info(f"\n3-bin price check:")
    logger.info(f"  Sum of 3 bin prices: ${sum_prices:.2f}")
    logger.info(f"  Max allowed: $0.95")
    logger.info(f"  Status: {'✓ PASS' if sum_prices <= 0.95 else '✗ FAIL'}")

    per_bin_min = 0.01
    per_bin_max = 0.45
    logger.info(f"\nPer-bin price checks:")
    logger.info(f"  Min per bin: ${per_bin_min:.2f}")
    logger.info(f"  Max per bin: ${per_bin_max:.2f}")
    for p in [mock_market_prob] * 3:
        min_check = "✓ PASS" if p >= per_bin_min else "✗ FAIL"
        max_check = "✓ PASS" if p <= per_bin_max else "✗ FAIL"
        logger.info(f"  ${p:.2f}: {min_check} (>= $0.01), {max_check} (<= $0.45)")

    logger.info("\n" + "=" * 100)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Run all pipeline trace tests."""
    banner("POLYMARKET AUTONOMOUS TRADING SYSTEM - PIPELINE TRACE TEST")
    logger.info(f"Test started at: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Log file: {log_file}")

    try:
        # Test 1: Full autonomous pipeline
        executed_1 = test_full_pipeline()
        logger.info(f"\nTest 1 result: {executed_1} trades executed")

        # Test 2: Forced execution
        logger.info("\n")
        executed_2 = test_forced_execution()
        logger.info(f"\nTest 2 result: {executed_2} trades executed")

        # Test 3: Data trace
        logger.info("\n")
        test_data_trace()

        # Summary
        banner("PIPELINE TRACE COMPLETE")
        logger.info(f"Total trades executed across all tests: {executed_1 + executed_2}")
        logger.info(f"Test completed at: {datetime.now(timezone.utc).isoformat()}")
        logger.info(f"\nFull log available at: {log_file}")
        logger.info(f"Verify autonomous execution:")
        logger.info(f"  1. Check systemd service: systemctl status polymarket-trading")
        logger.info(f"  2. Check service logs: journalctl -u polymarket-trading -f")
        logger.info(f"  3. Review trade log: tail -f ~/trading_logs/trading_*.log")

    except Exception as e:
        logger.error(f"Pipeline trace failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
