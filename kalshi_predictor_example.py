"""
Kalshi WeatherPredictor - Full Workflow Example Script

This script demonstrates the complete WeatherPredictor pipeline for the 7 Kalshi cities:
1. Fetch real-time weather data from Open-Meteo API
2. Generate hybrid probability distributions for temperature buckets
3. Simulate market prices (for demonstration)
4. Run edge detection and generate trading recommendations
5. Print human-readable trading summary

Usage:
    python3 kalshi_predictor_example.py

⚠️  IMPORTANT: Market prices in this script are SIMULATED for demonstration.
Real trading requires live market prices from the Kalshi API orderbook.
Replace the simulated_prices logic with live Kalshi API calls for production use.
"""

import logging
import random
from typing import Optional, Dict, List
from datetime import datetime

from weather_aggregator import WeatherAggregator
from weather_predictor import (
    WeatherPredictor, PredictorConfig, MarketEdgeSummary,
    create_buckets_from_range
)
from config import CITIES_KALSHI
from weather_models import LocationWeatherData


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_city_weather(city_key: str, agg: WeatherAggregator) -> Optional[LocationWeatherData]:
    """
    Fetch weather data for a Kalshi city.

    Args:
        city_key: City key from CITIES_KALSHI (e.g., "NYC", "Chicago")
        agg: WeatherAggregator instance

    Returns:
        LocationWeatherData or None if fetch fails
    """
    try:
        city = CITIES_KALSHI[city_key]
        weather = agg.get_complete_weather_data(
            latitude=city['lat'],
            longitude=city['lon'],
            location_name=city['name'],
            forecast_days=3,
            station_code=city['station']
        )
        logger.info(f"✓ Fetched weather for {city['name']}")
        return weather
    except Exception as e:
        logger.warning(f"✗ Failed to fetch weather for {city_key}: {e}")
        return None


def generate_simulated_market_prices(model_probs: Dict[str, float]) -> Dict[str, float]:
    """
    Generate simulated market prices for demonstration.

    This is ONLY FOR TESTING. Real usage must fetch from Kalshi API.

    Strategy: model_probs * random factor (0.85-1.15) then normalize
    This creates some visible edge (models slightly better than market)

    Args:
        model_probs: Model probability distribution

    Returns:
        Dict of bucket label → simulated market-implied probability
    """
    # Apply random multipliers to create realistic price variance
    simulated = {label: max(0.01, prob * random.uniform(0.85, 1.15))
                 for label, prob in model_probs.items()}

    # Normalize to sum to 1.0
    total = sum(simulated.values())
    if total > 0:
        simulated = {label: p / total for label, p in simulated.items()}

    return simulated


def print_trading_summary(summary: MarketEdgeSummary, city_name: str) -> None:
    """
    Print a human-readable trading recommendation summary.

    Args:
        summary: MarketEdgeSummary from calculate_edge()
        city_name: Human-readable city name
    """
    print(f"\n📊 Trading Analysis for {city_name}")
    print(f"   Confidence: {summary.confidence_score:.1f}/100")
    print(f"   Recommended Exposure: {summary.recommended_exposure}")
    print(f"   Overall EV: {summary.overall_ev:+.4f}")
    print(f"   Risk Flags: {', '.join(summary.risk_flags) if summary.risk_flags else 'None'}")

    if summary.top_buckets:
        print(f"   Top Opportunities: {', '.join(summary.top_buckets)}")

    # Show bucket-by-bucket recommendations for BUY/STRONG_BUY
    buys = [be for be in summary.bucket_edges if be.recommendation in ["BUY", "STRONG_BUY"]]
    if buys:
        print(f"   Buy Signals ({len(buys)} buckets):")
        for be in sorted(buys, key=lambda x: x.conviction, reverse=True)[:3]:
            print(f"      {be.label}: edge={be.edge:+.3f}, conviction={be.conviction:.2f}, {be.recommendation}")
    else:
        print(f"   ⚠️  No buy signals (all edges too small or confidence too low)")


def main():
    """
    Main workflow: fetch weather, predict probabilities, detect edges, print recommendations.
    """
    print("\n" + "=" * 80)
    print("🌡️  Kalshi WeatherPredictor - Full Workflow Demo")
    print("=" * 80)

    # Step 1: Configure WeatherPredictor
    config = PredictorConfig(
        ensemble_weight=0.7,
        min_edge_threshold=0.10,
        temp_unit='F'
    )
    predictor = WeatherPredictor(config=config)
    logger.info(f"Initialized WeatherPredictor with config")

    # Step 2: Initialize WeatherAggregator
    agg = WeatherAggregator(cache_ttl_minutes=30)
    logger.info(f"Initialized WeatherAggregator")

    # Step 3: Define temperature buckets (Fahrenheit, summer range for illustration)
    # NOTE: Real usage should derive bucket range from the specific Kalshi market contract,
    #       which varies by city, season, and specific market (high/low/range).
    buckets = create_buckets_from_range(low=85, high=105, unit='F')
    logger.info(f"Created {len(buckets)} temperature buckets (85-105°F)")

    # Step 4: Process all 7 Kalshi cities
    print("\n" + "-" * 80)
    print("Processing Cities...")
    print("-" * 80)

    results_table = []

    for city_key in CITIES_KALSHI.keys():
        # Fetch weather
        weather = fetch_city_weather(city_key, agg)
        if weather is None:
            results_table.append({
                'city': city_key,
                'status': 'SKIPPED - no weather data'
            })
            continue

        city_name = CITIES_KALSHI[city_key]['name']
        station_id = CITIES_KALSHI[city_key]['station']

        try:
            # Generate model probabilities
            model_probs_dict = predictor.hybrid_bucket_probabilities(
                weather_data=weather,
                buckets=buckets,
                station_id=station_id
            )
            model_probs = {label: data['probability'] for label, data in model_probs_dict.items()}

            # Generate SIMULATED market prices (for demo only)
            # ⚠️  REPLACE THIS with real Kalshi API calls in production
            market_prices = generate_simulated_market_prices(model_probs)

            # Run edge detection
            summary = predictor.calculate_edge(
                model_probs=model_probs,
                market_prices=market_prices,
                buckets=buckets,
                station_id=station_id,
                weather_data=weather,
                min_edge=config.min_edge_threshold
            )

            # Print per-city summary
            print_trading_summary(summary, city_name)

            # Record for aggregate table
            results_table.append({
                'city': city_key,
                'name': city_name,
                'confidence': summary.confidence_score,
                'exposure': summary.recommended_exposure,
                'ev': summary.overall_ev,
                'top_bucket': summary.top_buckets[0] if summary.top_buckets else '-',
                'status': 'OK'
            })

        except Exception as e:
            logger.exception(f"Error processing {city_key}")
            results_table.append({
                'city': city_key,
                'status': f'ERROR: {str(e)[:40]}'
            })

    # Print aggregate summary table
    print("\n" + "=" * 80)
    print("📋 Summary Table")
    print("=" * 80)
    print(f"{'City':<15} {'Confidence':<15} {'Exposure':<15} {'EV':<12} {'Top Bucket':<12}")
    print("-" * 80)

    for result in results_table:
        if result['status'] != 'OK':
            print(f"{result.get('city', '?'):<15} {result['status']}")
        else:
            print(f"{result['name']:<15} {result['confidence']:>6.1f}/100     {result['exposure']:<15} {result['ev']:>+.4f}    {result['top_bucket']:<12}")

    print("=" * 80)
    print("\n✨ Demo complete!")
    print("\n⚠️  IMPORTANT REMINDERS:")
    print("  • Market prices in this demo are SIMULATED (random multipliers)")
    print("  • Production use requires LIVE Kalshi API orderbook prices")
    print("  • Replace the simulated_prices logic with Kalshi API calls")
    print("  • Test thoroughly with paper trading before live trading")
    print("  • Kalshi contracts may have different temperature ranges/precision per market")


if __name__ == "__main__":
    main()
