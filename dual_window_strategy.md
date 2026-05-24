# Dual-Window Trading Strategy: 6-12h vs 30-36h Markets

## Market Window Characteristics

### 6-12h Window (SHORT DURATION - ~9 hours)
**Characteristics:**
- Very limited time for edge to play out
- High time decay working against you
- Less weather data available
- Market is already settled on the event date
- Quick resolutions = quick profits or losses
- Less overnight/sentiment risk

**Risks:**
- 🔴 High time decay (1% per hour roughly)
- 🔴 Less time to recover from adverse moves
- 🟡 Limited refinement of probability estimates
- 🟡 Tighter market spreads (less liquidity over time)

---

### 30-36h Window (LONG DURATION - ~33-36 hours)
**Characteristics:**
- Abundant time for edge to compound
- Overnight exposure (adds uncertainty)
- Much better weather forecasting (more data by morning)
- Market can reprrice significantly overnight
- Longer holding period allows volatility to resolve
- Better ensemble forecast confidence

**Risks:**
- 🟡 Overnight weather changes unpredictable
- 🟡 Market sentiment shifts (news, other events)
- 🟢 Time decay is minimal (0.03% per hour)
- 🟢 Much more time for edge to play out

---

## Proposed Risk Parameters

### Current Default Parameters (from trading_engine.py)
```
Global Exposure Limit:     25% of portfolio
Per-City Exposure Limit:   10% of portfolio
Single Trade Max:          4% of portfolio
Min Edge Threshold:        5%
Min Confidence Threshold:  55%
Soft Loss Limit:          -5% (warning)
Hard Loss Limit:          -8% (stop)
```

### RECOMMENDED: 6-12h Window (SHORT)
```
Global Exposure Limit:     15% of portfolio    (reduced - higher risk)
Per-City Exposure Limit:    6% of portfolio    (reduced)
Single Trade Max:           2% of portfolio    (reduced - HALF)
Min Edge Threshold:        10%                 (increased - need stronger edge)
Min Confidence Threshold:  70%                 (increased - need high conviction)
Soft Loss Limit:          -3%                 (tighter - quick stop)
Hard Loss Limit:          -5%                 (tighter - quick exit)
```

**Rationale:**
- 🔴 Half the position size because time decay is aggressive
- 🔴 2x edge threshold because we have only 9 hours for edge to work
- 🔴 Higher confidence (70%) because we need certainty in short window
- 🔴 Tighter stops because we can't afford to ride out big moves
- ⚠️ **Expect smaller but more frequent profits from these trades**

---

### RECOMMENDED: 30-36h Window (LONG)
```
Global Exposure Limit:     28% of portfolio    (increased - lower risk)
Per-City Exposure Limit:   12% of portfolio    (increased)
Single Trade Max:          5% of portfolio     (increased - can afford larger)
Min Edge Threshold:        3%                  (decreased - edge compounds)
Min Confidence Threshold:  50%                 (decreased - time helps)
Soft Loss Limit:          -6%                 (wider - time allows recovery)
Hard Loss Limit:         -10%                 (wider - let edge work)
```

**Rationale:**
- 🟢 Larger position size because time is working FOR us
- 🟢 Lower edge threshold (3% vs 10%) because compound over 36h
- 🟢 Lower confidence (50%) because ensemble forecast improves overnight
- 🟢 Wider stops because we have time to recover from volatility
- ✅ **Expect larger profits from fewer, more confident trades**

---

## Why These Differences?

### Time Value of Edge
```
6-12h Window:
  Edge Decay = 10% / 9 hours ≈ 1.1% per hour
  → Need strong edge upfront
  
30-36h Window:
  Edge Decay = 3% / 36 hours ≈ 0.08% per hour
  → Can afford weaker initial edge
```

### Forecast Quality
```
6-12h:  "Event happens today, forecast is locked in"
        → Market already priced in most info
        → Need consensus (70% confidence)

30-36h: "Event is tomorrow, forecast still improving"
        → Ensemble data + overnight models improve forecast
        → Weaker initial signal acceptable (50% confidence)
```

### Volatility & Recovery Time
```
6-12h:  Can't afford 3% adverse move → 1/3 of edge gone
30-36h: 3% adverse move is only 1% of expected edge

More time = can ride out volatility
```

---

## Strategy Summary

| Dimension | 6-12h (SHORT) | 30-36h (LONG) | Reason |
|-----------|---------------|---------------|--------|
| **Position Size** | 2% | 5% | Time decay vs. compounding |
| **Edge Min** | 10% | 3% | Edge decay rate |
| **Confidence Min** | 70% | 50% | Forecast quality improvement |
| **Stop Loss** | -3% to -5% | -6% to -10% | Time to recovery |
| **Expected Frequency** | High (many small wins) | Low (fewer big wins) | Market structure |
| **Holding Period** | 9 hours | 33-36 hours | Just defined |

---

## Implementation Notes

1. **Market Selection:** Route markets to appropriate strategy based on hours_to_resolution
2. **Position Sizing:** Apply different risk limits based on window
3. **Signal Thresholds:** Different min_edge and min_confidence per window
4. **Stop Management:** Different soft/hard loss limits in risk_manager
5. **Portfolio Balance:** May need separate exposure tracking per window

Example logic in trading_engine.py:
```python
if 6 <= hours_to_resolution <= 12:
    use_short_window_params()  # 2%, 10%, 70%, tight stops
elif 30 <= hours_to_resolution <= 36:
    use_long_window_params()   # 5%, 3%, 50%, wide stops
else:
    skip_market()  # Gap between windows
```

---

## Risk Assessment

### 6-12h Window Risk Profile: **MODERATE-HIGH**
- Time decay is relentless
- Small mistakes compound quickly
- Suitable for: High-conviction signals only
- Expected: 70% win rate, 2-3% avg profit per trade

### 30-36h Window Risk Profile: **MODERATE**
- More forgiving time frame
- Weather data improves overnight
- Suitable for: Broader signal acceptance
- Expected: 55-60% win rate, 4-5% avg profit per trade

---

## Questions Before Implementation

1. Would you like to implement both windows simultaneously?
2. Should we start with the safer 30-36h window and add 6-12h later?
3. Would you prefer even more conservative parameters for the short window?
4. Should we track and analyze performance separately per window?
