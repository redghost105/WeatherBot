#!/usr/bin/env python3
"""Detailed debug test for bucket market signal generation."""

import os
import sys
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from trading_engine import TradingEngine
from market_parser import parse_market_buckets, CITIES_KALSHI, get_city_for_station
from weather_aggregator import WeatherAggregator

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

load_dotenv()

print("=" * 100)
print("DETAILED BUCKET MARKET DEBUG TEST")
print("=" * 100)

engine = TradingEngine()

# Get markets
print("\n1. Scanning for bucket markets...")
markets = engine.scan_markets()
bucket_markets = [m for m in markets if '-B' in m.get('ticker', '')]
print(f"   Found {len(bucket_markets)} bucket markets")

if not bucket_markets:
    print("   No bucket markets")
    sys.exit(0)

# Test with first bucket market
test_market = bucket_markets[0]
ticker = test_market.get('ticker')
title = test_market.get('title')
print(f"\n2. Testing market: {ticker}")
print(f"   Title: {title}")

# Parse buckets
parsed = parse_market_buckets(test_market)
if not parsed:
    print("   ERROR: Failed to parse market buckets")
    sys.exit(1)

buckets, station_id = parsed
city_name = get_city_for_station(station_id)
city_config = CITIES_KALSHI.get(city_name or '')

print(f"   Station: {station_id}")
print(f"   City: {city_name}")
print(f"   Buckets parsed: {[b.label for b in buckets]}")

# Get weather
print(f"\n3. Fetching weather data...")
agg = WeatherAggregator(cache_ttl_minutes=0)
weather = agg.get_complete_weather_data(
    latitude=city_config['lat'],
    longitude=city_config['lon'],
    location_name=city_name,
    forecast_days=1,
    station_code=station_id
)

if not weather or not weather.daily_forecast:
    print("   ERROR: No weather data")
    sys.exit(1)

daily = weather.daily_forecast[0]
predicted_temp_f = daily.temperature_max
print(f"   Predicted max temp: {predicted_temp_f:.1f}°F")

# Find matching bucket
print(f"\n4. Finding bucket that contains {predicted_temp_f:.1f}°F...")
matching_bucket = None
for bucket in buckets:
    contains = bucket.contains(predicted_temp_f)
    print(f"   {bucket.label} ({bucket.low:.1f}-{bucket.high:.1f}): {contains}")
    if contains:
        matching_bucket = bucket

if matching_bucket:
    print(f"   ✓ Match: {matching_bucket.label}")
else:
    print(f"   ❌ No match found!")
    print(f"   Available range: {buckets[0].low}°F to {buckets[-1].high}°F")

# Try to generate signal
print(f"\n5. Attempting signal generation...")
signals = engine.generate_signals([test_market])
print(f"   Signals generated: {len(signals)}")

if signals:
    signal = signals[0]
    print(f"\n   ✓ SIGNAL:")
    print(f"     Ticker: {signal.market_ticker}")
    print(f"     Buckets: {signal.target_buckets}")
    print(f"     Edge: {signal.edge_pct:.1f}%")
    print(f"     Confidence: {signal.confidence:.0f}%")
else:
    print(f"\n   ❌ No signal")

print("\n" + "=" * 100)
