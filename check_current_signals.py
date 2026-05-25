#!/usr/bin/env python3
"""Check what signals are being generated right now."""

import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from trading_engine import TradingEngine

load_dotenv()

engine = TradingEngine()

print(f"\n{'='*150}")
print(f"CURRENT SIGNAL GENERATION - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
print(f"{'='*150}\n")

# Scan markets
print("Scanning for tomorrow's markets...")
markets = engine.scan_markets()
print(f"Found {len(markets)} markets\n")

# Generate signals
print("Generating signals...\n")
signals = engine.generate_signals(markets)

print(f"{'='*150}")
print(f"SIGNALS GENERATED: {len(signals)}")
print(f"{'='*150}\n")

if signals:
    # Group by city
    by_city = {}
    for signal in signals:
        ticker = signal.market_ticker
        if 'NY' in ticker:
            city = 'NYC'
        elif 'CHI' in ticker:
            city = 'Chicago'
        elif 'DFW' in ticker:
            city = 'Dallas'
        elif 'DEN' in ticker:
            city = 'Denver'
        elif 'LAX' in ticker:
            city = 'LA'
        else:
            city = 'Unknown'

        if city not in by_city:
            by_city[city] = []
        by_city[city].append(signal)

    # Print by city
    for city in sorted(by_city.keys()):
        city_signals = by_city[city]
        print(f"{'-'*150}")
        print(f"{city.upper()}: {len(city_signals)} signals")
        print(f"{'-'*150}\n")

        for i, signal in enumerate(city_signals, 1):
            print(f"{i}. {signal.market_ticker}")
            print(f"   Buckets:    {signal.target_buckets}")
            print(f"   Edge:       {signal.edge_pct:.1f}%")
            print(f"   Confidence: {signal.confidence:.0f}%")
            print(f"   Notional:   ${signal.total_notional:.2f}")
            print(f"   Reasoning:  {signal.reasoning}")
            print()

    print(f"{'='*150}")
    print(f"SIGNAL SUMMARY")
    print(f"{'='*150}\n")

    # Sort by edge
    signals_sorted = sorted(signals, key=lambda s: s.edge_pct, reverse=True)

    print(f"TOP 5 SIGNALS BY EDGE:\n")
    for i, signal in enumerate(signals_sorted[:5], 1):
        print(f"{i}. {signal.market_ticker}")
        print(f"   Edge: {signal.edge_pct:.1f}% | Confidence: {signal.confidence:.0f}%\n")

    # Statistics
    edges = [s.edge_pct for s in signals]
    confidences = [s.confidence for s in signals]

    print(f"Statistics:")
    print(f"  Total signals: {len(signals)}")
    print(f"  Avg edge:      {sum(edges)/len(edges):.1f}%")
    print(f"  Min edge:      {min(edges):.1f}%")
    print(f"  Max edge:      {max(edges):.1f}%")
    print(f"  Avg confidence: {sum(confidences)/len(confidences):.1f}%")
    print(f"  Min confidence: {min(confidences):.1f}%")
    print(f"  Max confidence: {max(confidences):.1f}%")

else:
    print("❌ NO SIGNALS GENERATED")
    print("\nThis could mean:")
    print("  • No markets meet the minimum edge threshold (11%)")
    print("  • No markets meet the minimum confidence threshold (58%)")
    print("  • Weather data is not available")
    print("  • All market prices are too favorable (no edge)")

print(f"\n{'='*150}\n")
