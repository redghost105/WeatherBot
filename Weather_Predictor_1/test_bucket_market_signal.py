#!/usr/bin/env python3
"""Debug test for bucket market signal generation."""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from trading_engine import TradingEngine

load_dotenv()

print("=" * 100)
print("BUCKET MARKET SIGNAL DEBUG TEST")
print("=" * 100)

engine = TradingEngine()

# Get markets
print("\n1. Scanning for markets...")
markets = engine.scan_markets()
print(f"   Found {len(markets)} total markets")

# Filter for bucket markets only
bucket_markets = [m for m in markets if '-B' in m.get('ticker', '')]
print(f"   Bucket markets: {len(bucket_markets)}")

if len(bucket_markets) == 0:
    print("   No bucket markets available")
    sys.exit(0)

# Show first few bucket markets
print(f"\n2. Available bucket markets:")
for m in bucket_markets[:5]:
    ticker = m.get('ticker')
    title = m.get('title', '')[:60]
    print(f"   • {ticker}: {title}")

# Test with first bucket market
test_market = bucket_markets[0]
ticker = test_market.get('ticker')
print(f"\n3. Testing signal generation with: {ticker}")

# Generate signals
signals = engine.generate_signals([test_market])
print(f"   Generated {len(signals)} signal(s)")

if signals:
    signal = signals[0]
    print(f"\n   ✓ SIGNAL GENERATED:")
    print(f"     Ticker: {signal.market_ticker}")
    print(f"     Buckets: {signal.target_buckets}")
    print(f"     Edge: {signal.edge_pct:.1f}%")
    print(f"     Confidence: {signal.confidence:.0f}%")
    print(f"     Notional: ${signal.total_notional:.2f}")
    print(f"     Reasoning: {signal.reasoning}")
else:
    print(f"\n   ❌ NO SIGNAL GENERATED")
    print(f"      This could mean:")
    print(f"      • Edge below 11% threshold")
    print(f"      • Confidence below 58% threshold")
    print(f"      • Predicted temperature not in any bucket")

print("\n" + "=" * 100)
