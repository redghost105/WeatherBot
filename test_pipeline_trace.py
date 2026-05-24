#!/usr/bin/env python3
"""
Test pipeline trace: Full end-to-end trading system test with real market discovery.
Tests the complete flow: scan → generate signals → validate → execute.
"""

import os
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

from trading_engine import TradingEngine
from signal_generator import TradeSignal

def banner(title):
    """Print a formatted section banner."""
    line = "=" * 100
    logger.info(line)
    logger.info(f"  {title}")
    logger.info(line)

def test_full_pipeline():
    """Test 1: Full autonomous pipeline with real market discovery."""
    banner("TEST 1: FULL AUTONOMOUS PIPELINE")

    engine = TradingEngine()

    # Stage 1: Market Scanning
    logger.info("\n--- STAGE 1: MARKET SCANNING ---")
    markets = engine.scan_markets()
    logger.info(f"Found {len(markets)} qualified markets")

    if not markets:
        logger.warning("No markets found - cannot proceed with pipeline")
        return

    for market in markets[:3]:
        ticker = market.get('ticker')
        hours = market.get('hours_to_resolution', 'N/A')
        if isinstance(hours, float):
            hours = f"{hours:.1f}h"
        logger.info(f"  • {ticker}: {hours}")

    # Stage 2: Signal Generation
    logger.info("\n--- STAGE 2: SIGNAL GENERATION ---")
    signals = engine.generate_signals(markets)
    logger.info(f"Generated {len(signals)} trade signals")

    if not signals:
        logger.warning("No signals generated")
        return

    for signal in signals[:3]:
        logger.info(f"  • {signal.market_ticker}: edge={signal.edge_pct:.1f}%, confidence={signal.confidence:.0f}")

    # Stage 3: Risk Validation
    logger.info("\n--- STAGE 3: RISK VALIDATION ---")
    validated = engine.validate_trades(signals)
    logger.info(f"Validated {len(validated)} trades")

    for trade in validated[:3]:
        logger.info(f"  • {trade.market_ticker}: notional=${trade.total_notional:.1f}")

    # Stage 4: Execution
    logger.info("\n--- STAGE 4: PAPER TRADE EXECUTION ---")
    executed = engine.execute_trades(validated)
    logger.info(f"Executed {executed} paper trades")

    # Stage 5: Summary
    logger.info("\n--- STAGE 5: SUMMARY ---")
    logger.info(f"Pipeline complete:")
    logger.info(f"  • Markets scanned: {len(markets)}")
    logger.info(f"  • Signals generated: {len(signals)}")
    logger.info(f"  • Trades validated: {len(validated)}")
    logger.info(f"  • Trades executed: {executed}")

def test_forced_execution():
    """Test 2: Forced execution with injected signal (mock markets)."""
    banner("TEST 2: FORCED EXECUTION (WITH MOCK MARKETS)")

    engine = TradingEngine()

    # Create a mock market for testing
    mock_market = {
        'ticker': 'KXHIGHLAX-26MAY24-T69',
        'title': 'Will the **high temp in LA** be >69° on May 24, 2026?',
        'close_time': '2026-05-24T22:59:00Z',
        'hours_to_resolution': 10.0,
        'yes_bid': 40,
        'no_bid': 60,
    }

    # Inject a signal directly
    logger.info("\n--- INJECTING TEST SIGNAL ---")
    signal = TradeSignal(
        market_ticker='KXHIGHLAX-26MAY24-T69',
        city_name='LA',
        station_id='KLAX',
        target_buckets=['69-70'],
        allocation=[1.0],
        total_notional=5.0,
        edge_pct=15.0,
        confidence=75.0,
        reasoning='Forced test signal for pipeline validation'
    )
    logger.info(f"Injected signal: {signal.market_ticker}")
    logger.info(f"  • Edge: {signal.edge_pct:.1f}%")
    logger.info(f"  • Confidence: {signal.confidence:.0f}")
    logger.info(f"  • Notional: ${signal.total_notional:.1f}")

    # Validate and execute
    logger.info("\n--- RISK VALIDATION ---")
    validated = engine.validate_trades([signal])
    logger.info(f"Validation result: {len(validated)} trades passed")

    logger.info("\n--- PAPER EXECUTION ---")
    executed = engine.execute_trades(validated)
    logger.info(f"Executed {executed} paper trades")

    if executed >= 1:
        logger.info("✓ Forced execution test PASSED")
    else:
        logger.warning("✗ Forced execution test FAILED")

def test_data_trace():
    """Test 3: Stage-by-stage data trace with raw output."""
    banner("TEST 3: DATA TRACE (WEATHER → SIGNALS → EXECUTION)")

    engine = TradingEngine()

    # Get a market to trace
    markets = engine.scan_markets()

    if not markets:
        logger.warning("No markets found for trace test")
        return

    market = markets[0]
    logger.info(f"\n--- TRACING MARKET: {market.get('ticker')} ---")
    logger.info(f"Title: {market.get('title')}")
    logger.info(f"Hours to close: {market.get('hours_to_resolution'):.1f}h")

    # Generate signals for this market
    logger.info("\n--- GENERATING SIGNALS ---")
    signals = engine.generate_signals([market])

    if signals:
        signal = signals[0]
        logger.info(f"Signal generated for {signal.market_ticker}")
        logger.info(f"  • Edge: {signal.edge_pct:.1f}%")
        logger.info(f"  • Confidence: {signal.confidence:.0f}")
        logger.info(f"  • Allocation: {signal.allocation}")
        logger.info(f"  • Reasoning: {signal.reasoning}")

        # Validate
        logger.info("\n--- VALIDATING TRADE ---")
        validated = engine.validate_trades([signal])
        if validated:
            logger.info(f"Trade validation PASSED")
        else:
            logger.warning(f"Trade validation FAILED")

        # Execute
        logger.info("\n--- EXECUTING ---")
        executed = engine.execute_trades(validated)
        logger.info(f"Executed {executed} paper trades")
    else:
        logger.warning("No signals generated for this market")

if __name__ == '__main__':
    logger.info("Starting Pipeline Trace Tests\n")

    try:
        test_full_pipeline()
        logger.info("\n" + "=" * 100 + "\n")

        test_forced_execution()
        logger.info("\n" + "=" * 100 + "\n")

        test_data_trace()
        logger.info("\n" + "=" * 100)
        logger.info("✓ All pipeline trace tests complete")
        logger.info("=" * 100)

    except Exception as e:
        logger.error(f"Test error: {e}", exc_info=True)
