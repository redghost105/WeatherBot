# Phase 10: Backtesting & Simulation Framework - Implementation Plan

**Objective**: Build a high-fidelity historical replay engine to validate the entire system against real market data before live deployment.

---

## Architecture Overview

```
Historical Data Layer
  ├─ Weather Archives (Open-Meteo, NOAA)
  ├─ Market Snapshots (Kalshi API)
  └─ Price History (stored/reconstructed)
         ↓
  BacktestSimulator
  ├─ Reconstruct state at timestamp T
  ├─ Run WeatherPredictor
  ├─ Apply RiskManager
  ├─ Simulate ExecutionService
  └─ Resolve against actual outcome
         ↓
  PerformanceAnalytics
  ├─ Metrics (Sharpe, drawdown, Brier score)
  ├─ Monte Carlo simulations
  ├─ Walk-forward optimization
  └─ Parameter sweeping
         ↓
  Reporting & Visualization
  ├─ HTML reports
  ├─ CSV data exports
  ├─ Charts (equity, calibration, heatmaps)
  └─ Counterfactual comparisons
```

---

## Core Components to Implement

### 1. **BacktestConfig** (Dataclass)
Configuration for all backtest parameters:
```python
@dataclass
class BacktestConfig:
    start_date: str                  # YYYY-MM-DD
    end_date: str                    # YYYY-MM-DD
    initial_capital: int             # cents
    
    # Strategy parameters
    min_edge_threshold: float        # 5% = 0.05
    ensemble_weight: float           # 0.7
    confidence_cutoff: float         # 60/100
    
    # Risk parameters
    max_position_size: int           # contracts
    max_daily_loss_pct: float        # 0.08 = -8%
    
    # Simulation parameters
    include_fees: bool = True
    fee_per_contract: float = 0.01   # $0.01 per contract
    slippage_pct: float = 0.02       # 2% price slippage
    
    # Output options
    output_dir: str = "backtest_results"
    generate_plots: bool = True
```

### 2. **HistoricalDataLoader** (Class)
Load and cache historical data:

**Responsibilities**:
- Fetch historical weather data from Open-Meteo archives
- Load Kalshi market snapshots (stored or reconstructed)
- Retrieve historical price sequences
- Cache data locally to avoid repeated API calls

**Key Methods**:
```python
class HistoricalDataLoader:
    def get_weather_history(
        self, 
        city: str, 
        date: str
    ) -> LocationWeatherData
        """Get archived weather for specific date"""
    
    def get_market_state(
        self, 
        city: str, 
        date: str
    ) -> Dict[str, MarketSnapshot]
        """Get market buckets and prices at timestamp"""
    
    def get_historical_prices(
        self, 
        ticker: str, 
        start_date: str, 
        end_date: str
    ) -> List[PricePoint]
        """Get price history for market"""
    
    def get_resolution_outcome(
        self, 
        city: str, 
        date: str
    ) -> float
        """Get actual NWS temperature for resolution"""
```

### 3. **BacktestSimulator** (Class)
Core simulation engine:

**Responsibilities**:
- Iterate through each day in backtest period
- Reconstruct exact state at each timestamp
- Run WeatherPredictor with historical bias
- Apply RiskManager rules
- Simulate order execution with realistic fills
- Resolve trades and calculate PnL

**Key Methods**:
```python
class BacktestSimulator:
    def run(self) -> BacktestResults
        """Run full backtest simulation"""
    
    def simulate_day(
        self, 
        date: str
    ) -> DayResults
        """Simulate single day of trading"""
    
    def execute_signal(
        self, 
        signal: TradeSignal,
        market_prices: Dict
    ) -> ExecutedTrade
        """Simulate realistic order execution with slippage/fees"""
    
    def resolve_trades(
        self, 
        date: str
    ) -> List[ResolvedTrade]
        """Resolve trades against actual outcomes"""
```

### 4. **PerformanceMetrics** (Class)
Calculate comprehensive statistics:

**Metrics to Calculate**:
- **Return Metrics**:
  - Total return (%)
  - Annualized return (%)
  - Monthly returns
  
- **Risk Metrics**:
  - Volatility (std dev of daily returns)
  - Sharpe ratio (return / volatility)
  - Sortino ratio (downside volatility)
  - Maximum drawdown
  - Drawdown duration
  - Profit factor (gross profit / gross loss)
  
- **Prediction Metrics**:
  - Brier score (calibration)
  - Hit rate (correct bucket prediction)
  - Edge realization rate (% of positive edges that made money)
  - Calibration slope
  
- **Trade Metrics**:
  - Win rate (% winning trades)
  - Average winning trade
  - Average losing trade
  - Largest win / largest loss
  - Trades per day
  - Average trade duration

**Breakdowns**:
- By city (NYC, Chicago, LA, etc.)
- By season (spring, summer, fall, winter)
- By confidence level (60-70, 70-80, 80-90, 90+)
- By weather regime (heat wave, cold front, stable)
- By time-to-resolution (< 12h, 12-24h, 24-30h)

**Key Methods**:
```python
class PerformanceMetrics:
    def calculate_all(
        self, 
        trades: List[ResolvedTrade],
        daily_balances: List[int]
    ) -> MetricsReport
        """Calculate all metrics"""
    
    def sharpe_ratio(
        self, 
        daily_returns: List[float]
    ) -> float
        """Calculate Sharpe ratio"""
    
    def brier_score(
        self, 
        predictions: Dict[str, float],
        outcomes: Dict[str, bool]
    ) -> float
        """Calculate Brier score"""
    
    def calculate_breakdowns(
        self, 
        trades: List[ResolvedTrade]
    ) -> BreakdownMetrics
        """Calculate per-city, per-season, per-confidence metrics"""
```

### 5. **MonteCarloSimulator** (Class)
Advanced statistical validation:

**Capabilities**:
- Run 1000s of randomized paths
- Controlled randomness in:
  - Market price movements
  - Execution fill rates
  - Slippage amount
  - Partial fills
- Calculate confidence intervals on key metrics

**Key Methods**:
```python
class MonteCarloSimulator:
    def run_paths(
        self, 
        base_trades: List[Trade],
        n_simulations: int = 1000,
        randomness_pct: float = 0.05
    ) -> MonteCarloResults
        """Run randomized simulations"""
    
    def confidence_interval(
        self, 
        metric: str,
        confidence: float = 0.95
    ) -> Tuple[float, float]
        """Get 95% confidence interval on metric"""
```

### 6. **WalkForwardOptimizer** (Class)
Avoid look-ahead bias:

**Approach**:
- Divide period into training windows and test windows
- Train parameters on past data
- Test on subsequent unseen data
- Report out-of-sample performance

**Key Methods**:
```python
class WalkForwardOptimizer:
    def optimize(
        self, 
        train_end_date: str,
        test_end_date: str,
        param_ranges: Dict[str, List]
    ) -> OptimizationResults
        """Find best parameters on training period, validate on test"""
    
    def parameter_sweep(
        self, 
        parameters: Dict[str, List],
        train_dates: DateRange
    ) -> ParameterSweepResults
        """Test all combinations of parameters"""
```

### 7. **CounterfactualAnalyzer** (Class)
Compare strategy variants:

**Experiments to Support**:
- With vs without HistoricalBiasLearner
- Pure ensemble vs statistical only
- Different blending weights (0.5, 0.6, 0.7, 0.8)
- Aggressive vs conservative risk limits
- Different edge thresholds (2%, 5%, 10%)

**Key Methods**:
```python
class CounterfactualAnalyzer:
    def compare_variants(
        self, 
        variants: Dict[str, BacktestConfig]
    ) -> ComparisonReport
        """Run multiple variants, compare results"""
    
    def ablation_study(
        self, 
        base_config: BacktestConfig,
        component_to_remove: str
    ) -> AblationResults
        """Test impact of removing one component"""
```

### 8. **BacktestReporter** (Class)
Generate output reports:

**Output Formats**:
- **HTML**: Interactive dashboard with charts
- **CSV**: Raw data for Excel/pandas analysis
- **JSON**: Machine-readable results
- **Text**: Summary statistics

**Key Methods**:
```python
class BacktestReporter:
    def generate_html_report(
        self, 
        results: BacktestResults
    ) -> str
        """Generate interactive HTML dashboard"""
    
    def export_csv(
        self, 
        trades: List[ResolvedTrade],
        daily_data: List[DailyStats],
        metrics: MetricsReport
    ) -> str
        """Export to CSV files"""
    
    def generate_json_export(
        self, 
        results: BacktestResults
    ) -> Dict
        """Export complete results as JSON"""
```

### 9. **Visualization** (Functions)
Create charts and diagrams:

**Charts to Generate**:
- **Equity Curve**: Portfolio value over time
- **Drawdown Plot**: Peak-to-trough declines
- **Calibration Diagram**: Predicted vs actual probabilities
- **City Heatmap**: Win rate by city over time
- **Confidence Distribution**: Performance by confidence level
- **Monthly Returns**: Return by month
- **Win/Loss Distribution**: Histogram of trade outcomes
- **Sharpe Over Time**: Rolling Sharpe ratio

**Key Functions**:
```python
def plot_equity_curve(daily_balances: List[int]) -> Figure
    """Plot portfolio value over time"""

def plot_drawdown(daily_balances: List[int]) -> Figure
    """Plot drawdown from peak"""

def plot_calibration(
    predicted_probs: List[float],
    actual_outcomes: List[bool]
) -> Figure
    """Plot calibration diagram"""

def plot_city_performance(
    trades_by_city: Dict[str, List[Trade]]
) -> Figure
    """Heatmap of win rate by city"""
```

---

## Implementation Phases

### Phase 10.1: Core Framework
1. Implement `BacktestConfig` and `HistoricalDataLoader`
2. Build `BacktestSimulator` with basic functionality
3. Implement `PerformanceMetrics` with essential statistics
4. Create basic reporting (CSV export)

### Phase 10.2: Advanced Analytics
1. Implement `MonteCarloSimulator`
2. Build `WalkForwardOptimizer`
3. Implement `CounterfactualAnalyzer`
4. Add visualization functions

### Phase 10.3: Production Polish
1. Optimize for speed (caching, parallel processing)
2. Add comprehensive HTML reporting
3. Create example backtest scenarios
4. Write documentation and usage guide

---

## Data Sources & Integration

### Historical Weather Data
- **Open-Meteo Historical API**: Free archive of weather data
  - Endpoint: `https://archive-api.open-meteo.com/v1/archive`
  - Parameters: `start_date`, `end_date`, `latitude`, `longitude`
  - Returns: Hourly/daily temperature history

- **NOAA/NWS Archive**: Official temperature resolution data
  - Free access to historical climatological records
  - Used for ground truth temperature outcomes

### Kalshi Market Data
- **Stored Snapshots**: Cache of market state at key times
  - Bucket definitions per city/date
  - Market activity patterns
  
- **Price History**: Historical price sequences
  - Can use GET `/markets/{id}/history` if available
  - Or reconstruct from trading volume/liquidity patterns

### Weather Bias State
- **Historical Bias File**: Replay exact bias learner state at each date
  - Load `station_bias_history.json` with data up to test date
  - Prevents look-ahead bias in bias corrections

---

## Success Criteria

✅ Can efficiently replay 3+ months of historical data  
✅ Results show positive expectancy under realistic assumptions  
✅ Brier score and calibration metrics documented  
✅ Edge realization rate > 50% on positive-edge trades  
✅ Sharpe ratio > 1.0 (indicates strong risk-adjusted returns)  
✅ Maximum drawdown < 15% of starting capital  
✅ Win rate > 50% on recommended trades  
✅ Comprehensive performance breakdown by city/season  
✅ Counterfactual experiments reveal impact of each component  
✅ Walk-forward results show consistency across time periods  
✅ HTML report provides actionable insights  
✅ System performs well across parameter ranges (robustness)

---

## Next Steps

1. **Implement Phase 10.1** (Core Framework)
   - Create `BacktestConfig` and data loaders
   - Build `BacktestSimulator`
   - Implement basic metrics
   - Create first CSV export

2. **Test with Sample Period**
   - Run backtest on known historical period
   - Validate against known outcomes
   - Document results

3. **Implement Phase 10.2** (Advanced Analytics)
   - Add Monte Carlo
   - Build walk-forward optimizer
   - Implement counterfactual experiments

4. **Production Polish** (Phase 10.3)
   - Optimize performance
   - Generate beautiful HTML reports
   - Create usage guide and examples

---

**Timeline**: Phase 10.1 (2-3 hours), 10.2 (2-3 hours), 10.3 (1-2 hours)

**Estimated Total**: 5-8 hours for complete backtesting framework

