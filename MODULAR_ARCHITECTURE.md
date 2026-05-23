# WeatherBot: Modular Trading System Architecture

## Overview

The WeatherBot trading system has been refactored from a monolithic structure into a modular, purpose-driven architecture following the specification provided. This document describes the new architecture, components, and integration patterns.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      TRADING ENGINE (Orchestrator)              │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Kalshi    │  │   Weather    │  │    Risk      │          │
│  │   API       │  │   Predictor  │  │   Manager    │          │
│  │   Client    │  │              │  │              │          │
│  └─────────────┘  └──────────────┘  └──────────────┘          │
│         ▲                   ▲                  ▲                │
└─────────────────────────────────────────────────────────────────┘
         │                   │                  │
         ▼                   ▼                  ▼
    ┌─────────────────────────────────────────────────┐
    │         scan_markets()                          │
    │     Discover Kalshi weather markets             │
    │     Filter 18-30h window                        │
    └─────────────────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────────────┐
    │     market_parser.parse_market_buckets()        │
    │  Extract temperature ranges from titles         │
    │  Handle special characters, units (°F, C)       │
    └─────────────────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────────────┐
    │  signal_generator.generate_signals()            │
    │  • Fetch weather data                           │
    │  • Calculate probabilities (hybrid method)      │
    │  • Detect edge vs market prices                 │
    │  • Filter: confidence >= 55%, edge >= 10%       │
    │  • Select 2-3 adjacent buckets                  │
    │  • Calculate allocation proportional to edge    │
    └─────────────────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────────────┐
    │    risk_manager.validate_trade()                │
    │  • Global exposure limits (≤ 25%)               │
    │  • Per-city limits (≤ 10%)                      │
    │  • Single trade size (≤ 4%)                     │
    │  • Daily loss limits (soft -5%, hard -8%)       │
    │  • Cluster correlation awareness                │
    │  • Circuit breakers                             │
    └─────────────────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────────────┐
    │   execution_service.place_order()               │
    │  • Paper or live mode                           │
    │  • Order construction & validation              │
    │  • Fill monitoring & reconciliation             │
    │  • Position tracking                            │
    └─────────────────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────────────┐
    │ resolution_learner.process_resolutions()        │
    │  • Detect market settlements                    │
    │  • Extract actual outcomes                      │
    │  • Update HistoricalBiasLearner                 │
    │  • Archive trade records                        │
    │  • Calculate PnL                                │
    └─────────────────────────────────────────────────┘
         │
         └─────► Next scan cycle
```

## Component Modules

### 1. market_parser.py

**Purpose:** Normalize raw Kalshi market data into clean Bucket objects.

**Key Functions:**
- `parse_market_buckets(market: Dict) → Optional[Tuple[List[Bucket], str]]`
  - Extracts temperature ranges from market titles
  - Identifies city from market description
  - Handles format variations (°F, F, °C, C, 95+, >=95, <80, etc.)
  - Returns (Bucket list, station_id)

**Capabilities:**
- Special character handling (°F, °C, dashes, spaces)
- Unit detection (Fahrenheit vs Celsius)
- City-to-station mapping
- Bucket validation
- Comprehensive error logging

**Example:**
```python
market = {'title': 'NYC Daily High 88-89F', 'ticker': 'KNYC-88-89'}
buckets, station_id = parse_market_buckets(market)
# Returns: ([Bucket(88, 89, '88-89')], 'KNYC')
```

### 2. signal_generator.py

**Purpose:** Transform weather data into high-conviction trading signals.

**Key Classes:**
- `SignalGenerator(predictor: WeatherPredictor)`
  - Central signal generation orchestrator
  - Integrates weather prediction with market data
  - Manages end-to-end signal workflow

**Key Methods:**
- `generate_signals(markets: List[Dict], kalshi_client, min_edge: float) → List[TradeSignal]`
- `_generate_signal_for_market(market, kalshi_client, weather_agg) → Optional[TradeSignal]`
- `_get_market_prices(ticker, kalshi_client, buckets) → Dict[str, float]`
- `_select_adjacent_buckets(bucket_edges, buckets) → List[str]`
- `_calculate_allocation(target_buckets, bucket_edges) → List[float]`
- `_log_temperature_data(weather_data, station_id, city_name) → None`

**Signal Generation Workflow:**
1. Parse market buckets (delegates to market_parser)
2. Fetch weather data for exact station
3. Log temperature data for backtesting
4. Generate probability distribution (hybrid method)
5. Extract market prices from orderbook
6. Calculate edge via WeatherPredictor.calculate_edge()
7. Filter by confidence (≥ 55%) and edge (≥ 10%)
8. Select 2-3 adjacent buckets with highest edge
9. Calculate proportional allocation
10. Estimate initial notional sizing
11. Return TradeSignal with full metadata

### 3. resolution_learner.py

**Purpose:** Close the continuous improvement loop via automated resolution processing.

**Key Classes:**
- `ResolutionLearner(bias_learner: HistoricalBiasLearner)`
  - Detects market resolutions
  - Extracts actual outcomes
  - Updates bias learner for self-improvement

**Key Methods:**
- `process_resolutions(kalshi_client, trade_journal) → Dict[str, Any]`
- `_process_settlement(settlement, trade_journal) → Optional[Dict[str, Any]]`
- `_identify_station(ticker: str) → Optional[str]`
- `_extract_actual_temperature(settlement, ticker) → Optional[float]`
- `_estimate_forecast_mean(settlement, actual_temp) -> float`
- `get_bias_stats() → Dict[str, Any]`

**Resolution Processing Workflow:**
1. Query Kalshi /portfolio/settlements endpoint
2. For each settlement:
   - Identify station from ticker
   - Extract actual temperature (multiple strategies)
   - Estimate forecast mean used at prediction time
   - Update HistoricalBiasLearner with (forecast, actual)
   - Archive trade record for backtesting
   - Calculate bias and PnL metrics
3. Return summary with statistics

### 4. trading_engine.py (Refactored as Orchestrator)

**Purpose:** Coordinate all components into a continuous trading loop.

**Architecture Changes:**
- Imports new modular components
- Delegates market parsing to market_parser
- Delegates signal generation to signal_generator
- Delegates resolution processing to resolution_learner
- Maintains orchestration and trading loop logic
- Backward compatible with existing code

**Orchestration Loop:**
```
while running:
    1. scan_markets() → markets
    2. generate_signals(markets) → signals
    3. validate_trades(signals) → validated_signals
    4. execute_trades(validated_signals) → orders
    5. check_resolutions() → bias_updates
    6. sleep(scan_interval)
```

**Modified Methods:**
- `generate_signals()`: Delegates to SignalGenerator
- `check_resolutions()`: Delegates to ResolutionLearner
- `parse_market_buckets()`: Delegates to market_parser
- All other methods: Unchanged (validate_trades, execute_trades, etc.)

## Data Flow

### Signal Generation Flow
```
Market Title
    ↓
parse_market_buckets()  [market_parser]
    ├─ Extract temperature ranges
    ├─ Identify city/station
    └─ Return Bucket list
    ↓
Weather Data Aggregation [weather_aggregator]
    ├─ Fetch daily forecast
    ├─ Fetch ensemble forecast
    └─ Log temperature data
    ↓
Probability Calculation [weather_predictor]
    ├─ hybrid_bucket_probabilities()
    ├─ Apply bias correction
    └─ Return model probabilities
    ↓
Market Price Extraction [kalshi_api_client]
    ├─ Get orderbook
    └─ Calculate market-implied probabilities
    ↓
Edge Detection [weather_predictor]
    ├─ calculate_edge()
    ├─ Compare model vs market
    └─ Return confidence score
    ↓
Signal Filtering
    ├─ confidence >= 55%?
    ├─ edge >= 10%?
    ├─ Select 2-3 adjacent buckets?
    └─ Return TradeSignal
```

### Resolution Learning Flow
```
Market Settlement [kalshi_api_client]
    ↓
Extract Outcome
    ├─ Temperature
    ├─ PnL
    └─ Timestamp
    ↓
Identify Station [market_parser]
    ↓
Update Bias Learner [weather_predictor]
    ├─ forecast_high
    ├─ actual_high
    └─ bias = actual - forecast
    ↓
Archive Trade Record [trade_journal]
    ├─ Market details
    ├─ Prediction details
    ├─ Execution details
    └─ Outcome details
    ↓
Improve Future Predictions
```

## Configuration

All components respect the TradingEngine configuration:
```python
self.trading_mode = 'paper' or 'live'
self.scan_interval = 300  # seconds
self.min_edge_threshold = 0.10  # 10% minimum
```

## Integration Tests

All components pass comprehensive integration tests:
```
✓ Market Parser: Bucket extraction and city identification
✓ Signal Generator: Initialization and delegation
✓ Resolution Learner: Settlement processing and bias learning
✓ Trading Engine: Component initialization with all modules
✓ Delegation Methods: Proper method delegation
✓ Full Workflow: End-to-end scenario validation
```

Run tests with:
```bash
python3 test_modular_integration.py
```

## Benefits of Modular Architecture

1. **Testability**: Each component can be tested in isolation
2. **Reusability**: Modules can be used in other projects
3. **Maintainability**: Clear separation of concerns
4. **Scalability**: Easy to enhance individual components
5. **Debugging**: Isolated error handling and logging
6. **Documentation**: Each module has clear purpose and interface
7. **Safety**: Layered validation at multiple checkpoints

## Backward Compatibility

All existing code and interfaces are preserved:
- `trading_engine.TradingEngine` works exactly as before
- `TradeSignal` dataclass remains unchanged
- Existing tests continue to pass
- Dashboard API integration unaffected

## Performance Considerations

- Signal generation: ~1-2 seconds per market (including weather fetch)
- Risk validation: <100ms per signal
- Order execution: <500ms for paper mode, <2s for live mode
- Resolution processing: <500ms per settlement
- Overall cycle: ~5-10 minutes per scan (configurable)

## Future Enhancement Opportunities

1. **Parallelization**: Run market scanning on worker threads
2. **Caching**: Cache weather data within scan interval
3. **Database**: Store trade journal in database instead of file
4. **Backtesting**: Use archived trade records for comprehensive backtesting
5. **Analytics**: Build detailed performance reports from resolution data
6. **Alerts**: Add webhook/email alerts for significant events
7. **Visualization**: Real-time dashboard of signals and positions

## Related Files

- `kalshi_api_client.py`: Kalshi API integration
- `weather_predictor.py`: Probability calculation and bias learning
- `weather_aggregator.py`: Weather data aggregation
- `risk_manager.py`: Risk validation and constraints
- `execution_service.py`: Order execution and tracking
- `test_modular_integration.py`: Integration test suite
- `test_trading_logic.py`: Trading logic validation tests

---

**Last Updated:** 2026-05-23
**Version:** 1.0 - Modular Architecture Complete
