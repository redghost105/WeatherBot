"""
Example: Risk-Gated Trading Flow

Demonstrates how RiskManager sits between WeatherPredictor signals
and ExecutionService to protect capital while enabling profitable trading.

Flow:
  WeatherPredictor → RiskManager.validate_trade() → ExecutionService.place_order()
"""

import logging
from datetime import datetime, timezone
from kalshi_api_client import KalshiAPIClient
from weather_predictor import WeatherPredictor, HistoricalBiasLearner
from execution_service import ExecutionService, ExecutionMode, TradeSignal, ExecutionConfig
from risk_manager import RiskManager, TradeProposal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def example_trade_flow():
    """
    Example showing a complete trade from signal generation through
    risk validation to execution.
    """
    print("\n" + "="*80)
    print("EXAMPLE: Risk-Gated Trading Flow")
    print("="*80)

    # ========================================================================
    # Setup: Initialize components
    # ========================================================================

    # Kalshi API client
    api_key = "YOUR_API_KEY_HERE"
    private_key = "YOUR_PRIVATE_KEY_HERE"
    kalshi = KalshiAPIClient(api_key, private_key)

    # Weather prediction engine with bias learning
    bias_learner = HistoricalBiasLearner()
    predictor = WeatherPredictor(bias_learner=bias_learner)

    # Risk manager - gatekeeper for all trades
    risk_manager = RiskManager(
        kalshi_client=kalshi,
        global_exposure_pct=0.25,        # 25% of equity
        per_city_exposure_pct=0.10,      # 10% per city
        single_trade_size_pct=0.04,      # 4% per trade
        soft_loss_threshold_pct=-0.05,   # Soft pause at -5%
        hard_loss_threshold_pct=-0.08,   # Hard halt at -8%
    )

    # Execution engine - places orders
    exec_config = ExecutionConfig(mode=ExecutionMode.PAPER)  # Paper mode for example
    executor = ExecutionService(kalshi, bias_learner, exec_config)

    print("✅ Components initialized:")
    print("   - KalshiAPIClient")
    print("   - WeatherPredictor with HistoricalBiasLearner")
    print("   - RiskManager (gatekeeper)")
    print("   - ExecutionService (executor)")

    # ========================================================================
    # Scenario 1: Strong Signal That Passes All Risk Checks
    # ========================================================================

    print("\n" + "-"*80)
    print("SCENARIO 1: Strong Signal with Good Risk Profile")
    print("-"*80)

    # Signal from WeatherPredictor: NYC temperature will exceed 75°
    signal_1 = TradeSignal(
        ticker="KXHIGHNY-26MAY21-T75",
        city="New York City",
        bucket_label=">75°",
        action="buy",
        side="yes",
        suggested_size=100,
        model_probability=0.65,      # Model says 65% chance
        market_probability=0.55,     # Market prices in 55%
        edge_pct=0.10,               # 10% edge (65% - 55%)
        confidence=85.0,             # High confidence
        timestamp=datetime.now(timezone.utc)
    )

    print(f"Signal received: {signal_1.city} {signal_1.bucket_label}")
    print(f"  Model prob: {signal_1.model_probability*100:.0f}%")
    print(f"  Market prob: {signal_1.market_probability*100:.0f}%")
    print(f"  Edge: {signal_1.edge_pct*100:.0f}% | Confidence: {signal_1.confidence:.0f}/100")

    # Convert to risk proposal
    proposal_1 = TradeProposal(
        ticker=signal_1.ticker,
        city=signal_1.city,
        side=signal_1.side,
        action=signal_1.action,
        size_contracts=signal_1.suggested_size,
        edge_pct=signal_1.edge_pct,
        confidence=signal_1.confidence,
        signal=signal_1
    )

    # Validate through RiskManager
    risk_result_1 = risk_manager.validate_trade(proposal_1)

    if risk_result_1.approved:
        print(f"✅ RISK CHECK PASSED: {risk_result_1.reason}")
        print(f"   Portfolio state: ${risk_result_1.portfolio_state.equity_cents()/100:.2f}")

        # Execute the trade
        success, order = executor.place_order(signal_1)
        if success:
            print(f"✅ ORDER EXECUTED: {order.order_id}")
            risk_manager.log_trade_executed(proposal_1)
        else:
            print(f"❌ ORDER FAILED: {order}")
    else:
        print(f"❌ RISK CHECK FAILED: {risk_result_1.reason}")
        print(f"   Violations: {', '.join(risk_result_1.checks_failed)}")

    # ========================================================================
    # Scenario 2: Weak Edge (Below Threshold)
    # ========================================================================

    print("\n" + "-"*80)
    print("SCENARIO 2: Weak Edge (Low Risk/Reward Ratio)")
    print("-"*80)

    # Chicago signal with weak edge
    signal_2 = TradeSignal(
        ticker="KXHIGHCHI-26MAY21-T65",
        city="Chicago",
        bucket_label=">65°",
        action="buy",
        side="yes",
        suggested_size=150,
        model_probability=0.52,      # Marginal edge
        market_probability=0.50,     # Only 2% edge
        edge_pct=0.02,               # Weak!
        confidence=55.0,             # Lower confidence
        timestamp=datetime.now(timezone.utc)
    )

    print(f"Signal received: {signal_2.city} {signal_2.bucket_label}")
    print(f"  Model prob: {signal_2.model_probability*100:.0f}%")
    print(f"  Market prob: {signal_2.market_probability*100:.0f}%")
    print(f"  Edge: {signal_2.edge_pct*100:.0f}% | Confidence: {signal_2.confidence:.0f}/100")

    proposal_2 = TradeProposal(
        ticker=signal_2.ticker,
        city=signal_2.city,
        side=signal_2.side,
        action=signal_2.action,
        size_contracts=signal_2.suggested_size,
        edge_pct=signal_2.edge_pct,
        confidence=signal_2.confidence,
        signal=signal_2
    )

    risk_result_2 = risk_manager.validate_trade(proposal_2)

    if risk_result_2.approved:
        print(f"✅ RISK CHECK PASSED: {risk_result_2.reason}")
        print(f"   Note: Trade approved even with weak edge (risk manager")
        print(f"   doesn't have edge minimum, that's WeatherPredictor's job)")
        print(f"   Action: Would still execute per risk rules")
    else:
        print(f"❌ RISK CHECK FAILED: {risk_result_2.reason}")

    # ========================================================================
    # Scenario 3: Oversized Trade (Exceeds Limit)
    # ========================================================================

    print("\n" + "-"*80)
    print("SCENARIO 3: Oversized Trade (Exceeds Size Limit)")
    print("-"*80)

    signal_3 = TradeSignal(
        ticker="KXHIGHLA-26MAY21-T85",
        city="Los Angeles",
        bucket_label=">85°",
        action="buy",
        side="yes",
        suggested_size=5000,         # WAY TOO BIG!
        model_probability=0.68,
        market_probability=0.55,
        edge_pct=0.13,
        confidence=78.0,
        timestamp=datetime.now(timezone.utc)
    )

    print(f"Signal received: {signal_3.city} {signal_3.bucket_label}")
    print(f"  Suggested size: {signal_3.suggested_size} contracts (too large!)")
    print(f"  Edge: {signal_3.edge_pct*100:.0f}% | Confidence: {signal_3.confidence:.0f}/100")

    proposal_3 = TradeProposal(
        ticker=signal_3.ticker,
        city=signal_3.city,
        side=signal_3.side,
        action=signal_3.action,
        size_contracts=signal_3.suggested_size,
        edge_pct=signal_3.edge_pct,
        confidence=signal_3.confidence,
        signal=signal_3
    )

    risk_result_3 = risk_manager.validate_trade(proposal_3)

    if risk_result_3.approved:
        print(f"✅ RISK CHECK PASSED: {risk_result_3.reason}")
    else:
        print(f"❌ RISK CHECK FAILED: {risk_result_3.reason}")
        print(f"   Violations: {', '.join(risk_result_3.checks_failed)}")
        print(f"   Action: Trade rejected - cannot place")

    # ========================================================================
    # Scenario 4: Circuit Breaker Active
    # ========================================================================

    print("\n" + "-"*80)
    print("SCENARIO 4: Circuit Breaker Active (All Trades Rejected)")
    print("-"*80)

    # Activate circuit breaker for demonstration
    risk_manager.manual_pause = True
    print("🛑 Manual pause activated by operator")

    signal_4 = TradeSignal(
        ticker="KXHIGHDEN-26MAY21-T60",
        city="Denver",
        bucket_label=">60°",
        action="buy",
        side="yes",
        suggested_size=50,
        model_probability=0.70,
        market_probability=0.60,
        edge_pct=0.10,
        confidence=80.0,
        timestamp=datetime.now(timezone.utc)
    )

    print(f"Signal received: {signal_4.city} {signal_4.bucket_label}")

    proposal_4 = TradeProposal(
        ticker=signal_4.ticker,
        city=signal_4.city,
        side=signal_4.side,
        action=signal_4.action,
        size_contracts=signal_4.suggested_size,
        edge_pct=signal_4.edge_pct,
        confidence=signal_4.confidence,
        signal=signal_4
    )

    risk_result_4 = risk_manager.validate_trade(proposal_4)

    print(f"❌ RISK CHECK FAILED: {risk_result_4.reason}")
    print(f"   Action: Trade rejected due to manual pause")

    # Reset for next scenario
    risk_manager.manual_pause = False
    print("✅ Manual pause disabled")

    # ========================================================================
    # Summary
    # ========================================================================

    print("\n" + "="*80)
    print("SUMMARY: Risk-Gated Trading Flow")
    print("="*80)

    summary = risk_manager.get_summary()
    print(f"\nPortfolio State:")
    if summary['portfolio_state']:
        ps = summary['portfolio_state']
        print(f"  Equity: ${ps['balance_cents']/100 + ps['portfolio_value_cents']/100:.2f}")
        print(f"  Available: ${ps['balance_cents']/100:.2f}")
        print(f"  Open Positions: {ps['total_open_positions']}")

    if summary['daily_state']:
        ds = summary['daily_state']
        print(f"\nDaily Tracking:")
        print(f"  Date: {ds['date']}")
        print(f"  Daily PnL: ${ds['daily_pnl_cents']/100:.2f}")
        print(f"  Trades Today: {ds['trades_placed_today']}")
        print(f"  Soft Pause: {'🟡 ACTIVE' if ds['soft_pause_active'] else '✅ Inactive'}")
        print(f"  Hard Pause: {'🛑 ACTIVE' if ds['hard_pause_active'] else '✅ Inactive'}")

    print(f"\nCircuit Breaker: {'🛑 ACTIVE' if summary['circuit_breaker_active'] else '✅ Inactive'}")
    print(f"API Failures: {summary['consecutive_api_failures']}/5")

    print(f"\nExposure by City:")
    for city, contracts in summary['open_positions_by_city'].items():
        print(f"  {city}: {contracts} contracts")

    print("\n" + "="*80)
    print("✅ Example complete - RiskManager in action!")
    print("="*80)


if __name__ == "__main__":
    example_trade_flow()
