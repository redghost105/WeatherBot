#!/usr/bin/env python3
"""Test suite for ExecutionService - Phase 8 validation."""

import logging
from datetime import datetime, timezone
from execution_service import (
    ExecutionService, ExecutionConfig, ExecutionMode, TradeSignal,
    OrderStatus
)
from kalshi_api_client import KalshiAPIClient
from weather_predictor import HistoricalBiasLearner

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Test configuration
API_KEY_ID = "c9d784b0-f004-413d-a380-205288096083"
PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAxQ9Da8JAoanhGNUbRYhmhpvYGOGSLJvWIYqp920KuHy8c+ta
ByiKce0wufkQVp1x0AOsQ+xCQ/5aIi7eOkaQFu4VXAXZ/Lo2fV8IGNbHDXUkFry3
Og5/S51IVWYNWVnCTNxlfeI6hAFQUV7maj/P1EPmfeAPOy9Rx151OB2wkP0QYmRq
4OGQWXlg9hY/3T+qNw0ngcX3hXTFzAMWX1X9DhYAzFtKv7ZXYMawkMVxh+RvHdSX
ei2Okk9zYzA2tdCri55vgiNKnYxoHFvL5euNm6DtSN69xiUGuMN3u6xgyKmMEyL/
kDmcMVpPfeDskhvYOKxPyHhmPmrDlPbJroRZTQIDAQABAoIBABlZA0UjMYkZ/vhg
wSdKilWaSku5CEJwsTSTT5WiExT0BpGqnmP5VQWeivwBC5b4naEyN8Bs7YEtgI6R
FMjONs6cRWcW4Zleoo+x36rCRcx3WvMJx0/SeZFSY/GINQNfRlz4pJ1ysjA0sw4k
dOMJ3kPhkA50+cCVL6HDhrR3LTUY/m/CP0UOKa01lpCLWMoUJ79UwLfqzSSxte31
WVyQ3O2acw5epAKjmoPIp8ulw1XDpJskl7CEmouTcnxiJ6vsVMCmWq+OEjs1zn6I
GAuy8DqlHk135mh2UW1zdsibq4nNczDL5IW6h4QCltp64Rgi7sdG1o3wL4lNctjM
C1o1BgECgYEA3tm9OVqeGh5tMpHRIjT3c5jkPv9T8k49HC1EIm06941CthmwgCQA
76YsmAMOekYb8XNr6YAY2JH4Dc/WGlz8dTm0VXQIUfuiw0jA7p8CreeNyla7QARj
SMQ280VkIJcQx0iMVTXAOXr2xaxm88YpEikPlSFSwRSdlF5QE27WicECgYEA4l9k
mJ0eBszVxOPgvYfSFpCpTTBI7lVwER+WdoeRl63o9E6lIan+QLHSC8o4fBmL7Sbw
4kwQnABH6EiRMjWaMHWnbzV/64kSGkdZUDHdhLv9fGQxlesoBh2zUf0Z57faVTZ7
iZFY2rWYmE0z5WQmjaGhxnkGvyxxpstN+QzU+o0CgYAhSwhhDC+4mTkZJ/3FjYI2
i+31l3G0LookroKSXh1EJJ+F0xqyWi6lnv7kivhbviOok+TYUqHjoRMdBSLod2Hk
JYXSim4/yUdMw47HV4wv7Psa8pAxBTbMBTxsZb6Ku+buzuDgThJ0w/EgIRyUaNNz
+hxw3DSf0fOk2d4+uP1mQQKBgQDN7l/SIeRl5UN2uKMDaCJrmrAZYxqFjj3Dpgu3
yj5dUL0COuUoCcAdVGaziQP3iTnsxKcQBoh5khvYKOPFXFPnT7DAj1fOikRomY2b
UbGmBWplFbSyIFmprq0poelGDc/WAxlBHXNKizbFHj5eqMwVvfswVXsYwLKnPH2z
WcQKJQKBgQC++BeONDvW3Lzg01POMOsWrv4L83mAXG2WR0AfWz1V3EDsm3t5NbFq
xQosKGrAaA43OOsSdHoqoS558o76AkqgrITuq5smNU7Lw5AS2UfKIPmHknoJIdrq
hIXJORCr9UfAkyHX1FqzTQGPZmS+/J3X4Y9y55AEI+UE0GDepJHN7g==
-----END RSA PRIVATE KEY-----"""

def test_paper_mode_basic():
    """Test ExecutionService in paper trading mode."""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Paper Trading Mode - Basic Order Placement")
    logger.info("="*80)

    # Setup
    kalshi = KalshiAPIClient(API_KEY_ID, PRIVATE_KEY)
    bias_learner = HistoricalBiasLearner(bias_file="test_bias.json", max_history=30)
    config = ExecutionConfig(mode=ExecutionMode.PAPER)
    service = ExecutionService(kalshi, bias_learner, config)

    # Create a trade signal
    signal = TradeSignal(
        ticker="KXHIGHNY-26MAY21-T75",
        city="New York City",
        bucket_label=">75°",
        action="buy",
        side="yes",
        suggested_size=5,
        model_probability=0.65,
        market_probability=0.55,
        edge_pct=0.18,
        confidence=78.5,
    )

    logger.info(f"\n📊 Trade Signal:")
    logger.info(f"  Ticker: {signal.ticker}")
    logger.info(f"  Action: {signal.action} {signal.side}")
    logger.info(f"  Size: {signal.suggested_size} contracts")
    logger.info(f"  Model Prob: {signal.model_probability:.2%} → Market: {signal.market_probability:.2%}")
    logger.info(f"  Edge: {signal.edge_pct:.1%} | Confidence: {signal.confidence:.1f}")

    # Place order
    success, order = service.place_order(signal)

    logger.info(f"\n✓ Order Placement Result:")
    logger.info(f"  Success: {success}")
    logger.info(f"  Order ID: {order.order_id}")
    logger.info(f"  Status: {order.status.value}")
    logger.info(f"  Filled Qty: {order.filled_quantity}/{order.count}")

    assert success, "Paper order should always succeed"
    assert order.status == OrderStatus.FILLED, "Paper orders should fill immediately"
    assert order.filled_quantity == order.count, "Paper orders should fill completely"

    logger.info(f"\n✓ TEST PASSED")
    return service


def test_signal_validation():
    """Test signal validation and rejection."""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Signal Validation & Rejection")
    logger.info("="*80)

    kalshi = KalshiAPIClient(API_KEY_ID, PRIVATE_KEY)
    bias_learner = HistoricalBiasLearner()
    config = ExecutionConfig(mode=ExecutionMode.PAPER)
    service = ExecutionService(kalshi, bias_learner, config)

    # Test 1: Low edge
    signal = TradeSignal(
        ticker="KXHIGHNY-26MAY21-T75",
        city="New York City",
        bucket_label=">75°",
        action="buy",
        side="yes",
        suggested_size=5,
        model_probability=0.52,
        market_probability=0.50,
        edge_pct=0.02,  # Too low!
        confidence=70.0,
    )

    is_valid, reason = service.validate_signal(signal)
    logger.info(f"\n✓ Low edge test: {is_valid} ({reason})")
    assert not is_valid and "threshold" in reason.lower()

    # Test 2: Low confidence
    signal.edge_pct = 0.15
    signal.confidence = 45.0  # Too low!

    is_valid, reason = service.validate_signal(signal)
    logger.info(f"✓ Low confidence test: {is_valid} ({reason})")
    assert not is_valid and "confidence" in reason.lower()

    # Test 3: Position size too large
    signal.confidence = 75.0
    signal.suggested_size = 50  # Exceeds limit!

    is_valid, reason = service.validate_signal(signal)
    logger.info(f"✓ Position size test: {is_valid} ({reason})")
    assert not is_valid and "size" in reason.lower()

    logger.info(f"\n✓ TEST PASSED")


def test_circuit_breaker():
    """Test circuit breaker functionality."""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Circuit Breaker Activation")
    logger.info("="*80)

    kalshi = KalshiAPIClient(API_KEY_ID, PRIVATE_KEY)
    bias_learner = HistoricalBiasLearner()
    config = ExecutionConfig(mode=ExecutionMode.PAPER, max_daily_loss=500.0)
    service = ExecutionService(kalshi, bias_learner, config)

    # Simulate daily loss
    service.daily_pnl = -600.0  # Exceeds limit

    signal = TradeSignal(
        ticker="KXHIGHNY-26MAY21-T75",
        city="New York City",
        bucket_label=">75°",
        action="buy",
        side="yes",
        suggested_size=5,
        model_probability=0.65,
        market_probability=0.55,
        edge_pct=0.18,
        confidence=78.5,
    )

    is_valid, reason = service.validate_signal(signal)
    logger.info(f"\n✓ Circuit breaker triggered: {not is_valid}")
    logger.info(f"  Reason: {reason}")
    logger.info(f"  Circuit broken: {service.is_circuit_broken}")

    assert not is_valid and service.is_circuit_broken
    logger.info(f"\n✓ TEST PASSED")


def test_position_tracking():
    """Test position lifecycle management."""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Position Tracking & Reconciliation")
    logger.info("="*80)

    kalshi = KalshiAPIClient(API_KEY_ID, PRIVATE_KEY)
    bias_learner = HistoricalBiasLearner()
    config = ExecutionConfig(mode=ExecutionMode.PAPER)
    service = ExecutionService(kalshi, bias_learner, config)

    # Place buy order
    signal = TradeSignal(
        ticker="KXHIGHNY-26MAY21-T75",
        city="New York City",
        bucket_label=">75°",
        action="buy",
        side="yes",
        suggested_size=5,
        model_probability=0.65,
        market_probability=0.55,
        edge_pct=0.18,
        confidence=78.5,
    )

    success, order = service.place_order(signal)
    service.update_positions()

    logger.info(f"\n✓ After buy order:")
    logger.info(f"  Positions: {len(service.positions)}")
    logger.info(f"  Position in {order.ticker}: {service.positions[order.ticker].count} contracts")

    assert order.ticker in service.positions
    assert service.positions[order.ticker].count == 5

    # Simulate resolution
    pnl = service.reconcile_resolution("KXHIGHNY-26MAY21-T75", 78.0)  # YES wins
    logger.info(f"\n✓ After resolution (78°):")
    logger.info(f"  Resolution PnL: {pnl} cents")
    logger.info(f"  Daily PnL: {service.daily_pnl} cents")

    logger.info(f"\n✓ TEST PASSED")


def main():
    """Run all tests."""
    logger.info("\n" + "="*100)
    logger.info("EXECUTION SERVICE TEST SUITE - Phase 8")
    logger.info("="*100)

    try:
        # Run tests
        test_paper_mode_basic()
        test_signal_validation()
        test_circuit_breaker()
        test_position_tracking()

        logger.info("\n" + "="*100)
        logger.info("✅ ALL TESTS PASSED")
        logger.info("="*100)
        logger.info("\nExecutionService is ready for production integration.")
        logger.info("Next steps:")
        logger.info("  1. Integrate with WeatherPredictor trade signals")
        logger.info("  2. Set up daily reconciliation job")
        logger.info("  3. Monitor audit journal for compliance")
        logger.info("  4. Enable live mode once tested thoroughly")

    except AssertionError as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        logger.error(f"\n❌ UNEXPECTED ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
