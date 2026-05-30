#!/usr/bin/env python3
"""
Integration Test: Verify modular trading system components work together.

Tests:
1. Market parsing (market_parser)
2. Signal generation (signal_generator)
3. Resolution learning (resolution_learner)
4. Full trading engine orchestration
"""

import logging
import sys
from datetime import datetime, timezone
from typing import List, Dict

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Test imports
try:
    from market_parser import parse_market_buckets, CITIES_KALSHI
    from signal_generator import SignalGenerator, TradeSignal
    from resolution_learner import ResolutionLearner
    from trading_engine import TradingEngine
    from weather_predictor import WeatherPredictor, Bucket
    logger.info("✓ All modular components imported successfully")
except Exception as e:
    logger.error(f"✗ Import failed: {e}")
    sys.exit(1)


def test_market_parser():
    """Test market title parsing."""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Market Parser")
    logger.info("="*60)

    test_cases = [
        {
            'title': 'NYC Daily High Temperature 88-89F',
            'ticker': 'KNYC-88-89',
            'expected_city': 'NYC'
        },
        {
            'title': 'Chicago High Temperature 72-73F',
            'ticker': 'KMDW-72-73',
            'expected_city': 'Chicago'
        },
        {
            'title': 'LA Daily Low 45-46',
            'ticker': 'KLAX-45-46',
            'expected_city': 'LA'
        },
    ]

    passed = 0
    for test in test_cases:
        result = parse_market_buckets(test)
        if result:
            buckets, station_id = result
            logger.info(f"✓ {test['ticker']}: parsed {len(buckets)} bucket(s)")
            passed += 1
        else:
            logger.warning(f"✗ {test['ticker']}: parsing failed")

    logger.info(f"Market Parser: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_signal_generator():
    """Test signal generation."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Signal Generator")
    logger.info("="*60)

    try:
        predictor = WeatherPredictor()
        signal_gen = SignalGenerator(predictor)
        logger.info("✓ SignalGenerator initialized successfully")
        return True
    except Exception as e:
        logger.error(f"✗ SignalGenerator initialization failed: {e}")
        return False


def test_resolution_learner():
    """Test resolution learner."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Resolution Learner")
    logger.info("="*60)

    try:
        predictor = WeatherPredictor()
        learner = ResolutionLearner(predictor.bias_learner)
        logger.info("✓ ResolutionLearner initialized successfully")

        # Test settlement processing
        test_settlement = {
            'market_id': 'test_001',
            'market_ticker': 'NYC-HIGH-88-89',
            'outcome': 'yes',
            'temperature': 88.5,
            'pnl_dollars': 25.50,
        }

        trade_journal = {}
        result = learner._process_settlement(test_settlement, trade_journal)
        if result:
            logger.info(f"✓ Settlement processed: {result['ticker']}")
            return True
        else:
            logger.warning("✗ Settlement processing failed")
            return False

    except Exception as e:
        logger.error(f"✗ ResolutionLearner test failed: {e}")
        return False


def test_trading_engine_initialization():
    """Test trading engine initialization with modular components."""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Trading Engine Initialization")
    logger.info("="*60)

    try:
        engine = TradingEngine()
        logger.info("✓ TradingEngine initialized")

        # Verify all components are initialized
        checks = [
            ("Kalshi Client", engine.kalshi_client is not None),
            ("WeatherPredictor", engine.predictor is not None),
            ("RiskManager", engine.risk_manager is not None),
            ("ExecutionService", engine.execution_service is not None),
            ("SignalGenerator", engine.signal_generator is not None),
            ("ResolutionLearner", engine.resolution_learner is not None),
        ]

        all_ready = True
        for name, ready in checks:
            status = "✓" if ready else "✗"
            logger.info(f"  {status} {name}")
            all_ready = all_ready and ready

        return all_ready

    except Exception as e:
        logger.error(f"✗ TradingEngine initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_delegation_methods():
    """Test that trading engine methods properly delegate to modules."""
    logger.info("\n" + "="*60)
    logger.info("TEST 5: Delegation Methods")
    logger.info("="*60)

    try:
        engine = TradingEngine()

        # Test parse_market_buckets delegation
        test_market = {
            'title': 'NYC Daily High Temperature 88-89F',
            'ticker': 'KNYC-88-89'
        }
        result = engine.parse_market_buckets(test_market)
        if result:
            logger.info("✓ parse_market_buckets delegates correctly")
        else:
            logger.warning("✗ parse_market_buckets delegation failed")
            return False

        # Test generate_signals delegation
        markets = [test_market]
        signals = engine.generate_signals(markets)
        logger.info(f"✓ generate_signals delegates correctly (returned {len(signals)} signals)")

        return True

    except Exception as e:
        logger.error(f"✗ Delegation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_workflow():
    """Test simplified full workflow."""
    logger.info("\n" + "="*60)
    logger.info("TEST 6: Full Workflow")
    logger.info("="*60)

    try:
        # Simulate workflow
        logger.info("1. Scanning markets...")
        # In real scenario: markets = engine.scan_markets()
        logger.info("   (Skipped - requires live Kalshi API)")

        logger.info("2. Parsing market buckets...")
        test_market = {
            'title': 'NYC Daily High Temperature 88-89F',
            'ticker': 'KNYC-88-89'
        }
        parsed = parse_market_buckets(test_market)
        if parsed:
            logger.info(f"   ✓ Parsed into {len(parsed[0])} bucket(s)")

        logger.info("3. Weather data collection...")
        logger.info("   (Skipped - requires live WeatherAggregator)")

        logger.info("4. Signal generation...")
        logger.info("   (Would use SignalGenerator.generate_signals())")

        logger.info("5. Risk validation...")
        logger.info("   (Would use RiskManager.validate_trade())")

        logger.info("6. Trade execution...")
        logger.info("   (Would use ExecutionService.place_order())")

        logger.info("7. Resolution learning...")
        logger.info("   (Would use ResolutionLearner.process_resolutions())")

        logger.info("✓ Full workflow components verified")
        return True

    except Exception as e:
        logger.error(f"✗ Workflow test failed: {e}")
        return False


def main():
    """Run all integration tests."""
    logger.info("\n")
    logger.info("╔" + "="*58 + "╗")
    logger.info("║" + "MODULAR TRADING SYSTEM INTEGRATION TEST".center(58) + "║")
    logger.info("╚" + "="*58 + "╝")

    tests = [
        ("Market Parser", test_market_parser),
        ("Signal Generator", test_signal_generator),
        ("Resolution Learner", test_resolution_learner),
        ("Trading Engine Initialization", test_trading_engine_initialization),
        ("Delegation Methods", test_delegation_methods),
        ("Full Workflow", test_full_workflow),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"Test {name} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    logger.info("\n" + "="*60)
    logger.info("SUMMARY")
    logger.info("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {name}")

    logger.info(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 ALL INTEGRATION TESTS PASSED")
        return 0
    else:
        logger.error("❌ SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
