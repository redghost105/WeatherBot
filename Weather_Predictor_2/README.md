# Paruchh v3 — Polymarket Weather Trading Bot

A complete implementation of the Paruchh v3 strategy for trading weather temperature bins on Polymarket.

**Key features:**
- 3-model weather consensus (ICON, GFS, ECMWF) with `bias_correction=true`
- 18-30 hour entry window (sweet spot for fresh models + market repricing)
- 3-bin portfolio strategy (center ± adjacents based on model agreement)
- Paper trading mode for validation (30+ closed bets before live)
- Automatic Telegram alerts for trades placed/resolved
- 11 cities across 3 continents with verified airport coordinates

**Expected performance:** +45.9% ROI over 3 days (from PDF guide)

---

## Setup

### 1. Create virtual environment
```bash
cd parurchh_weather_bot
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure credentials
```bash
cp .env.example .env
# Edit .env with your Polymarket credentials
```

### 3. (Optional) Set up Telegram alerts
```bash
# In .env:
TELEGRAM_BOT_TOKEN=<your_bot_token>
TELEGRAM_CHAT_ID=<your_chat_id>
```

---

## Usage

### Paper mode (test without real money)
```bash
python paper_trade_loop.py
```
Logs trades to `paper_trades.csv`. Run until 30+ closed bets with positive ROI.

### Live mode (real money)
```bash
python live_trade_loop.py
```
Places real orders via Polymarket CLOB API. Logs to `live_trades.csv`.

---

## How it works

1. **Every 10 minutes:**
   - Check if current time is in 18-30h window before tomorrow
   - Fetch weather consensus from Open-Meteo for all 11 cities
   - If models agree (spread ≤ 3°C), scan Polymarket for temperature bins
   - Build 3-bin portfolio: center bin + one above + one below
   - Apply price filters (math edge, resolved bins, overpriced)
   - Log or place trades

2. **Deduplication:**
   - One bet per bin per event (city + target date)
   - Skips if already logged this bin

3. **ROI calculation:**
   - Win: stake × 14-20 (payout on YES at entry price)
   - Loss: -$2 (stake)
   - Tracks in CSV with status/PnL columns

---

## Files

| File | Purpose |
|------|---------|
| `config.py` | 11 cities with exact station coordinates |
| `forecast_consensus.py` | Open-Meteo 3-model fetching |
| `portfolio_builder.py` | 3-bin selection logic + filters |
| `market_scanner.py` | Polymarket bin discovery |
| `polymarket_client.py` | CLOB API wrapper |
| `trade_journal.py` | CSV-backed trade log |
| `telegram_notifier.py` | Alert sender |
| `paper_trade_loop.py` | Scan + log loop |
| `live_trade_loop.py` | Scan + order loop |

---

## Known issues

- Hong Kong systematically runs cold by ~1°C (apply bias correction in CITY_BIAS_C)
- Bin gaps on Fahrenheit markets (e.g., 57-58 gap) — fallback to nearest midpoint
- Tokyo coordinates verified for Haneda (RJTT), not central Tokyo

---

## References

- [Paruchh v3 guide](https://x.com/theparuchh/status/2052406323388490199) (the PDF)
- [Polymarket CLOB docs](https://docs.polymarket.com)
- [Open-Meteo API](https://open-meteo.com)
