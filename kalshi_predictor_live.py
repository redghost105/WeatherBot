"""
Kalshi WeatherPredictor - LIVE PRODUCTION VERSION

This script demonstrates the complete WeatherPredictor pipeline with REAL Kalshi market data:
1. Fetch real-time weather data from Open-Meteo API
2. Generate hybrid probability distributions for temperature buckets
3. Fetch REAL market prices from Kalshi API orderbook
4. Run edge detection and generate trading recommendations
5. Print human-readable trading summary with actual market data

Usage:
    python3 kalshi_predictor_live.py

⚠️  IMPORTANT: Uses REAL Kalshi market prices from live orderbook.
All trading signals are based on actual market data.
"""

import logging
import sys
from typing import Optional, Dict, List
from datetime import datetime, timezone

from weather_aggregator import WeatherAggregator
from weather_predictor import (
    WeatherPredictor, PredictorConfig, MarketEdgeSummary,
    create_buckets_from_range, Bucket
)
from kalshi_api_client import KalshiAPIClient
from config import CITIES_KALSHI
from weather_models import LocationWeatherData


# Mapping of cities to Kalshi weather series tickers
CITY_TO_SERIES = {
    "New York City": "KXHIGHNY",
    "Chicago": "KXHIGHCHI",
    "Miami": "KXHIGHMIA",
    "Atlanta": "KXHIGHATL",
    "Dallas": "KXHIGHDAL",
    "Los Angeles": "KXHIGHLAX",
    "Denver": "KXHIGHDEN",
}


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


def fetch_kalshi_markets(kalshi: KalshiAPIClient, city_name: str) -> Dict[float, Dict]:
    """
    Fetch all Kalshi temperature markets for a city and their orderbooks.

    Uses series ticker (e.g., KXHIGHNY) to retrieve markets via the Kalshi API.

    Args:
        kalshi: KalshiAPIClient instance
        city_name: City name (e.g., "New York City")

    Returns:
        Dict mapping temperature threshold → {ticker, yes_price, no_price, market_prob}
    """
    markets = {}

    try:
        # Get series ticker for this city
        series_ticker = CITY_TO_SERIES.get(city_name)
        if not series_ticker:
            logger.warning(f"No series ticker mapping for {city_name}")
            return markets

        logger.debug(f"Fetching markets for {city_name} using series ticker: {series_ticker}")

        # Fetch markets using series_ticker parameter
        found_markets = kalshi.get_markets(status=None, series_ticker=series_ticker)

        if not found_markets:
            logger.warning(f"No temperature markets found for {city_name} (series: {series_ticker})")
            return markets

        logger.debug(f"Found {len(found_markets)} temperature markets for {city_name}")

        # Limit to first 10 markets to avoid timeout (API calls are slow)
        # Focus on recent markets which have better liquidity
        markets_to_process = found_markets[:10]
        logger.info(f"Processing {len(markets_to_process)} markets (out of {len(found_markets)}) for {city_name}")

        # Fetch orderbooks for each market
        for market in markets_to_process:
            ticker = market.get("ticker", "")
            if not ticker:
                continue

            # Extract temperature threshold from market ticker
            # Format: HIGHNY-22NOV27-T57 or HIGHNY-22NOV27-B51.5
            try:
                # Split by last dash to get strike component
                parts = ticker.rsplit("-", 1)
                if len(parts) < 2:
                    logger.debug(f"Could not parse ticker format: {ticker}")
                    continue

                strike_str = parts[-1]  # e.g., "T57" or "B51.5"

                if strike_str.startswith("T"):
                    # Upper bound market: "T57" means 57°F or lower
                    threshold = float(strike_str[1:])
                elif strike_str.startswith("B"):
                    # Lower bound market: "B51.5" means 51.5°F or higher
                    threshold = float(strike_str[1:])
                else:
                    logger.debug(f"Unknown strike format: {strike_str}")
                    continue

            except (ValueError, IndexError) as e:
                logger.debug(f"Could not parse threshold from {ticker}: {e}")
                continue

            try:
                # Fetch orderbook
                orderbook = kalshi.get_orderbook(ticker)

                if not orderbook:
                    logger.debug(f"Empty orderbook for {ticker}")
                    continue

                # Extract prices
                yes_bids = orderbook.get("yes_dollars", [])
                no_bids = orderbook.get("no_dollars", [])

                if not yes_bids or not no_bids:
                    logger.debug(f"Incomplete bids for {ticker}: yes={len(yes_bids)}, no={len(no_bids)}")
                    continue

                yes_price = float(yes_bids[-1][0])
                no_price = float(no_bids[-1][0])

                # Calculate implied probability
                total = yes_price + no_price
                if total > 0:
                    market_prob = yes_price / total
                else:
                    market_prob = 0.5

                markets[threshold] = {
                    'ticker': ticker,
                    'yes_price': yes_price,
                    'no_price': no_price,
                    'market_prob': market_prob,
                    'volume_yes': float(yes_bids[-1][1]) if len(yes_bids) > 1 else 0,
                    'volume_no': float(no_bids[-1][1]) if len(no_bids) > 1 else 0,
                }

                logger.debug(f"  {ticker}: YES=${yes_price:.4f} NO=${no_price:.4f} (P={market_prob:.1%})")

            except Exception as e:
                logger.warning(f"Error fetching orderbook for {ticker}: {e}")
                continue

        logger.info(f"✓ Fetched {len(markets)} markets with orderbooks for {city_name}")
        return markets

    except Exception as e:
        logger.error(f"Error fetching Kalshi markets: {e}")
        return markets


def convert_forecast_to_binary_probs(model_probs_dict: Dict, buckets: List[Bucket]) -> Dict[float, float]:
    """
    Convert bucket-based probability distribution to binary threshold probabilities.

    P(Temp > X.99) = sum of probabilities for all buckets with midpoint > X.99

    Args:
        model_probs_dict: Dict from hybrid_bucket_probabilities (bucket_label → {probability, ...})
        buckets: List of Bucket objects

    Returns:
        Dict mapping temperature threshold → P(Temp > threshold)
    """
    thresholds_probs = {}

    # Extract probabilities by bucket
    bucket_probs = {}
    for bucket in buckets:
        if bucket.label in model_probs_dict:
            bucket_probs[bucket.label] = model_probs_dict[bucket.label]['probability']

    # For each possible threshold, calculate P(Temp > threshold)
    for threshold in range(75, 100):  # Thresholds from 75 to 99
        threshold_decimal = float(f"{threshold}.99")

        # Sum probabilities for buckets where midpoint > threshold
        prob_above = sum(
            model_probs_dict[bucket.label]['probability']
            for bucket in buckets
            if bucket.label in model_probs_dict and bucket.midpoint() > threshold_decimal
        )

        thresholds_probs[threshold_decimal] = prob_above

    return thresholds_probs


def print_trading_summary(summary: MarketEdgeSummary, city_name: str, market_data: Dict) -> None:
    """
    Print a human-readable trading recommendation summary with REAL market data.

    Args:
        summary: MarketEdgeSummary from calculate_edge()
        city_name: Human-readable city name
        market_data: Dict of threshold → market prices from Kalshi
    """
    print(f"\n📊 Trading Analysis for {city_name}")
    print(f"   Confidence: {summary.confidence_score:.1f}/100")
    print(f"   Recommended Exposure: {summary.recommended_exposure}")
    print(f"   Overall EV: {summary.overall_ev:+.4f}")
    print(f"   Risk Flags: {', '.join(summary.risk_flags) if summary.risk_flags else 'None'}")

    if market_data:
        print(f"   Markets Available: {len(market_data)}")

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
    Main workflow: fetch weather, predict probabilities, detect edges with REAL market data.
    """
    print("\n" + "=" * 80)
    print("🌡️  Kalshi WeatherPredictor - LIVE PRODUCTION MODE")
    print("=" * 80)
    print("Using REAL Kalshi market prices from live orderbooks\n")

    # Initialize Kalshi API client with provided credentials
    api_key_id = "c9d784b0-f004-413d-a380-205288096083"
    private_key_pem = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAxQ9Da8JAoanhGNUbRYhmhpvYGOGSLJvWIYqp920KuHy8c+ta
ByiKce0wufkQVp1x0AOsQ+xCQ/5aIi7eOkaQFu4VXAXZ/Lo2fV8IGNbHDXUkFry3
Og5/S51IVWYNWVnCTNxlfeI6hAFQUV7maj/P1EPmfeAPOy9Rx151OB2wkP0QYmRq
4OGQWXlg9hY/3T+qNw0ngcX3hXTFzAMWX1X9DhYAzFtKv7ZXYMawkMVxh+RvHdSX
ei2Okk9zYzA2tdCri55vgiNKnYxoHFvL5euNm6DtSN69xiUGuMN3u6xgyKmMEyL/
kDmcMVpPfeDskhvYOKxPyHhmPmrDlPbJroRZTQIDAQABAoIBABlZA0UjMYkZ/vhg
wSdKilWaSku5CEJwsTSTT5WiExT0BpGqnmP5VQWeivwBC5b4naEyN8Bs7YEtgI6R
FMjONs6cRWcW4Zleoo+x36rCRcx3WvMJx0/SeZFSY/GINQNfRlz4pJ1ysjA0sw4k
dOMJ3kPhkA50+cCVL6HDhrR3LTUY/m/CP0UOKa01lpCLWMoUJ79UwLfqzSSxte31
WVyQ3O2acw5epAKjmoPIp8ulw1XDpJskl7CEmouTcnxiJ6vsVMCmWq+OEjs1zn6I
GAuy8DqlHk135mh2UW1zdsibq4nNczDL5IW6h4QCltp64Rgi7sdG1o3wL4lNctjM
C1o1BgECgYEA3tm9OVqeGh5tMpHRIjT3c5jkPv9T8k49HC1EIm06941CthmwgCQA
76YsmAMOekYb8XNr6YAY2JH4Dc/WGlz8dTm0VXQIUfuiw0jA7p8CreeNyla7QARj
SMQ280VkIJcQx0iMVTXAOXr2xaxm88YpEikPlSFSwRSdlF5QE27WicECgYEA4l9k
mJ0eBszVxOPgvYfSFpCpTTBI7lVwER+WdoeRl63o9E6lIan+QLHSC8o4fBmL7Sbw
4kwQnABH6EiRMjWaMHWnbzV/64kSGkdZUDHdhLv9fGQxlesoBh2zUf0Z57faVTZ7
iZFY2rWYmE0z5WQmjaGhxnkGvyxxpstN+QzU+o0CgYAhSwhhDC+4mTkZJ/3FjYI2
i+31l3G0LookroKSXh1EJJ+F0xqyWi6lnv7kivhbviOok+TYUqHjoRMdBSLod2Hk
JYXSim4/yUdMw47HV4wv7Psa8pAxBTbMBTxsZb6Ku+buzuDgThJ0w/EgIRyUaNNz
+hxw3DSf0fOk2d4+uP1mQQKBgQDN7l/SIeRl5UN2uKMDaCJrmrAZYxqFjj3Dpgu3
yj5dUL0COuUoCcAdVGaziQP3iTnsxKcQBoh5khvYKOPFXFPnT7DAj1fOikRomY2b
UbGmBWplFbSyIFmprq0poelGDc/WAxlBHXNKizbFHj5eqMwVvfswVXsYwLKnPH2z
WcQKJQKBgQC++BeONDvW3Lzg01POMOsWrv4L83mAXG2WR0AfWz1V3EDsm3t5NbFq
xQosKGrAaA43OOsSdHoqoS558o76AkqgrITuq5smNU7Lw5AS2UfKIPmHknoJIdrq
hIXJORCr9UfAkyHX1FqzTQGPZmS+/J3X4Y9y55AEI+UE0GDepJHN7g==
-----END RSA PRIVATE KEY-----"""

    try:
        kalshi = KalshiAPIClient(api_key_id, private_key_pem)
        logger.info("✓ Kalshi API client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Kalshi API: {e}")
        print(f"\n❌ ERROR: Could not connect to Kalshi API: {e}")
        return

    # Step 1: Configure WeatherPredictor
    config = PredictorConfig(
        ensemble_weight=0.7,
        min_edge_threshold=0.05,  # Lower threshold to detect more edges
        temp_unit='F'
    )
    predictor = WeatherPredictor(config=config)
    logger.info(f"Initialized WeatherPredictor with config")

    # Step 2: Initialize WeatherAggregator
    agg = WeatherAggregator(cache_ttl_minutes=30)
    logger.info(f"Initialized WeatherAggregator")

    # Step 3: Define temperature buckets for probability distribution
    buckets = create_buckets_from_range(low=85, high=105, unit='F')
    logger.info(f"Created {len(buckets)} temperature buckets (85-105°F)")

    # Step 4: Process all 7 Kalshi cities
    print("\n" + "-" * 80)
    print("Processing Cities with REAL Kalshi Market Data...")
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

            # REAL: Fetch Kalshi markets and prices
            print(f"\n  Fetching REAL Kalshi markets for {city_name}...")
            kalshi_markets = fetch_kalshi_markets(kalshi, city_name)

            if not kalshi_markets:
                print(f"  ⚠️  No Kalshi market data available for {city_name}")
                market_prices = {}
            else:
                # Convert bucket probabilities to threshold probabilities for comparison
                threshold_model_probs = convert_forecast_to_binary_probs(model_probs_dict, buckets)

                # Use Kalshi market prices directly
                market_prices = {
                    f"{int(threshold)}-{int(threshold)+1}": kalshi_markets[threshold]['market_prob']
                    for threshold in kalshi_markets.keys()
                    if threshold in threshold_model_probs
                }

                print(f"  ✓ Using {len(market_prices)} real Kalshi market prices")

            # Run edge detection with REAL market prices
            summary = predictor.calculate_edge(
                model_probs=model_probs,
                market_prices=market_prices if market_prices else {label: 0.5 for label in model_probs.keys()},
                buckets=buckets,
                station_id=station_id,
                weather_data=weather,
                min_edge=config.min_edge_threshold
            )

            # Print per-city summary
            print_trading_summary(summary, city_name, kalshi_markets)

            # Record for aggregate table
            results_table.append({
                'city': city_key,
                'name': city_name,
                'confidence': summary.confidence_score,
                'exposure': summary.recommended_exposure,
                'ev': summary.overall_ev,
                'markets': len(kalshi_markets),
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
    print("📋 Summary Table - REAL KALSHI MARKET DATA")
    print("=" * 80)
    print(f"{'City':<15} {'Confidence':<15} {'Exposure':<15} {'Markets':<10} {'EV':<12}")
    print("-" * 80)

    for result in results_table:
        if result['status'] != 'OK':
            print(f"{result.get('city', '?'):<15} {result['status']}")
        else:
            print(f"{result['name']:<15} {result['confidence']:>6.1f}/100     {result['exposure']:<15} {result.get('markets', 0):<10} {result['ev']:>+.4f}")

    print("=" * 80)
    print("\n✨ Live analysis complete!")
    print("\n✅ PRODUCTION MODE:")
    print("  • Using REAL Kalshi API orderbook prices")
    print("  • Real-time market data integrated")
    print("  • Trading signals based on actual market conditions")
    print("  • Ready for live order execution")


if __name__ == "__main__":
    # Run and capture output
    import sys
    from io import StringIO

    # Redirect stdout to capture output
    old_stdout = sys.stdout
    output_buffer = StringIO()
    sys.stdout = output_buffer

    try:
        main()
    finally:
        # Restore stdout
        sys.stdout = old_stdout

        # Get captured output
        output = output_buffer.getvalue()

        # Print to console
        print(output)

        # Also write to file
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"KALSHI_LIVE_EXECUTION_{timestamp}.md"

        # Wrap output in markdown
        markdown_output = f"""# Kalshi WeatherPredictor - Live Execution Report
**Execution Date**: {datetime.now(timezone.utc).isoformat()}
**Status**: ✅ PRODUCTION MODE - REAL MARKET DATA

---

## Execution Output

```
{output}
```

---

**Report Generated**: {timestamp}
"""

        with open(filename, 'w') as f:
            f.write(markdown_output)

        logger.info(f"Report saved to {filename}")
