#!/usr/bin/env python3
"""Debug test for single-bucket temperature matching strategy."""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from trading_engine import TradingEngine
from market_parser import parse_market_buckets
from weather_aggregator import WeatherAggregator
from weather_predictor import WeatherPredictor

load_dotenv()

print("=" * 100)
print("SINGLE BUCKET STRATEGY DEBUG TEST")
print("=" * 100)

engine = TradingEngine()

# Get markets
print("\n1. Scanning for markets...")
markets = engine.scan_markets()
print(f"   Found {len(markets)} markets")

if len(markets) == 0:
    print("   No markets available to test")
    sys.exit(0)

# Test with first market
test_market = markets[0]
ticker = test_market.get('ticker')
print(f"\n2. Testing with market: {ticker}")

# Parse buckets
parsed = parse_market_buckets(test_market)
if not parsed:
    print("   Failed to parse market")
    sys.exit(1)

buckets, station_id = parsed
print(f"   Station: {station_id}")
print(f"   Available buckets: {[b.label for b in buckets]}")

# Get weather for this station
from market_parser import CITIES_KALSHI, get_city_for_station
city_name = get_city_for_station(station_id)
city_config = CITIES_KALSHI.get(city_name or '')

if not city_config:
    print(f"   Unknown city for station {station_id}")
    sys.exit(1)

print(f"   City: {city_name}")

# Fetch weather
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
    print("   No weather data available")
    sys.exit(1)

daily = weather.daily_forecast[0]
predicted_temp_f = daily.temperature_max
print(f"   Predicted max temperature: {predicted_temp_f:.1f}°F")

# Check which bucket contains this temperature
print(f"\n4. Finding bucket for {predicted_temp_f:.1f}°F...")
matching_bucket = None
for bucket in buckets:
    print(f"   Checking {bucket.label} ({bucket.low:.1f} - {bucket.high:.1f}°F)...", end=" ")
    if bucket.contains(predicted_temp_f):
        print("✓ MATCH")
        matching_bucket = bucket
    else:
        print("✗")

if matching_bucket:
    print(f"\n   ✓ Found matching bucket: {matching_bucket.label}")
else:
    print(f"\n   ❌ No bucket contains {predicted_temp_f:.1f}°F")
    print(f"   Bucket range: {buckets[0].low:.1f}°F to {buckets[-1].high:.1f}°F")

# Generate signal
print(f"\n5. Generating signal...")
signals = engine.generate_signals([test_market])
print(f"   Generated {len(signals)} signal(s)")

if signals:
    signal = signals[0]
    print(f"   ✓ Signal: {signal.market_ticker}")
    print(f"     Buckets: {signal.target_buckets}")
    print(f"     Edge: {signal.edge_pct:.1f}%")
    print(f"     Confidence: {signal.confidence:.0f}%")
else:
    print(f"   ❌ No signal generated")

print("\n" + "=" * 100)
