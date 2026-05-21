"""
Risk Management & Portfolio Layer for Kalshi Weather Trading Bot.

Implements a dedicated RiskManager that sits between the Scanner/Orchestrator
and the ExecutionService, enforcing safety rules and protecting capital:

- Portfolio State Tracking: Maintains accurate view of equity, positions, PnL
- Global & Per-City Exposure Limits: Prevents overexposure
- Single Trade Size Limits: Enforces maximum position size
- Daily Loss Limits: Soft pause at -5%, hard pause at -8%
- Cluster Correlation Rules: Reduces size for correlated city bets
- Circuit Breakers: API health, large loss, manual pause
- Comprehensive Logging: Every decision logged with full context

Architecture:
    WeatherPredictor (generates signal)
        ↓
    RiskManager.validate_trade(proposal)  ← NEW GATE
        ↓
    ExecutionService.place_order(signal)  ← EXISTING
"""

import json
import logging
import statistics
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum

from kalshi_api_client import KalshiAPIClient
from execution_service import TradeSignal

logger = logging.getLogger(__name__)


# ============================================================================
# PHASE 9: Risk Management Data Structures
# ============================================================================

class RiskDecision(Enum):
    """Outcome of a trade validation check."""
    APPROVED = "approved"
    REJECTED = "rejected"
    CIRCUIT_BROKEN = "circuit_broken"


class CircuitBreakerType(Enum):
    """Types of circuit breaker events."""
    API_HEALTH = "api_health"
    LARGE_LOSS = "large_loss"
    MANUAL_PAUSE = "manual_pause"


@dataclass
class PortfolioState:
    """Current portfolio state as fetched from Kalshi."""
    timestamp: datetime
    balance_cents: int                  # Available balance in cents
    portfolio_value_cents: int          # Total portfolio value in cents
    total_open_positions: int           # Count of open positions
    realized_pnl_cents: int             # PnL from resolved trades
    unrealized_pnl_cents: int           # PnL from open positions

    def total_pnl_cents(self) -> int:
        """Total PnL (realized + unrealized)."""
        return self.realized_pnl_cents + self.unrealized_pnl_cents

    def equity_cents(self) -> int:
        """Current equity (balance + portfolio value)."""
        return self.balance_cents + self.portfolio_value_cents


@dataclass
class DailyRiskState:
    """Daily risk tracking state."""
    date: str                           # ISO date string (YYYY-MM-DD UTC)
    start_equity_cents: int             # Equity at UTC midnight
    daily_pnl_cents: int                # PnL since start of day
    trades_placed_today: int            # Count of trades executed
    soft_pause_active: bool             # True if -5% loss threshold hit
    hard_pause_active: bool             # True if -8% loss threshold hit
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TradeProposal:
    """Trade proposal submitted for risk validation."""
    ticker: str                         # Market ticker (e.g., "KXHIGHNY-26MAY21-T75")
    city: str                           # City name (e.g., "NYC")
    side: str                           # "yes" or "no"
    action: str                         # "buy" or "sell"
    size_contracts: int                 # Proposed contract count
    edge_pct: float                     # Edge percentage (model prob - market prob)
    confidence: float                   # Confidence score (0-100)
    signal: Optional[TradeSignal] = None  # Original signal (optional, for tracing)


@dataclass
class RiskCheckResult:
    """Result of risk validation."""
    decision: RiskDecision
    approved: bool                      # True if trade approved
    reason: str                         # Explanation (rejection reason or "APPROVED")
    checks_failed: List[str]            # List of failed check names
    portfolio_state: Optional[PortfolioState] = None
    daily_state: Optional[DailyRiskState] = None
    logs: List[str] = field(default_factory=list)  # Detailed check logs


# ============================================================================
# PHASE 9: City Cluster Definitions
# ============================================================================

CITY_CLUSTERS = {
    "East Coast": ["NYC", "Boston", "Philadelphia", "Miami", "Atlanta"],
    "Midwest": ["Chicago", "Detroit", "Cleveland", "Minneapolis", "Denver"],
    "West Coast": ["Los Angeles", "San Francisco", "Seattle", "Portland", "Phoenix"],
    "South": ["Houston", "Dallas", "Austin", "New Orleans"],
}

# Reverse lookup: city → cluster name
CITY_TO_CLUSTER = {}
for cluster_name, cities in CITY_CLUSTERS.items():
    for city in cities:
        CITY_TO_CLUSTER[city] = cluster_name


# ============================================================================
# PHASE 9: RiskManager Class
# ============================================================================

class RiskManager:
    """
    Gatekeeper between trading signals and execution.

    Maintains accurate portfolio state, enforces exposure limits, tracks daily
    losses, detects correlations, and implements circuit breakers.
    """

    # Default configuration (can be overridden)
    DEFAULT_GLOBAL_EXPOSURE_PCT = 0.25      # 25% of equity max
    DEFAULT_PER_CITY_EXPOSURE_PCT = 0.10    # 10% of equity max
    DEFAULT_SINGLE_TRADE_SIZE_PCT = 0.04    # 4% of equity max
    DEFAULT_SOFT_LOSS_THRESHOLD_PCT = -0.05 # -5% soft pause
    DEFAULT_HARD_LOSS_THRESHOLD_PCT = -0.08 # -8% hard pause
    DEFAULT_CLUSTER_CORRELATION_REDUCTION = 0.5  # 50% size reduction

    def __init__(
        self,
        kalshi_client: KalshiAPIClient,
        state_file: str = "risk_manager_state.json",
        global_exposure_pct: float = DEFAULT_GLOBAL_EXPOSURE_PCT,
        per_city_exposure_pct: float = DEFAULT_PER_CITY_EXPOSURE_PCT,
        single_trade_size_pct: float = DEFAULT_SINGLE_TRADE_SIZE_PCT,
        soft_loss_threshold_pct: float = DEFAULT_SOFT_LOSS_THRESHOLD_PCT,
        hard_loss_threshold_pct: float = DEFAULT_HARD_LOSS_THRESHOLD_PCT,
        cluster_correlation_reduction: float = DEFAULT_CLUSTER_CORRELATION_REDUCTION,
        manual_pause: bool = False,
    ):
        """
        Initialize RiskManager.

        Args:
            kalshi_client: KalshiAPIClient for fetching portfolio state
            state_file: Path to JSON file for persistence
            global_exposure_pct: Max exposure as % of equity
            per_city_exposure_pct: Max exposure per city as % of equity
            single_trade_size_pct: Max trade size as % of equity
            soft_loss_threshold_pct: Daily loss % for soft pause
            hard_loss_threshold_pct: Daily loss % for hard pause
            cluster_correlation_reduction: Size reduction factor for correlated cities
            manual_pause: If True, reject all new trades
        """
        self.kalshi = kalshi_client
        self.state_file = Path(state_file)

        # Configuration
        self.global_exposure_pct = global_exposure_pct
        self.per_city_exposure_pct = per_city_exposure_pct
        self.single_trade_size_pct = single_trade_size_pct
        self.soft_loss_threshold_pct = soft_loss_threshold_pct
        self.hard_loss_threshold_pct = hard_loss_threshold_pct
        self.cluster_correlation_reduction = cluster_correlation_reduction
        self.manual_pause = manual_pause

        # State tracking
        self.portfolio_state: Optional[PortfolioState] = None
        self.daily_state: Optional[DailyRiskState] = None
        self.open_positions_by_city: Dict[str, int] = {}  # city → total contracts
        self.open_positions_by_ticker: Dict[str, Dict] = {}  # ticker → position details
        self.circuit_breaker_active = False
        self.circuit_breaker_type: Optional[CircuitBreakerType] = None
        self.consecutive_api_failures = 0
        self.last_portfolio_update: Optional[datetime] = None

        # Load persisted state if it exists
        self._load_state()

        # Ensure daily state exists
        if self.daily_state is None:
            self._init_daily_state()

        logger.info(
            f"RiskManager initialized: global_exp={global_exposure_pct*100}%, "
            f"per_city_exp={per_city_exposure_pct*100}%, "
            f"single_trade={single_trade_size_pct*100}%, "
            f"soft_loss={soft_loss_threshold_pct*100}%, "
            f"hard_loss={hard_loss_threshold_pct*100}%"
        )

    def validate_trade(self, proposal: TradeProposal) -> RiskCheckResult:
        """
        Validate a trade proposal against all risk rules.

        Returns decision immediately if circuit breaker is active.
        Otherwise checks rules in order: global → per-city → cluster → loss → size.

        Args:
            proposal: TradeProposal with trade details

        Returns:
            RiskCheckResult with decision and detailed logs
        """
        result = RiskCheckResult(
            decision=RiskDecision.REJECTED,
            approved=False,
            reason="",
            checks_failed=[]
        )

        # Refresh portfolio state (every 30-60 seconds typically)
        self._refresh_portfolio_state()
        result.portfolio_state = self.portfolio_state
        result.daily_state = self.daily_state

        # Check manual pause flag
        if self.manual_pause:
            result.reason = "MANUAL_PAUSE: Trading disabled by operator"
            result.checks_failed.append("manual_pause")
            self._log_rejection(proposal, result)
            return result

        # Check circuit breaker status
        if self.circuit_breaker_active:
            result.decision = RiskDecision.CIRCUIT_BROKEN
            result.reason = f"CIRCUIT_BREAKER: {self.circuit_breaker_type.value}"
            result.checks_failed.append("circuit_breaker")
            self._log_rejection(proposal, result)
            return result

        # Check daily loss hard pause
        if self.daily_state and self.daily_state.hard_pause_active:
            result.reason = "HARD_PAUSE: Daily loss exceeded -8% threshold"
            result.checks_failed.append("daily_loss_hard_pause")
            self._log_rejection(proposal, result)
            return result

        # Check global exposure limit
        check = self._check_global_exposure(proposal)
        if not check['passed']:
            result.reason = check['reason']
            result.checks_failed.append("global_exposure")
            result.logs.append(check['detail'])
            self._log_rejection(proposal, result)
            return result
        result.logs.append(check['detail'])

        # Check per-city exposure limit
        check = self._check_per_city_exposure(proposal)
        if not check['passed']:
            result.reason = check['reason']
            result.checks_failed.append("per_city_exposure")
            result.logs.append(check['detail'])
            self._log_rejection(proposal, result)
            return result
        result.logs.append(check['detail'])

        # Check cluster correlation and adjust size if needed
        adjusted_size = self._check_cluster_correlation(proposal)
        if adjusted_size < proposal.size_contracts:
            reduction_pct = (1 - adjusted_size / proposal.size_contracts) * 100
            result.logs.append(
                f"Cluster correlation detected: size reduced by {reduction_pct:.0f}% "
                f"({proposal.size_contracts} → {adjusted_size} contracts)"
            )
            # Update proposal to use adjusted size
            proposal.size_contracts = adjusted_size

        # Check single trade size limit (with potential cluster adjustment)
        check = self._check_single_trade_size(proposal)
        if not check['passed']:
            result.reason = check['reason']
            result.checks_failed.append("single_trade_size")
            result.logs.append(check['detail'])
            self._log_rejection(proposal, result)
            return result
        result.logs.append(check['detail'])

        # Check daily loss soft pause (warning, not rejection)
        if self.daily_state and self.daily_state.soft_pause_active:
            result.logs.append(
                f"⚠️  SOFT PAUSE ACTIVE: Daily loss at {self.daily_state.daily_pnl_cents/100:.2f}, "
                f"exceeds -5% threshold. Trade accepted but monitor closely."
            )

        # All checks passed
        result.decision = RiskDecision.APPROVED
        result.approved = True
        result.reason = "APPROVED"
        self._log_approval(proposal, result)

        return result

    def _check_global_exposure(self, proposal: TradeProposal) -> Dict:
        """Check total open notional exposure against limit."""
        if not self.portfolio_state:
            return {
                'passed': False,
                'reason': 'PORTFOLIO_STATE_UNAVAILABLE',
                'detail': 'Unable to fetch portfolio state'
            }

        equity = self.portfolio_state.equity_cents()
        limit_cents = int(equity * self.global_exposure_pct)

        # Calculate current notional exposure (sum of all open positions in cents)
        # For simplicity, use contract counts * 50 cents per contract as estimate
        current_exposure = sum(count * 50 for count in self.open_positions_by_city.values())
        proposed_exposure = proposal.size_contracts * 50
        total_exposure = current_exposure + proposed_exposure

        passed = total_exposure <= limit_cents
        pct_of_limit = (total_exposure / limit_cents * 100) if limit_cents > 0 else 0

        return {
            'passed': passed,
            'reason': 'GLOBAL_EXPOSURE_EXCEEDED' if not passed else 'global_exposure_ok',
            'detail': (
                f"Global exposure: {total_exposure/100:.2f} cents "
                f"({pct_of_limit:.1f}% of {limit_cents/100:.2f} limit). "
                f"Current: {current_exposure/100:.2f}, Proposed: {proposed_exposure/100:.2f}"
            )
        }

    def _check_per_city_exposure(self, proposal: TradeProposal) -> Dict:
        """Check single city exposure against limit."""
        if not self.portfolio_state:
            return {
                'passed': False,
                'reason': 'PORTFOLIO_STATE_UNAVAILABLE',
                'detail': 'Unable to fetch portfolio state'
            }

        equity = self.portfolio_state.equity_cents()
        limit_contracts = int(equity * self.per_city_exposure_pct / 50)  # ~50 cents per contract

        current_city_exposure = self.open_positions_by_city.get(proposal.city, 0)
        total_city_exposure = current_city_exposure + proposal.size_contracts

        passed = total_city_exposure <= limit_contracts

        return {
            'passed': passed,
            'reason': 'PER_CITY_EXPOSURE_EXCEEDED' if not passed else 'per_city_exposure_ok',
            'detail': (
                f"City ({proposal.city}) exposure: {total_city_exposure} contracts "
                f"(limit: {limit_contracts}). Current: {current_city_exposure}, "
                f"Proposed: {proposal.size_contracts}"
            )
        }

    def _check_cluster_correlation(self, proposal: TradeProposal) -> int:
        """
        Check if other cities in same cluster have active high-edge recommendations.
        If yes, reduce proposed trade size by correlation factor.

        Returns adjusted size (may be less than proposal.size_contracts).
        """
        cluster = CITY_TO_CLUSTER.get(proposal.city)
        if not cluster:
            return proposal.size_contracts

        # Count how many other cities in cluster have open positions
        other_cities_in_cluster = [
            c for c in CITY_CLUSTERS[cluster]
            if c != proposal.city and self.open_positions_by_city.get(c, 0) > 0
        ]

        if len(other_cities_in_cluster) >= 2:
            # Two or more correlated positions active: reduce size
            adjusted_size = int(proposal.size_contracts * (1 - self.cluster_correlation_reduction))
            return max(1, adjusted_size)  # Never reduce below 1 contract

        return proposal.size_contracts

    def _check_single_trade_size(self, proposal: TradeProposal) -> Dict:
        """Check individual trade size against limit."""
        if not self.portfolio_state:
            return {
                'passed': False,
                'reason': 'PORTFOLIO_STATE_UNAVAILABLE',
                'detail': 'Unable to fetch portfolio state'
            }

        equity = self.portfolio_state.equity_cents()
        limit_contracts = int(equity * self.single_trade_size_pct / 50)  # ~50 cents per contract

        passed = proposal.size_contracts <= limit_contracts

        return {
            'passed': passed,
            'reason': 'SINGLE_TRADE_SIZE_EXCEEDED' if not passed else 'single_trade_size_ok',
            'detail': (
                f"Trade size: {proposal.size_contracts} contracts "
                f"(limit: {limit_contracts}). "
                f"At {self.single_trade_size_pct*100:.1f}% of equity (${equity/100:.2f})"
            )
        }

    def _refresh_portfolio_state(self) -> None:
        """Fetch current portfolio state from Kalshi API."""
        try:
            # Fetch balance
            balance_data = self.kalshi.get_portfolio_balance()
            if not balance_data:
                self.consecutive_api_failures += 1
                if self.consecutive_api_failures >= 5:
                    self._trigger_circuit_breaker(CircuitBreakerType.API_HEALTH)
                return

            # Fetch positions
            positions_data = self.kalshi.get_positions()
            if positions_data is None:
                self.consecutive_api_failures += 1
                if self.consecutive_api_failures >= 5:
                    self._trigger_circuit_breaker(CircuitBreakerType.API_HEALTH)
                return

            # Reset failure counter on success
            self.consecutive_api_failures = 0

            # Build new state
            balance_cents = balance_data.get('balance', 0)
            portfolio_value_cents = balance_data.get('portfolio_value', 0)
            realized_pnl_cents = balance_data.get('realized_pnl', 0)
            unrealized_pnl_cents = balance_data.get('unrealized_pnl', 0)

            self.portfolio_state = PortfolioState(
                timestamp=datetime.now(timezone.utc),
                balance_cents=balance_cents,
                portfolio_value_cents=portfolio_value_cents,
                total_open_positions=len(positions_data),
                realized_pnl_cents=realized_pnl_cents,
                unrealized_pnl_cents=unrealized_pnl_cents
            )

            self.last_portfolio_update = datetime.now(timezone.utc)

            # Update city and ticker position tracking
            self._update_position_tracking(positions_data)

            # Update daily PnL
            self._update_daily_pnl()

            # Persist state
            self._save_state()

            logger.debug(
                f"Portfolio state refreshed: equity=${self.portfolio_state.equity_cents()/100:.2f}, "
                f"pnl=${self.portfolio_state.total_pnl_cents()/100:.2f}, "
                f"positions={self.portfolio_state.total_open_positions}"
            )

        except Exception as e:
            logger.error(f"Failed to refresh portfolio state: {e}")
            self.consecutive_api_failures += 1
            if self.consecutive_api_failures >= 5:
                self._trigger_circuit_breaker(CircuitBreakerType.API_HEALTH)

    def _update_position_tracking(self, positions: List[Dict]) -> None:
        """Update internal tracking of open positions by city and ticker."""
        self.open_positions_by_city = {}
        self.open_positions_by_ticker = {}

        for pos in positions:
            ticker = pos.get('ticker', '')
            quantity = pos.get('quantity', 0)
            side = pos.get('side', '')

            # Extract city from ticker (e.g., "KXHIGHNY" → "NYC")
            city = self._extract_city_from_ticker(ticker)

            if city:
                self.open_positions_by_city[city] = self.open_positions_by_city.get(city, 0) + abs(quantity)

            self.open_positions_by_ticker[ticker] = {
                'quantity': quantity,
                'side': side,
                'current_price': pos.get('current_price'),
                'entry_price': pos.get('entry_price'),
                'realized_pnl': pos.get('realized_pnl', 0),
                'unrealized_pnl': pos.get('unrealized_pnl', 0),
            }

    def _extract_city_from_ticker(self, ticker: str) -> Optional[str]:
        """
        Extract city from ticker.

        E.g., "KXHIGHNY-26MAY21-T75" → "NYC"
        Handles common Kalshi patterns.
        """
        # Simple pattern matching - expand as needed
        patterns = {
            'NY': 'NYC',
            'CHI': 'Chicago',
            'LA': 'Los Angeles',
            'SF': 'San Francisco',
            'BOS': 'Boston',
            'PHI': 'Philadelphia',
            'MIA': 'Miami',
            'ATL': 'Atlanta',
            'DET': 'Detroit',
            'CLE': 'Cleveland',
            'MIN': 'Minneapolis',
            'DEN': 'Denver',
            'HOU': 'Houston',
            'DAL': 'Dallas',
            'AUS': 'Austin',
            'NO': 'New Orleans',
            'SEA': 'Seattle',
            'PDX': 'Portland',
            'PHX': 'Phoenix',
        }

        ticker_upper = ticker.upper()
        for pattern, city in patterns.items():
            if pattern in ticker_upper:
                return city

        return None

    def _update_daily_pnl(self) -> None:
        """Update daily PnL tracking."""
        if not self.portfolio_state or not self.daily_state:
            return

        # Daily PnL = total profit/loss from today's trading
        # Measured as: (current total equity) - (starting equity at beginning of day)
        current_total_equity = self.portfolio_state.balance_cents + self.portfolio_state.unrealized_pnl_cents
        self.daily_state.daily_pnl_cents = current_total_equity - self.daily_state.start_equity_cents

        # Check for soft/hard loss thresholds
        if self.daily_state.start_equity_cents <= 0:
            return  # Cannot calculate loss % without valid starting equity

        daily_loss_pct = self.daily_state.daily_pnl_cents / self.daily_state.start_equity_cents

        if daily_loss_pct <= self.hard_loss_threshold_pct and not self.daily_state.hard_pause_active:
            self.daily_state.hard_pause_active = True
            self._trigger_circuit_breaker(CircuitBreakerType.LARGE_LOSS)
            logger.warning(
                f"HARD PAUSE TRIGGERED: Daily loss {daily_loss_pct*100:.2f}% "
                f"exceeds {self.hard_loss_threshold_pct*100:.1f}% threshold"
            )

        if daily_loss_pct <= self.soft_loss_threshold_pct and not self.daily_state.soft_pause_active:
            self.daily_state.soft_pause_active = True
            logger.warning(
                f"SOFT PAUSE TRIGGERED: Daily loss {daily_loss_pct*100:.2f}% "
                f"exceeds {self.soft_loss_threshold_pct*100:.1f}% threshold"
            )

    def _trigger_circuit_breaker(self, breaker_type: CircuitBreakerType) -> None:
        """Activate circuit breaker."""
        self.circuit_breaker_active = True
        self.circuit_breaker_type = breaker_type
        logger.critical(f"🛑 CIRCUIT BREAKER ACTIVATED: {breaker_type.value}")
        self._save_state()

    def reset_circuit_breaker(self) -> None:
        """Manually reset circuit breaker (after investigation)."""
        self.circuit_breaker_active = False
        self.circuit_breaker_type = None
        logger.info("Circuit breaker reset (manual)")
        self._save_state()

    def reset_daily_limits(self) -> None:
        """Reset daily limits at UTC midnight."""
        self._init_daily_state()
        logger.info("Daily limits reset at UTC midnight")
        self._save_state()

    def _init_daily_state(self) -> None:
        """Initialize daily state at midnight."""
        if self.portfolio_state:
            # Start equity is current balance only (not portfolio value)
            # This represents starting cash at beginning of day
            start_equity = self.portfolio_state.balance_cents
        else:
            start_equity = 0

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.daily_state = DailyRiskState(
            date=today,
            start_equity_cents=start_equity,
            daily_pnl_cents=0,
            trades_placed_today=0,
            soft_pause_active=False,
            hard_pause_active=False
        )

    def log_trade_executed(self, proposal: TradeProposal) -> None:
        """Record that a trade was executed."""
        if self.daily_state:
            self.daily_state.trades_placed_today += 1
            self._save_state()

    def _log_approval(self, proposal: TradeProposal, result: RiskCheckResult) -> None:
        """Log approved trade."""
        logger.info(
            f"✅ TRADE APPROVED | {proposal.city} {proposal.ticker} "
            f"{proposal.size_contracts} contracts | edge={proposal.edge_pct*100:.1f}% | "
            f"confidence={proposal.confidence:.1f}/100 | "
            f"Checks: {' | '.join(result.logs)}"
        )

    def _log_rejection(self, proposal: TradeProposal, result: RiskCheckResult) -> None:
        """Log rejected trade."""
        logger.warning(
            f"❌ TRADE REJECTED | {proposal.city} {proposal.ticker} "
            f"{proposal.size_contracts} contracts | Reason: {result.reason} | "
            f"Failed: {', '.join(result.checks_failed)}"
        )

    def _load_state(self) -> None:
        """Load persisted state from JSON file."""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)

            # Restore daily state if present and still valid for today
            if 'daily_state' in data:
                daily_data = data['daily_state']
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

                if daily_data.get('date') == today:
                    last_updated = datetime.fromisoformat(daily_data['last_updated']) if 'last_updated' in daily_data else datetime.now(timezone.utc)
                    self.daily_state = DailyRiskState(
                        date=daily_data['date'],
                        start_equity_cents=daily_data['start_equity_cents'],
                        daily_pnl_cents=daily_data['daily_pnl_cents'],
                        trades_placed_today=daily_data['trades_placed_today'],
                        soft_pause_active=daily_data['soft_pause_active'],
                        hard_pause_active=daily_data['hard_pause_active'],
                        last_updated=last_updated
                    )

            # Restore circuit breaker state
            if 'circuit_breaker_active' in data:
                self.circuit_breaker_active = data['circuit_breaker_active']

            if 'circuit_breaker_type' in data and data['circuit_breaker_type']:
                self.circuit_breaker_type = CircuitBreakerType(data['circuit_breaker_type'])

            logger.info(f"Loaded risk manager state from {self.state_file}")

        except Exception as e:
            logger.warning(f"Failed to load risk manager state: {e}")

    def _save_state(self) -> None:
        """Persist state to JSON file."""
        try:
            data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'circuit_breaker_active': self.circuit_breaker_active,
                'circuit_breaker_type': self.circuit_breaker_type.value if self.circuit_breaker_type else None,
            }

            if self.daily_state:
                daily_dict = asdict(self.daily_state)
                # Convert datetime to isoformat string for JSON serialization
                daily_dict['last_updated'] = daily_dict['last_updated'].isoformat()
                data['daily_state'] = daily_dict

            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save risk manager state: {e}")

    def get_summary(self) -> Dict:
        """Return summary of current risk status."""
        return {
            'portfolio_state': asdict(self.portfolio_state) if self.portfolio_state else None,
            'daily_state': asdict(self.daily_state) if self.daily_state else None,
            'circuit_breaker_active': self.circuit_breaker_active,
            'circuit_breaker_type': self.circuit_breaker_type.value if self.circuit_breaker_type else None,
            'open_positions_by_city': self.open_positions_by_city,
            'consecutive_api_failures': self.consecutive_api_failures,
            'last_portfolio_update': self.last_portfolio_update.isoformat() if self.last_portfolio_update else None,
        }
