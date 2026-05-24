#!/usr/bin/env python3
"""Detailed market window analysis."""

import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from kalshi_api_client import KalshiAPIClient

load_dotenv()

api_key_id = os.getenv('KALSHI_API_KEY_ID')
private_key_path = os.getenv('KALSHI_PRIVATE_KEY_PATH')

with open(private_key_path, 'r') as f:
    private_key_pem = f.read()

client = KalshiAPIClient(api_key_id, private_key_pem)

now = datetime.now(timezone.utc)
print(f"\n{'='*120}")
print(f"DETAILED MARKET ANALYSIS - {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
print(f"{'='*120}\n")

series_patterns = {
    'NYC': 'KXHIGHNY',
    'Chicago': 'KXHIGHCHI',
    'Dallas': 'KXHIGHDFW',
    'Denver': 'KXHIGHDEN',
    'LA': 'KXHIGHLAX',
}

# Group markets by hour windows
windows = {
    '0-6h': [],
    '6-12h': [],
    '12-18h': [],
    '18-30h': [],
    '30-36h': [],
    '36h+': [],
}

all_markets = []

# Collect all markets
for city_name, series_ticker in series_patterns.items():
    try:
        markets = client.get_markets(status='open', series_ticker=series_ticker)
        all_markets.extend(markets)
    except Exception as e:
        print(f"Error fetching {city_name}: {e}")

print(f"TOTAL MARKETS DISCOVERED: {len(all_markets)}\n")

# Categorize by time window
for market in all_markets:
    ticker = market.get('ticker')
    close_time_str = market.get('close_time')

    if close_time_str:
        close_dt = datetime.fromisoformat(close_time_str.replace('Z', '+00:00'))
        hours = (close_dt - now).total_seconds() / 3600

        if hours < 6:
            windows['0-6h'].append((ticker, hours))
        elif hours < 12:
            windows['6-12h'].append((ticker, hours))
        elif hours < 18:
            windows['12-18h'].append((ticker, hours))
        elif hours < 30:
            windows['18-30h'].append((ticker, hours))
        elif hours < 36:
            windows['30-36h'].append((ticker, hours))
        else:
            windows['36h+'].append((ticker, hours))

# Print each window
for window_name in ['0-6h', '6-12h', '12-18h', '18-30h', '30-36h', '36h+']:
    markets_in_window = windows[window_name]

    print(f"{'='*120}")
    print(f"WINDOW: {window_name:<15} | Count: {len(markets_in_window):>2}")
    print(f"{'='*120}")

    if markets_in_window:
        markets_in_window.sort(key=lambda x: x[1])
        for ticker, hours in markets_in_window[:8]:
            print(f"  {ticker:<35} {hours:>6.1f}h")
        if len(markets_in_window) > 8:
            print(f"  ... and {len(markets_in_window) - 8} more")
    else:
        print("  (no markets in this window)")
    print()

# Summary
print(f"{'='*120}")
print(f"SUMMARY")
print(f"{'='*120}")
all_hours = []
for market in all_markets:
    close_time_str = market.get('close_time')
    if close_time_str:
        close_dt = datetime.fromisoformat(close_time_str.replace('Z', '+00:00'))
        hours = (close_dt - now).total_seconds() / 3600
        all_hours.append(hours)

print(f"  Total markets:               {len(all_markets):>3}")
print(f"  Min hours to resolution:     {min(all_hours):>6.1f}h")
print(f"  Max hours to resolution:     {max(all_hours):>6.1f}h")
print(f"\n  Current trading window (18-30h): {len(windows['18-30h']):>2} markets")
print(f"  Proposed window (12-30h):        {len(windows['12-18h']) + len(windows['18-30h']):>2} markets")
print(f"  Alternative window (6-18h):      {len(windows['6-12h']) + len(windows['12-18h']):>2} markets")

print(f"\n{'='*120}\n")
