# Polymarket Weather Trading Bots

This repository contains two independent weather trading bots for Polymarket.

---

## 📁 Folder Structure

```
Polymarket/
├── Weather_Predictor_1/          # Original Kalshi weather trading bot
│   ├── config.py
│   ├── signal_generator.py
│   ├── execution_service.py
│   ├── kalshi_api_client.py
│   ├── market_parser.py
│   ├── telegram_bot.py
│   ├── backtest_engine.py
│   ├── trading_engine.py
│   ├── weather_predictor.py
│   └── ... (28 files total)
│
├── Weather_Predictor_2/          # Parurchh v3 Polymarket bot (NEW)
│   ├── config.py
│   ├── forecast_consensus.py
│   ├── portfolio_builder.py
│   ├── market_scanner.py
│   ├── polymarket_client.py
│   ├── paper_trade_loop.py
│   ├── live_trade_loop.py
│   ├── telegram_notifier.py
│   ├── trade_journal.py
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
└── [Root docs & config files]
```

---

## 🤖 Bot Comparison

| Feature | Weather_Predictor_1 | Weather_Predictor_2 |
|---------|-------------------|-------------------|
| **Exchange** | Kalshi | Polymarket |
| **Strategy** | Multi-city ensemble forecasting | Parurchh v3 (3-model consensus) |
| **Weather Models** | GFS ensemble | ICON + GFS + ECMWF |
| **Entry Window** | Flexible (configurable) | 18-30 hours before resolution |
| **Portfolio** | Single best bin | 3 adjacent bins |
| **Status** | Established, being improved | New (v3, validated +45.9% ROI) |

---

## 🚀 Quick Start

### Weather_Predictor_2 (Parurchh v3 - Recommended for new trading)
```bash
cd Weather_Predictor_2
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with Polymarket credentials
python paper_trade_loop.py
```

### Weather_Predictor_1 (Original Kalshi bot)
```bash
cd Weather_Predictor_1
# Follow setup instructions in that folder
```

---

## 📊 Key Differences

### Weather_Predictor_1 (Kalshi)
- Established system with multiple trading strategies
- Integrated with Kalshi API
- Desktop dashboard support
- Risk management and backtesting built-in

### Weather_Predictor_2 (Polymarket v3)
- Clean implementation of Parurchh v3 strategy
- Lightweight and focused
- Three-model weather consensus
- Paper mode for safe testing
- Telegram alerts for trade notifications

---

## 🔧 Development

Each bot has its own:
- `config.py` — city coordinates, parameters
- `.env` file — credentials (gitignored)
- `requirements.txt` — Python dependencies
- Test suite for validation

To switch between bots, simply `cd` into the appropriate folder.

---

## 📈 Results

**Weather_Predictor_2 (Parurchh v3):**
- 3 days of v3: 17/30 wins (56.7%), +$43.15 PnL (+45.9% ROI)
- Win when correct: $14-20 payout
- Loss when wrong: -$2

**Weather_Predictor_1:**
- Active trading on Kalshi
- Continuous improvement and optimization
