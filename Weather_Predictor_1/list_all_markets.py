#!/usr/bin/env python3
"""List all tomorrow's markets discovered by the trading system."""

import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from trading_engine import TradingEngine

load_dotenv()

engine = TradingEngine()

print(f"\n{'='*150}")
print(f"ALL MARKETS DISCOVERED - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
print(f"{'='*150}\n")

# Scan markets
markets = engine.scan_markets()

print(f"TOTAL MARKETS FOUND: {len(markets)}\n")

# Group by city
cities = {}
for market in markets:
    ticker = market.get('ticker', '')
    # Extract city from ticker (e.g., KXHIGHNY -> NYC)
    if 'NY' in ticker:
        city = 'NYC'
    elif 'CHI' in ticker or 'KXHIGHCHI' in ticker:
        city = 'Chicago'
    elif 'DFW' in ticker:
        city = 'Dallas'
    elif 'DEN' in ticker:
        city = 'Denver'
    elif 'LAX' in ticker or 'KXHIGHLAX' in ticker:
        city = 'LA'
    else:
        city = 'Unknown'

    if city not in cities:
        cities[city] = []
    cities[city].append(market)

# Print by city
for city in sorted(cities.keys()):
    city_markets = cities[city]
    print(f"\n{'-'*150}")
    print(f"{city.upper()}: {len(city_markets)} markets")
    print(f"{'-'*150}")

    for i, market in enumerate(city_markets, 1):
        ticker = market.get('ticker', 'N/A')
        title = market.get('title', 'N/A')[:80]
        close_time = market.get('close_time', 'N/A')
        hours = market.get('hours_to_resolution', 'N/A')

        if isinstance(hours, float):
            hours_str = f"{hours:>6.1f}h"
        else:
            hours_str = str(hours)

        print(f"\n{i:>2}. {ticker}")
        print(f"    Title:  {title}")
        print(f"    Close:  {close_time}")
        print(f"    Hours:  {hours_str}")

print(f"\n{'='*150}")
print(f"SUMMARY BY CITY")
print(f"{'='*150}\n")

for city in sorted(cities.keys()):
    print(f"  {city:<12} {len(cities[city]):>3} markets")

print(f"\n  {'TOTAL':<12} {len(markets):>3} markets")

# Calculate hours range
if markets:
    hours_list = []
    for market in markets:
        hours = market.get('hours_to_resolution')
        if isinstance(hours, (int, float)):
            hours_list.append(hours)

    if hours_list:
        print(f"\n  Hours range: {min(hours_list):.1f}h to {max(hours_list):.1f}h")

print(f"\n{'='*150}\n")
