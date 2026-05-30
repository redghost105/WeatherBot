#!/usr/bin/env python3
"""Test which markets are available in different time windows."""

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
print(f"MARKET WINDOW TEST - Current time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
print(f"{'='*120}\n")

series_patterns = {
    'NYC': 'KXHIGHNY',
    'Chicago': 'KXHIGHCHI',
    'Dallas': 'KXHIGHDFW',
    'Denver': 'KXHIGHDEN',
    'LA': 'KXHIGHLAX',
}

all_markets = []
window_18_30 = []
window_12_30 = []

# Collect all markets
for city_name, series_ticker in series_patterns.items():
    try:
        markets = client.get_markets(status='open', series_ticker=series_ticker)
        all_markets.extend(markets)
    except Exception as e:
        print(f"Error fetching {city_name}: {e}")

print(f"TOTAL MARKETS FOUND: {len(all_markets)}\n")

# Categorize by time window
for market in all_markets:
    ticker = market.get('ticker')
    close_time_str = market.get('close_time')

    if close_time_str:
        close_dt = datetime.fromisoformat(close_time_str.replace('Z', '+00:00'))
        hours = (close_dt - now).total_seconds() / 3600

        if 18 <= hours <= 30:
            window_18_30.append((ticker, hours))

        if 12 <= hours <= 30:
            window_12_30.append((ticker, hours))

# Print results
print(f"{'='*120}")
print(f"MARKETS IN 18-30 HOUR WINDOW: {len(window_18_30)}")
print(f"{'='*120}")
if window_18_30:
    window_18_30.sort(key=lambda x: x[1])
    for ticker, hours in window_18_30[:15]:
        print(f"  {ticker:<35} {hours:>6.1f}h")
    if len(window_18_30) > 15:
        print(f"  ... and {len(window_18_30) - 15} more")
else:
    print("  ⚠️  No markets found in this window")

print(f"\n{'='*120}")
print(f"MARKETS IN 12-30 HOUR WINDOW: {len(window_12_30)}")
print(f"{'='*120}")
if window_12_30:
    window_12_30.sort(key=lambda x: x[1])
    for ticker, hours in window_12_30[:15]:
        print(f"  {ticker:<35} {hours:>6.1f}h")
    if len(window_12_30) > 15:
        print(f"  ... and {len(window_12_30) - 15} more")
else:
    print("  ⚠️  No markets found in this window")

# Summary statistics
if all_markets:
    all_hours = []
    for market in all_markets:
        close_time_str = market.get('close_time')
        if close_time_str:
            close_dt = datetime.fromisoformat(close_time_str.replace('Z', '+00:00'))
            hours = (close_dt - now).total_seconds() / 3600
            all_hours.append(hours)

    print(f"\n{'='*120}")
    print(f"TIME RANGE SUMMARY")
    print(f"{'='*120}")
    print(f"  Min hours to resolution: {min(all_hours):>6.1f}h")
    print(f"  Max hours to resolution: {max(all_hours):>6.1f}h")
    print(f"  Markets in 18-30h:       {len(window_18_30):>6} ({100*len(window_18_30)/len(all_markets):.1f}%)")
    print(f"  Markets in 12-30h:       {len(window_12_30):>6} ({100*len(window_12_30)/len(all_markets):.1f}%)")

print(f"\n{'='*120}\n")
