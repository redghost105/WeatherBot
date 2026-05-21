# Phase 8 Example: A Complete Trading Day

## Scenario: May 21, 2026 - Trading Session

This example shows **real data structures** flowing through the system, with **actual orders placed** and **actual rejections** with reasons.

---

## MORNING: WeatherPredictor Generates Signals

The WeatherPredictor analyzes real weather data and creates 5 trade signals. The ExecutionService evaluates each one.

---

### **SIGNAL #1: NYC Temperature - STRONG EDGE** ✅ ACCEPTED

#### Input Data from WeatherPredictor

```python
# WeatherPredictor output
edge_summary = {
    "city": "New York City",
    "station_id": "KXHIGHNY",
    "market_date": "2026-05-21",
    "confidence": 78.5,
    "weather_data": {
        "temperature": 72.0,  # Current
        "ensemble_members": 10,
        "ensemble_std": 1.8,  # Tight agreement
        "daily_forecast": [...],
        "ensemble_forecast": [...]
    },
    "edges": [
        {
            "bucket_label": ">75°",
            "model_prob": 0.68,      # Model says 68% chance
            "market_prob": 0.52,     # Market says 52% chance
            "edge": 0.16,            # 16% edge (LARGE!)
            "recommendation": "STRONG_BUY",
            "conviction": 0.92
        }
    ]
}
```

#### ExecutionService Receives TradeSignal

```python
signal = TradeSignal(
    ticker="KXHIGHNY-26MAY21-T75",
    city="New York City",
    bucket_label=">75°",
    action="buy",
    side="yes",
    suggested_size=5,
    model_probability=0.68,
    market_probability=0.52,
    edge_pct=0.16,              # 16% edge
    confidence=78.5,             # Good confidence
    timestamp=datetime.now(timezone.utc)
)
```

#### Validation Checks

```
Signal Validation:
✓ Edge 16% > threshold 5%          PASS
✓ Confidence 78.5 > threshold 60   PASS
✓ Position size 5 <= limit 10      PASS
✓ Daily P&L 0 > limit -$1000       PASS

Market Checks:
✓ Market KXHIGHNY-26MAY21-T75 exists
✓ Status: "active" (open for trading)
✓ Orderbook has liquidity
```

#### Order Placed

```python
order = OrderRecord(
    order_id="kalshi-12345",
    client_order_id="550e8400-e29b-41d4-a716-446655440001",
    ticker="KXHIGHNY-26MAY21-T75",
    action="buy",
    side="yes",
    count=5,                       # 5 contracts
    yes_price=68,                  # $0.68/contract
    status=OrderStatus.FILLED,
    filled_quantity=5,
    filled_price=0.68,
    filled_ts=datetime.now(timezone.utc)
)
```

#### Audit Log Entry

```json
{
  "timestamp": "2026-05-21T09:15:32.123456+00:00",
  "event_type": "live_order_placed",
  "mode": "live",
  "ticker": "KXHIGHNY-26MAY21-T75",
  "order_id": "kalshi-12345",
  "action": "buy",
  "side": "yes",
  "count": 5,
  "price": 0.68,
  "edge_pct": 0.16,
  "confidence": 78.5,
  "status": "placed"
}
```

#### Console Output

```
[09:15] 📊 NYC MARKET ANALYSIS
        Current Temp: 72°F
        Ensemble Std: 1.8° (tight, confident)
        Forecast: 74°F
        Confidence: 78.5/100

[09:15] 💡 EDGE DETECTED
        Market thinks: 52% chance temp > 75°
        Model thinks: 68% chance temp > 75°
        EDGE: +16% ← STRONG EDGE!

[09:15] ✅ VALIDATION PASSED
        ✓ Edge 16% > 5% threshold
        ✓ Confidence 78.5 > 60
        ✓ Daily P&L OK (0 > -$1000)
        ✓ Market active

[09:16] 📤 ORDER #1: BUY KXHIGHNY-26MAY21-T75
        Size: 5 contracts
        Price: $0.68 each = $3.40 total
        Side: YES (temp will exceed 75°)
        Status: FILLED ✓
```

---

### **SIGNAL #2: Chicago Temperature - WEAK EDGE** ❌ REJECTED

#### Input Data from WeatherPredictor

```python
edge_summary = {
    "city": "Chicago",
    "station_id": "KXHIGHCHI",
    "confidence": 65.2,  # Moderate confidence
    "weather_data": {
        "temperature": 62.0,
        "ensemble_std": 2.8,  # Looser agreement
        "forecast": 64°F
    },
    "edges": [
        {
            "bucket_label": ">65°",
            "model_prob": 0.53,      # Model says 53%
            "market_prob": 0.51,     # Market says 51%
            "edge": 0.02,            # Only 2% edge (WEAK!)
            "recommendation": "SKIP",
            "conviction": 0.55
        }
    ]
}
```

#### ExecutionService Receives TradeSignal

```python
signal = TradeSignal(
    ticker="KXHIGHCHI-26MAY21-T65",
    city="Chicago",
    bucket_label=">65°",
    action="buy",
    side="yes",
    suggested_size=3,
    model_probability=0.53,
    market_probability=0.51,
    edge_pct=0.02,               # Only 2% edge (BAD!)
    confidence=65.2,
    timestamp=datetime.now(timezone.utc)
)
```

#### Validation Check - FAILS

```
Signal Validation:
✗ Edge 2% < threshold 5%          FAIL ← Rejected here!
  (Would have checked others if this passed)
```

#### Result: REJECTED

```python
# Order rejected, NOT created
success = False
reason = "Edge below minimum threshold"
```

#### Audit Log Entry

```json
{
  "timestamp": "2026-05-21T09:17:45.234567+00:00",
  "event_type": "signal_rejected",
  "mode": "live",
  "ticker": "KXHIGHCHI-26MAY21-T65",
  "reason": "Edge below minimum threshold",
  "edge_pct": 0.02,
  "min_threshold": 0.05,
  "confidence": 65.2
}
```

#### Console Output

```
[09:17] 💡 EDGE DETECTED (weak)
        Market: 51%
        Model: 53%
        Edge: +2% ← Below 5% minimum!

[09:17] ❌ TRADE REJECTED
        Reason: "Edge below minimum threshold (2% < 5%)"
        Status: Waiting for next signal
```

---

### **SIGNAL #3: Miami Temperature - LOW CONFIDENCE** ❌ REJECTED

#### Input Data from WeatherPredictor

```python
edge_summary = {
    "city": "Miami",
    "station_id": "KXHIGHMIA",
    "confidence": 45.0,  # LOW CONFIDENCE!
    "weather_data": {
        "temperature": 86.0,
        "ensemble_std": 4.2,  # Very loose agreement
        "forecast_uncertain": True
    },
    "edges": [
        {
            "bucket_label": ">92°",
            "model_prob": 0.61,
            "market_prob": 0.48,
            "edge": 0.13,  # Edge is good...
            "recommendation": "BUY",
            "conviction": 0.58
        }
    ]
}
```

#### ExecutionService Receives TradeSignal

```python
signal = TradeSignal(
    ticker="KXHIGHMIA-26MAY21-T92",
    city="Miami",
    bucket_label=">92°",
    action="buy",
    side="yes",
    suggested_size=4,
    model_probability=0.61,
    market_probability=0.48,
    edge_pct=0.13,               # Edge OK
    confidence=45.0,              # Confidence too low!
    timestamp=datetime.now(timezone.utc)
)
```

#### Validation Check - FAILS

```
Signal Validation:
✓ Edge 13% > threshold 5%
✗ Confidence 45 < threshold 60   FAIL ← Rejected here!
```

#### Result: REJECTED

```python
success = False
reason = "Confidence below threshold"
```

#### Console Output

```
[09:18] 💡 EDGE DETECTED (but uncertain)
        Market: 48%
        Model: 61%
        Edge: +13% ← Good edge...
        Confidence: 45/100 ← But too uncertain!

[09:18] ❌ TRADE REJECTED
        Reason: "Confidence below threshold (45 < 60)"
        Status: Waiting for clearer signal
```

---

### **SIGNAL #4: Los Angeles Temperature - TOO MUCH SIZE** ❌ REJECTED

#### Input Data from WeatherPredictor

```python
edge_summary = {
    "city": "Los Angeles",
    "station_id": "KXHIGHLAX",
    "confidence": 82.3,
    "weather_data": {
        "temperature": 71.0,
        "ensemble_std": 1.2  # Tight!
    },
    "edges": [
        {
            "bucket_label": ">75°",
            "model_prob": 0.72,
            "market_prob": 0.58,
            "edge": 0.14,
            "recommendation": "STRONG_BUY",
            "conviction": 0.95
        }
    ]
}
```

#### ExecutionService Receives TradeSignal

```python
signal = TradeSignal(
    ticker="KXHIGHLAX-26MAY21-T75",
    city="Los Angeles",
    bucket_label=">75°",
    action="buy",
    side="yes",
    suggested_size=15,            # TOO LARGE!
    model_probability=0.72,
    market_probability=0.58,
    edge_pct=0.14,
    confidence=82.3,
    timestamp=datetime.now(timezone.utc)
)
```

#### Validation Check - FAILS

```
Signal Validation:
✓ Edge 14% > threshold 5%
✓ Confidence 82.3 > threshold 60
✗ Position size 15 > limit 10    FAIL ← Rejected here!
```

#### Result: REJECTED

```python
success = False
reason = "Position size (15) exceeds limit (10)"
```

#### Console Output

```
[09:19] 💡 EDGE DETECTED
        Edge: 14%, Confidence: 82.3/100
        Suggested Size: 15 contracts ← Too large!

[09:19] ❌ TRADE REJECTED
        Reason: "Position size (15) exceeds limit (10)"
        Status: Could retry with smaller size
```

---

### **SIGNAL #5: Denver Temperature - STRONG SIGNAL** ✅ ACCEPTED

#### Input Data from WeatherPredictor

```python
edge_summary = {
    "city": "Denver",
    "station_id": "KXHIGHDEN",
    "confidence": 76.8,
    "weather_data": {
        "temperature": 65.0,
        "ensemble_std": 1.5,
        "forecast": 67°F
    },
    "edges": [
        {
            "bucket_label": ">68°",
            "model_prob": 0.66,
            "market_prob": 0.54,
            "edge": 0.12,
            "recommendation": "BUY",
            "conviction": 0.88
        }
    ]
}
```

#### ExecutionService Receives TradeSignal

```python
signal = TradeSignal(
    ticker="KXHIGHDEN-26MAY21-T68",
    city="Denver",
    bucket_label=">68°",
    action="buy",
    side="yes",
    suggested_size=4,
    model_probability=0.66,
    market_probability=0.54,
    edge_pct=0.12,
    confidence=76.8,
    timestamp=datetime.now(timezone.utc)
)
```

#### Validation Checks - ALL PASS

```
Signal Validation:
✓ Edge 12% > threshold 5%
✓ Confidence 76.8 > threshold 60
✓ Position size 4 <= limit 10
✓ Daily P&L $1.75 > limit -$1000  (from NYC trade)

Market Checks:
✓ Market KXHIGHDEN-26MAY21-T68 exists
✓ Status: "active"
✓ Orderbook healthy
```

#### Order Placed

```python
order = OrderRecord(
    order_id="kalshi-12346",
    client_order_id="550e8400-e29b-41d4-a716-446655440002",
    ticker="KXHIGHDEN-26MAY21-T68",
    action="buy",
    side="yes",
    count=4,
    yes_price=66,
    status=OrderStatus.FILLED,
    filled_quantity=4,
    filled_price=0.66,
    filled_ts=datetime.now(timezone.utc)
)
```

#### Console Output

```
[09:20] 📊 DENVER MARKET ANALYSIS
        Confidence: 76.8/100
        Current: 65°F
        Ensemble: Tight agreement
        Forecast: 67°F → Could hit >68°

[09:20] 💡 EDGE DETECTED
        Market: 54%
        Model: 66%
        Edge: +12% ✓

[09:20] ✅ ALL CHECKS PASSED
        ✓ Edge OK (12% > 5%)
        ✓ Confidence OK (76.8 > 60)
        ✓ Size OK (4 <= 10)
        ✓ Capital OK

[09:21] 📤 ORDER #2: BUY KXHIGHDEN-26MAY21-T68
        Size: 4 contracts
        Price: $0.66 each = $2.64 total
        Status: FILLED ✓
```

---

## MID-DAY: Position Monitoring

### Current Position Status

```
LIVE POSITIONS - 12:30 PM UTC
════════════════════════════════════════════════════════════════

Market 1: KXHIGHNY-26MAY21-T75
├─ Status: OPEN
├─ Position: +5 contracts
├─ Entry: $0.68/contract
├─ Current Market Price: $0.72
├─ Unrealized P&L: +$0.20/contract × 5 = +$1.00
└─ Reason: Temperature rising, edge confirmed

Market 2: KXHIGHDEN-26MAY21-T68
├─ Status: OPEN
├─ Position: +4 contracts
├─ Entry: $0.66/contract
├─ Current Market Price: $0.67
├─ Unrealized P&L: +$0.01/contract × 4 = +$0.04
└─ Reason: Market slower to confirm signal

SUMMARY
════════════════════════════════════════════════════════════════
Total Contracts: 9
Total Invested: $6.04
Current Value: $6.08
Unrealized P&L: +$0.04 (after fees)
Win Rate: 2/2 positions profitable
```

---

## AFTERNOON: Markets Resolve

### Final Temperatures (Official NWS Data)

```
NYC:     78°F (predicted >75° ✓ CORRECT)
Denver:  69°F (predicted >68° ✓ CORRECT)
```

### Resolution & PnL Calculation

#### NYC Position Resolution

```python
order = orders["kalshi-12345"]
order.resolution_value = 78.0  # Official temp

# YES contracts win (we predicted >75°, actual 78°)
entry_cost = 0.68 * 5 = $3.40
exit_value = 1.00 * 5 = $5.00  # YES contracts worth $1 each
realized_pnl = $5.00 - $3.40 = $1.60

order.pnl = 1.60  # In dollars
order.status = OrderStatus.FILLED  # Mark as resolved
```

#### Denver Position Resolution

```python
order = orders["kalshi-12346"]
order.resolution_value = 69.0

# YES contracts win (we predicted >68°, actual 69°)
entry_cost = 0.66 * 4 = $2.64
exit_value = 1.00 * 4 = $4.00
realized_pnl = $4.00 - $2.64 = $1.36
```

### Daily Summary

```
TRADING DAY RESULTS - May 21, 2026
════════════════════════════════════════════════════════════════

ORDERS PLACED
✓ NYC (KXHIGHNY-26MAY21-T75):    +5 contracts @ $0.68 = PROFIT $1.60
✓ Denver (KXHIGHDEN-26MAY21-T68): +4 contracts @ $0.66 = PROFIT $1.36

ORDERS REJECTED
✗ Chicago (weak edge 2% < 5%)
✗ Miami (low confidence 45 < 60)
✗ LA (position too large 15 > 10)

DAILY FINANCIALS
════════════════════════════════════════════════════════════════
Total Invested:      $6.04
Total Realized:      $9.36
Daily Profit:        $2.96
Win Rate:            2/2 (100%)
Rejection Rate:      3/5 signals (60% filtered out)
Average Edge Taken:  13% (NYC 16%, Denver 12%)
Average Confidence:  77.6/100
```

### Audit Trail Summary

```json
[
  {
    "timestamp": "2026-05-21T09:16:32.123456+00:00",
    "event_type": "live_order_placed",
    "ticker": "KXHIGHNY-26MAY21-T75",
    "count": 5,
    "price": 0.68,
    "status": "filled"
  },
  {
    "timestamp": "2026-05-21T09:17:45.234567+00:00",
    "event_type": "signal_rejected",
    "ticker": "KXHIGHCHI-26MAY21-T65",
    "reason": "Edge below minimum threshold"
  },
  {
    "timestamp": "2026-05-21T09:18:52.345678+00:00",
    "event_type": "signal_rejected",
    "ticker": "KXHIGHMIA-26MAY21-T92",
    "reason": "Confidence below threshold"
  },
  {
    "timestamp": "2026-05-21T09:19:33.456789+00:00",
    "event_type": "signal_rejected",
    "ticker": "KXHIGHLAX-26MAY21-T75",
    "reason": "Position size exceeds limit"
  },
  {
    "timestamp": "2026-05-21T09:21:11.567890+00:00",
    "event_type": "live_order_placed",
    "ticker": "KXHIGHDEN-26MAY21-T68",
    "count": 4,
    "price": 0.66,
    "status": "filled"
  },
  {
    "timestamp": "2026-05-21T16:30:00.678901+00:00",
    "event_type": "resolution_reconciled",
    "ticker": "KXHIGHNY-26MAY21-T75",
    "resolution_value": 78.0,
    "pnl": 1.60
  },
  {
    "timestamp": "2026-05-21T16:30:05.789012+00:00",
    "event_type": "resolution_reconciled",
    "ticker": "KXHIGHDEN-26MAY21-T68",
    "resolution_value": 69.0,
    "pnl": 1.36
  }
]
```

### Learning Loop Update

```python
# HistoricalBiasLearner receives outcomes
bias_learner.update(
    station_id="KXHIGHNY",
    forecast_high=72.0,    # What model predicted
    actual_high=78.0,      # What actually happened
    date="2026-05-21"
)

bias_learner.update(
    station_id="KXHIGHDEN",
    forecast_high=67.0,
    actual_high=69.0,
    date="2026-05-21"
)

# Tomorrow's forecasts will be 2-3°F more accurate based on this
```

---

## Key Takeaways

### What Got Executed
- **NYC Order**: Strong edge (16%), high confidence (78.5) → **PLACED & PROFITABLE**
- **Denver Order**: Good edge (12%), high confidence (76.8) → **PLACED & PROFITABLE**

### What Got Rejected
- **Chicago**: Edge too small (2% vs 5% minimum) → **IGNORED** (correct call)
- **Miami**: Confidence too low (45 vs 60 minimum) → **IGNORED** (correct call)
- **LA**: Position size too large (15 vs 10 max) → **IGNORED** (correct call)

### System Discipline
- ✅ Rejected 60% of signals (saved capital on weak trades)
- ✅ Only traded highest-confidence, largest-edge opportunities
- ✅ Tracked every decision in audit trail
- ✅ Fed actual outcomes back to improve tomorrow's predictions
- ✅ Profit = $2.96 from disciplined execution

---

This is what a **real trading day** looks like through Phase 8's eyes!
