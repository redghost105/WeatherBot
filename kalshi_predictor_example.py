"""
WeatherPredictor Example Script - Full Workflow Demonstration

This script demonstrates the complete WeatherPredictor workflow for trading weather markets:
1. Fetch weather data for 7 major US cities from WeatherAggregator
2. Create temperature buckets matching typical market structures
3. Generate probability distributions using the hybrid method
4. Detect trading edges by comparing model vs. market prices
5. Output trading recommendations with confidence metrics

IMPORTANT: Market prices in this example are SIMULATED for demonstration.
For real trading, integrate actual Kalshi API orderbook prices via KalshiAPIClient.

Usage:
    python3 kalshi_predictor_example.py
"""

import logging
import json
import random
from datetime import datetime, timezone
from typing import Dict, Optional
from dataclasses import asdict

from weather_predictor import (
    WeatherPredictor,
    PredictorConfig,
    create_buckets_from_range,
    HistoricalBiasLearner
)
from weather_aggregator import WeatherAggregator
from weather_models import LocationWeatherData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Seven major US cities for trading
CITIES_KALSHI = [
    {"name": "New York", "lat": 40.77, "lon": -73.97, "code": "KNYC", "abbr": "NYC"},
    {"name": "Los Angeles", "lat": 34.05, "lon": -118.24, "code": "KLAX", "abbr": "LAX"},
    {"name": "Chicago", "lat": 41.88, "lon": -87.63, "code": "KMDW", "abbr": "ORD"},
    {"name": "Dallas", "lat": 32.90, "lon": -97.04, "code": "KDFW", "abbr": "DFW"},
    {"name": "Houston", "lat": 29.76, "lon": -95.37, "code": "KIAH", "abbr": "IAH"},
    {"name": "Atlanta", "lat": 33.64, "lon": -84.43, "code": "KATL", "abbr": "ATL"},
    {"name": "Phoenix", "lat": 33.44, "lon": -112.07, "code": "KPHX", "abbr": "PHX"},
]


def setup_logging() -> None:
    """Configure structured logging for audit trail."""
    # Already configured in module-level basicConfig
    logger.info("=" * 80)
    logger.info("WeatherPredictor Example - Full Workflow")
    logger.info(f"Start time: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 80)


def fetch_city_weather(
    city: Dict,
    agg: WeatherAggregator
) -> Optional[LocationWeatherData]:
    """
    Fetch weather data for a single city.

    Args:
        city: City dict with name, lat, lon, code
        agg: WeatherAggregator instance

    Returns:
        LocationWeatherData or None if fetch fails
    """
    try:
        logger.info(f"Fetching weather for {city['name']} ({city['code']})...")
        weather = agg.get_complete_weather_data(
            latitude=city['lat'],
            longitude=city['lon'],
            location_name=city['name'],
            forecast_days=3,
            station_code=city['code']
        )

        if weather:
            logger.info(f"✓ {city['name']}: {len(weather.ensemble_forecast)} ensemble members, "
                       f"{len(weather.daily_forecast)} daily forecasts")
            return weather
        else:
            logger.warning(f"✗ {city['name']}: No weather data returned")
            return None

    except Exception as e:
        logger.warning(f"✗ {city['name']}: Failed to fetch weather: {e}")
        return None


def generate_simulated_prices(
    model_probs: Dict[str, float]
) -> Dict[str, float]:
    """
    Generate SIMULATED market prices for demonstration.

    WARNING: These are NOT real Kalshi prices. Real trading requires
    actual orderbook data from KalshiAPIClient.

    Simulation logic:
    - Start with model probability
    - Apply random 15% mispricing (±15%)
    - Clamp to [0.01, 0.99]
    - Normalize so all prices sum to 1.0

    Args:
        model_probs: Dict of bucket_label -> probability

    Returns:
        Dict of simulated market prices
    """
    prices = {}
    for label, prob in model_probs.items():
        # Add random mispricing: ±15%
        noise = random.uniform(0.85, 1.15)
        simulated = prob * noise
        # Clamp to reasonable bounds
        prices[label] = max(0.01, min(0.99, simulated))

    # Normalize so they sum to ~1.0 (market constraint)
    total = sum(prices.values())
    if total > 0:
        prices = {k: v / total for k, v in prices.items()}

    return prices


def print_trading_summary(
    city_name: str,
    station_id: str,
    summary: Dict
) -> None:
    """
    Pretty-print the trading edge summary for one city.

    Args:
        city_name: Human-readable city name
        station_id: Station code (e.g., "KNYC")
        summary: MarketEdgeSummary dataclass (converted to dict)
    """
    logger.info("")
    logger.info(f"{'='*80}")
    logger.info(f"TRADING SUMMARY: {city_name} ({station_id})")
    logger.info(f"{'='*80}")

    logger.info(f"Confidence: {summary['confidence_score']:.0f}/100")
    logger.info(f"Overall EV: ${summary['overall_ev']:.3f}")
    logger.info(f"Recommended Exposure: {summary['recommended_exposure']}")

    if summary['top_buckets']:
        logger.info(f"Top Buckets: {', '.join(summary['top_buckets'])}")

    if summary['risk_flags']:
        logger.info(f"⚠️  Risk Flags: {', '.join(summary['risk_flags'])}")

    logger.info(f"Reasoning: {summary['reasoning']}")

    # Bucket details
    logger.info("\nBucket Analysis:")
    logger.info(f"{'Bucket':<12} {'Model %':<10} {'Market %':<10} {'Edge':<8} {'Action':<15}")
    logger.info("-" * 55)

    for edge in summary['bucket_edges']:
        model_pct = edge['model_prob'] * 100
        market_pct = edge['market_prob'] * 100
        edge_val = edge['edge']
        recommendation = edge['recommendation']

        logger.info(f"{edge['label']:<12} {model_pct:>8.1f}% {market_pct:>8.1f}% "
                   f"{edge_val:>7.3f}  {recommendation:<15}")


def run_city_analysis(
    city: Dict,
    weather: LocationWeatherData,
    predictor: WeatherPredictor,
    buckets: list
) -> Optional[Dict]:
    """
    Run complete analysis for one city.

    Args:
        city: City dict
        weather: LocationWeatherData from WeatherAggregator
        predictor: WeatherPredictor instance
        buckets: List of Bucket objects

    Returns:
        Analysis summary dict or None on failure
    """
    try:
        # Generate probabilities
        logger.debug(f"Generating hybrid probabilities for {city['name']}...")
        model_probs_dict = predictor.hybrid_bucket_probabilities(
            weather, buckets, city['code']
        )

        if not model_probs_dict:
            logger.warning(f"No probabilities generated for {city['name']}")
            return None

        # Extract probabilities
        model_probs = {label: d['probability'] for label, d in model_probs_dict.items()}

        # Generate SIMULATED market prices (WARNING: Not real prices)
        logger.debug(f"Generating simulated market prices for {city['name']}...")
        market_prices = generate_simulated_prices(model_probs)

        # Calculate edge
        logger.debug(f"Calculating trading edges for {city['name']}...")
        summary = predictor.calculate_edge(
            model_probs=model_probs,
            market_prices=market_prices,
            buckets=buckets,
            station_id=city['code'],
            weather_data=weather,
            min_edge=0.10
        )

        return {
            'city': city['name'],
            'station_id': city['code'],
            'confidence': summary.confidence_score,
            'ev': summary.overall_ev,
            'exposure': summary.recommended_exposure,
            'top_bucket': summary.top_buckets[0] if summary.top_buckets else None,
            'summary': summary
        }

    except Exception as e:
        logger.error(f"Analysis failed for {city['name']}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main() -> int:
    """
    Main orchestration: Analyze all 7 cities.

    Returns:
        0 on success, 1 on error
    """
    try:
        setup_logging()

        # Step 1: Configure predictor
        logger.info("\n[1/5] Configuring WeatherPredictor...")
        config = PredictorConfig(
            ensemble_weight=0.7,
            min_edge_threshold=0.10,
            temp_unit='F'
        )
        predictor = WeatherPredictor(config=config)
        logger.info("✓ Predictor configured")

        # Step 2: Initialize WeatherAggregator
        logger.info("\n[2/5] Initializing WeatherAggregator...")
        agg = WeatherAggregator(cache_ttl_minutes=30)
        logger.info("✓ WeatherAggregator ready")

        # Step 3: Create temperature buckets
        # Illustrative summer temperature range (typical for US markets)
        logger.info("\n[3/5] Creating temperature buckets...")
        buckets = create_buckets_from_range(low=85, high=105, unit='F', step=1.0)
        logger.info(f"✓ Created {len(buckets)} buckets: {buckets[0].label} to {buckets[-1].label}")

        # Step 4: Analyze each city
        logger.info("\n[4/5] Analyzing all 7 cities...")
        results = []
        for city in CITIES_KALSHI:
            weather = fetch_city_weather(city, agg)
            if not weather:
                continue

            analysis = run_city_analysis(city, weather, predictor, buckets)
            if analysis:
                results.append(analysis)
                print_trading_summary(analysis['city'], analysis['station_id'],
                                    asdict(analysis['summary']))

        # Step 5: Summary table
        logger.info("\n[5/5] Summary Table")
        logger.info("=" * 80)
        logger.info(f"{'City':<15} {'Confidence':<12} {'EV':<10} {'Exposure':<10} {'Top Bucket':<12}")
        logger.info("-" * 80)

        for r in results:
            ev_str = f"${r['ev']:.3f}"
            confidence_str = f"{r['confidence']:.0f}/100"
            top_bucket = r['top_bucket'] or "—"
            logger.info(f"{r['city']:<15} {confidence_str:<12} {ev_str:<10} "
                       f"{r['exposure']:<10} {top_bucket:<12}")

        logger.info("=" * 80)
        logger.info(f"\n✓ Analysis complete: {len(results)}/{len(CITIES_KALSHI)} cities analyzed")
        logger.info(f"End time: {datetime.now(timezone.utc).isoformat()}\n")

        return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
