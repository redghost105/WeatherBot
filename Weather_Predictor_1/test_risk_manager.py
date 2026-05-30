"""
Comprehensive test suite for RiskManager.

Tests cover:
- Portfolio state tracking
- Global exposure limits
- Per-city exposure limits
- Single trade size limits
- Daily loss limits (soft/hard pause)
- Cluster correlation rules
- Circuit breakers (API, loss, manual)
- Trade validation logic
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from risk_manager import (
    RiskManager, TradeProposal, PortfolioState, DailyRiskState,
    RiskDecision, CircuitBreakerType, CITY_CLUSTERS
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def create_mock_kalshi_client(unrealized_pnl=0):
    """Create a mock Kalshi API client."""
    mock = Mock()
    mock.get_portfolio_balance = Mock(return_value={
        'balance': 1000000,  # $10,000 in cents
        'portfolio_value': 500000,  # $5,000 in cents
        'realized_pnl': 100000,  # $1,000 realized
        'unrealized_pnl': unrealized_pnl,  # Configurable, defaults to 0
    })
    mock.get_positions = Mock(return_value=[])
    return mock


# ============================================================================
# TEST 1: Basic RiskManager Initialization
# ============================================================================

def test_risk_manager_initialization():
    """Test RiskManager initializes with correct defaults."""
    print("\n" + "="*80)
    print("TEST 1: Basic RiskManager Initialization")
    print("="*80)

    mock_kalshi = create_mock_kalshi_client(unrealized_pnl=0)
    rm = RiskManager(mock_kalshi)

    assert rm.global_exposure_pct == 0.25
    assert rm.per_city_exposure_pct == 0.10
    assert rm.single_trade_size_pct == 0.04
    assert rm.soft_loss_threshold_pct == -0.05
    assert rm.hard_loss_threshold_pct == -0.08
    assert rm.manual_pause == False
    assert rm.circuit_breaker_active == False

    print("✅ RiskManager initialized with correct defaults")
    print("✅ Circuit breaker not active")
    print("✅ Manual pause disabled")


# ============================================================================
# TEST 2: Global Exposure Limit Enforcement
# ============================================================================

def test_global_exposure_limit():
    """Test global exposure limit is enforced."""
    print("\n" + "="*80)
    print("TEST 2: Global Exposure Limit Enforcement")
    print("="*80)

    mock_kalshi = create_mock_kalshi_client(unrealized_pnl=0)
    rm = RiskManager(mock_kalshi, global_exposure_pct=0.25)

    # Simulate initial portfolio state
    rm._refresh_portfolio_state()

    # Equity = 1,500,000 cents ($15,000)
    # Global limit = 25% = 375,000 cents
    # Each contract ≈ 50 cents, so ~7,500 contracts max

    proposal = TradeProposal(
        ticker="KXHIGHNY-26MAY21-T75",
        city="NYC",
        side="yes",
        action="buy",
        size_contracts=1000,  # Small initial trade
        edge_pct=0.10,
        confidence=75.0
    )

    result = rm.validate_trade(proposal)
    assert result.approved == True
    print(f"✅ Small trade (1000 contracts) approved: {result.reason}")

    # Now simulate very large position already open
    rm.open_positions_by_city["Chicago"] = 7000  # Chicago already has 7000 contracts
    rm.open_positions_by_city["NYC"] = 500  # NYC has 500 contracts

    proposal = TradeProposal(
        ticker="KXHIGHNY-26MAY21-T75",
        city="NYC",
        side="yes",
        action="buy",
        size_contracts=500,  # This would exceed global limit
        edge_pct=0.10,
        confidence=75.0
    )

    result = rm.validate_trade(proposal)
    assert result.approved == False
    assert "GLOBAL_EXPOSURE" in result.reason or "global_exposure" in str(result.checks_failed)
    print(f"✅ Large trade rejected when global limit exceeded: {result.reason}")


# ============================================================================
# TEST 3: Per-City Exposure Limit Enforcement
# ============================================================================

def test_per_city_exposure_limit():
    """Test per-city exposure limit is enforced."""
    print("\n" + "="*80)
    print("TEST 3: Per-City Exposure Limit Enforcement")
    print("="*80)

    mock_kalshi = create_mock_kalshi_client(unrealized_pnl=0)
    rm = RiskManager(mock_kalshi, per_city_exposure_pct=0.10)

    rm._refresh_portfolio_state()

    # Equity = 1,500,000 cents ($15,000)
    # Per-city limit = 10% = 150,000 cents ≈ 3,000 contracts

    # Simulate existing NYC position
    rm.open_positions_by_city["NYC"] = 2500

    proposal = TradeProposal(
        ticker="KXHIGHNY-26MAY21-T75",
        city="NYC",
        side="yes",
        action="buy",
        size_contracts=600,  # 2500 + 600 = 3100 > 3000 limit
        edge_pct=0.10,
        confidence=75.0
    )

    result = rm.validate_trade(proposal)
    assert result.approved == False
    assert "PER_CITY_EXPOSURE" in result.reason or "per_city" in str(result.checks_failed)
    print(f"✅ Trade rejected when per-city limit exceeded: {result.reason}")

    # Reduce to acceptable size
    proposal.size_contracts = 400
    result = rm.validate_trade(proposal)
    assert result.approved == True
    print(f"✅ Smaller trade within per-city limit approved: {result.reason}")


# ============================================================================
# TEST 4: Single Trade Size Limit Enforcement
# ============================================================================

def test_single_trade_size_limit():
    """Test single trade size limit is enforced."""
    print("\n" + "="*80)
    print("TEST 4: Single Trade Size Limit Enforcement")
    print("="*80)

    mock_kalshi = create_mock_kalshi_client(unrealized_pnl=0)
    rm = RiskManager(mock_kalshi, single_trade_size_pct=0.04)

    rm._refresh_portfolio_state()

    # Equity = 1,500,000 cents ($15,000)
    # Single trade limit = 4% = 60,000 cents ≈ 1,200 contracts

    proposal = TradeProposal(
        ticker="KXHIGHCHI-26MAY21-T65",
        city="Chicago",
        side="yes",
        action="buy",
        size_contracts=2000,  # Exceeds limit
        edge_pct=0.10,
        confidence=75.0
    )

    result = rm.validate_trade(proposal)
    assert result.approved == False
    assert "SINGLE_TRADE_SIZE" in result.reason or "single_trade" in str(result.checks_failed)
    print(f"✅ Large trade rejected when size limit exceeded: {result.reason}")

    # Smaller trade
    proposal.size_contracts = 800
    result = rm.validate_trade(proposal)
    assert result.approved == True
    print(f"✅ Smaller trade within size limit approved: {result.reason}")


# ============================================================================
# TEST 5: Manual Pause Flag Enforcement
# ============================================================================

def test_manual_pause():
    """Test manual pause flag prevents all trades."""
    print("\n" + "="*80)
    print("TEST 5: Manual Pause Flag Enforcement")
    print("="*80)

    mock_kalshi = create_mock_kalshi_client(unrealized_pnl=0)
    rm = RiskManager(mock_kalshi, manual_pause=True)

    proposal = TradeProposal(
        ticker="KXHIGHNY-26MAY21-T75",
        city="NYC",
        side="yes",
        action="buy",
        size_contracts=1,  # Even tiny trade
        edge_pct=0.10,
        confidence=75.0
    )

    result = rm.validate_trade(proposal)
    assert result.approved == False
    assert "MANUAL_PAUSE" in result.reason
    print(f"✅ All trades rejected when manual pause enabled: {result.reason}")

    # Disable manual pause
    rm.manual_pause = False
    rm._refresh_portfolio_state()
    result = rm.validate_trade(proposal)
    assert result.approved == True
    print(f"✅ Trades approved after manual pause disabled: {result.reason}")


# ============================================================================
# TEST 6: Circuit Breaker - API Health
# ============================================================================

def test_circuit_breaker_api_health():
    """Test API health circuit breaker after 5 failures."""
    print("\n" + "="*80)
    print("TEST 6: Circuit Breaker - API Health")
    print("="*80)

    mock_kalshi = Mock()
    mock_kalshi.get_portfolio_balance = Mock(return_value=None)  # Simulate failure
    mock_kalshi.get_positions = Mock(return_value=None)

    rm = RiskManager(mock_kalshi)

    # Trigger 5 consecutive failures
    for i in range(5):
        rm._refresh_portfolio_state()
        print(f"  API failure {i+1}/5 - consecutive_failures={rm.consecutive_api_failures}")

    assert rm.circuit_breaker_active == True
    assert rm.circuit_breaker_type == CircuitBreakerType.API_HEALTH
    print("✅ Circuit breaker activated after 5 API failures")

    proposal = TradeProposal(
        ticker="KXHIGHNY-26MAY21-T75",
        city="NYC",
        side="yes",
        action="buy",
        size_contracts=100,
        edge_pct=0.10,
        confidence=75.0
    )

    result = rm.validate_trade(proposal)
    assert result.approved == False
    assert result.decision == RiskDecision.CIRCUIT_BROKEN
    print(f"✅ Trades rejected when circuit breaker active: {result.reason}")

    # Test manual reset
    rm.reset_circuit_breaker()
    assert rm.circuit_breaker_active == False
    print("✅ Circuit breaker reset manually")


# ============================================================================
# TEST 7: Soft and Hard Daily Loss Limits
# ============================================================================

def test_daily_loss_limits():
    """Test soft (-5%) and hard (-8%) daily loss limits."""
    print("\n" + "="*80)
    print("TEST 7: Soft and Hard Daily Loss Limits")
    print("="*80)

    mock_kalshi = create_mock_kalshi_client(unrealized_pnl=0)
    rm = RiskManager(mock_kalshi)

    rm._refresh_portfolio_state()
    initial_equity = rm.portfolio_state.equity_cents()
    print(f"Initial equity: ${initial_equity/100:.2f}")

    # Initialize daily state
    rm._init_daily_state()
    assert rm.daily_state.soft_pause_active == False
    assert rm.daily_state.hard_pause_active == False
    print("✅ Daily state initialized: soft and hard pause inactive")

    # Simulate -3% loss (below soft threshold)
    rm.portfolio_state.realized_pnl_cents = -45000  # -$450
    rm._update_daily_pnl()
    assert rm.daily_state.soft_pause_active == False
    print("✅ -3% loss: soft pause not triggered")

    # Simulate -6% loss (triggers soft pause)
    rm.portfolio_state.realized_pnl_cents = -90000  # -$900
    rm._update_daily_pnl()
    assert rm.daily_state.soft_pause_active == True
    print("✅ -6% loss: soft pause triggered ⚠️")

    # Check that soft pause allows trades with warning
    proposal = TradeProposal(
        ticker="KXHIGHNY-26MAY21-T75",
        city="NYC",
        side="yes",
        action="buy",
        size_contracts=100,
        edge_pct=0.10,
        confidence=75.0
    )

    result = rm.validate_trade(proposal)
    assert result.approved == True  # Soft pause allows trades
    assert any("SOFT PAUSE" in log for log in result.logs)
    print("✅ Soft pause: trades allowed with warning")

    # Simulate -9% loss (triggers hard pause)
    rm.daily_state.hard_pause_active = False  # Reset
    rm.portfolio_state.realized_pnl_cents = -135000  # -$1350 = -9%
    rm._update_daily_pnl()
    assert rm.daily_state.hard_pause_active == True
    assert rm.circuit_breaker_active == True
    print("✅ -9% loss: hard pause triggered 🛑")

    # Check that hard pause rejects all trades
    result = rm.validate_trade(proposal)
    assert result.approved == False
    print("✅ Hard pause: all trades rejected")


# ============================================================================
# TEST 8: Cluster Correlation Rule
# ============================================================================

def test_cluster_correlation():
    """Test size reduction for correlated city clusters."""
    print("\n" + "="*80)
    print("TEST 8: Cluster Correlation Rule")
    print("="*80)

    mock_kalshi = create_mock_kalshi_client(unrealized_pnl=0)
    rm = RiskManager(mock_kalshi, cluster_correlation_reduction=0.50)

    rm._refresh_portfolio_state()

    # Setup: East Coast cluster cities have positions
    rm.open_positions_by_city["NYC"] = 100
    rm.open_positions_by_city["Boston"] = 100
    # Now Philadelphia also wants to trade

    proposal = TradeProposal(
        ticker="KXHIGHPHI-26MAY21-T70",
        city="Philadelphia",
        side="yes",
        action="buy",
        size_contracts=100,  # Requested size
        edge_pct=0.10,
        confidence=75.0
    )

    # Validate - should trigger correlation check and reduce size
    adjusted_size = rm._check_cluster_correlation(proposal)
    assert adjusted_size == 50  # 50% reduction
    print(f"✅ Correlation detected in East Coast cluster: 100 → {adjusted_size} contracts (50% reduction)")

    # Now test with no correlation
    rm.open_positions_by_city.clear()
    rm.open_positions_by_city["Chicago"] = 100  # Only one Midwest city

    proposal = TradeProposal(
        ticker="KXHIGHDET-26MAY21-T65",
        city="Detroit",
        side="yes",
        action="buy",
        size_contracts=100,
        edge_pct=0.10,
        confidence=75.0
    )

    adjusted_size = rm._check_cluster_correlation(proposal)
    assert adjusted_size == 100  # No reduction
    print(f"✅ No correlation with single other city: 100 → {adjusted_size} contracts (no reduction)")


# ============================================================================
# TEST 9: State Persistence
# ============================================================================

def test_state_persistence():
    """Test saving and loading state to JSON."""
    print("\n" + "="*80)
    print("TEST 9: State Persistence")
    print("="*80)

    state_file = Path("/tmp/test_risk_manager_state.json")
    if state_file.exists():
        state_file.unlink()

    # Create manager with circuit breaker active
    mock_kalshi = create_mock_kalshi_client(unrealized_pnl=0)
    rm1 = RiskManager(mock_kalshi, state_file=str(state_file))

    rm1._refresh_portfolio_state()
    rm1._init_daily_state()
    rm1.daily_state.trades_placed_today = 5
    rm1.circuit_breaker_active = True
    rm1.circuit_breaker_type = CircuitBreakerType.LARGE_LOSS
    rm1._save_state()

    assert state_file.exists()
    print(f"✅ State saved to {state_file}")

    # Load into new manager
    rm2 = RiskManager(mock_kalshi, state_file=str(state_file))

    assert rm2.circuit_breaker_active == True
    assert rm2.circuit_breaker_type == CircuitBreakerType.LARGE_LOSS
    assert rm2.daily_state.trades_placed_today == 5
    print("✅ State loaded correctly from file")

    # Cleanup
    state_file.unlink()


# ============================================================================
# TEST 10: Integration - Full Trade Validation Flow
# ============================================================================

def test_full_validation_flow():
    """Test complete trade validation with all rules."""
    print("\n" + "="*80)
    print("TEST 10: Integration - Full Trade Validation Flow")
    print("="*80)

    mock_kalshi = create_mock_kalshi_client(unrealized_pnl=0)
    rm = RiskManager(
        mock_kalshi,
        global_exposure_pct=0.25,
        per_city_exposure_pct=0.10,
        single_trade_size_pct=0.04
    )

    rm._refresh_portfolio_state()

    # Scenario 1: Strong trade with good edge
    proposal = TradeProposal(
        ticker="KXHIGHNY-26MAY21-T75",
        city="NYC",
        side="yes",
        action="buy",
        size_contracts=200,
        edge_pct=0.15,  # 15% edge
        confidence=85.0  # High confidence
    )

    result = rm.validate_trade(proposal)
    assert result.approved == True
    print(f"✅ Scenario 1 (strong edge): {result.reason}")
    print(f"   Checks passed: {', '.join([c for c in result.logs if 'ok' in c or 'OK' in c or '✓' in c])}")

    # Scenario 2: Weak edge (but not rejected, just lower conviction)
    proposal = TradeProposal(
        ticker="KXHIGHCHI-26MAY21-T65",
        city="Chicago",
        side="yes",
        action="buy",
        size_contracts=100,
        edge_pct=0.02,  # 2% edge (low)
        confidence=55.0  # Lower confidence
    )

    result = rm.validate_trade(proposal)
    assert result.approved == True  # Still approved (no edge minimum in risk manager)
    print(f"✅ Scenario 2 (weak edge): {result.reason}")

    # Scenario 3: Way too large
    proposal = TradeProposal(
        ticker="KXHIGHLA-26MAY21-T85",
        city="Los Angeles",
        side="yes",
        action="buy",
        size_contracts=10000,  # Huge size
        edge_pct=0.10,
        confidence=75.0
    )

    result = rm.validate_trade(proposal)
    assert result.approved == False
    assert "SINGLE_TRADE_SIZE" in result.reason or "single_trade" in str(result.checks_failed)
    print(f"✅ Scenario 3 (oversized): {result.reason}")


# ============================================================================
# TEST 11: City Extraction from Ticker
# ============================================================================

def test_city_extraction():
    """Test extracting city from Kalshi ticker symbols."""
    print("\n" + "="*80)
    print("TEST 11: City Extraction from Ticker")
    print("="*80)

    mock_kalshi = create_mock_kalshi_client(unrealized_pnl=0)
    rm = RiskManager(mock_kalshi)

    test_cases = [
        ("KXHIGHNY-26MAY21-T75", "NYC"),
        ("KXHIGHCHI-26MAY21-T65", "Chicago"),
        ("KXHIGHLA-26MAY21-T85", "Los Angeles"),
        ("KXHIGHSF-26MAY21-T70", "San Francisco"),
        ("KXHIGHDAL-26MAY21-T95", "Dallas"),
    ]

    for ticker, expected_city in test_cases:
        extracted = rm._extract_city_from_ticker(ticker)
        assert extracted == expected_city, f"Expected {expected_city}, got {extracted}"
        print(f"✅ {ticker} → {extracted}")


# ============================================================================
# TEST 12: Get Summary
# ============================================================================

def test_get_summary():
    """Test getting summary of risk manager state."""
    print("\n" + "="*80)
    print("TEST 12: Get Summary")
    print("="*80)

    mock_kalshi = create_mock_kalshi_client(unrealized_pnl=0)
    rm = RiskManager(mock_kalshi)

    rm._refresh_portfolio_state()
    summary = rm.get_summary()

    assert summary['circuit_breaker_active'] == False
    assert summary['portfolio_state'] is not None
    assert summary['daily_state'] is not None
    assert 'open_positions_by_city' in summary
    assert 'consecutive_api_failures' in summary

    print("✅ Summary contains all required fields:")
    for key in summary:
        print(f"   - {key}")


# ============================================================================
# Main Test Runner
# ============================================================================

def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("RISK MANAGER TEST SUITE")
    print("="*80)

    tests = [
        ("TEST 1", test_risk_manager_initialization),
        ("TEST 2", test_global_exposure_limit),
        ("TEST 3", test_per_city_exposure_limit),
        ("TEST 4", test_single_trade_size_limit),
        ("TEST 5", test_manual_pause),
        ("TEST 6", test_circuit_breaker_api_health),
        ("TEST 7", test_daily_loss_limits),
        ("TEST 8", test_cluster_correlation),
        ("TEST 9", test_state_persistence),
        ("TEST 10", test_full_validation_flow),
        ("TEST 11", test_city_extraction),
        ("TEST 12", test_get_summary),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ {name} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {name} ERROR: {e}")
            failed += 1

    print("\n" + "="*80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("="*80)

    return failed == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
