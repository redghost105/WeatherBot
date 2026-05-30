#!/usr/bin/env python3
"""Test single city end-to-end flow with real API and weather data."""

import logging
from datetime import datetime, timezone
from weather_aggregator import WeatherAggregator
from weather_predictor import WeatherPredictor, PredictorConfig, create_buckets_from_range
from kalshi_api_client import KalshiAPIClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# NYC setup
CITY_NAME = "New York City"
LAT, LON = 40.7789, -73.9692
SERIES_TICKER = "KXHIGHNY"
STATION_ID = "KNYC"

# API credentials
API_KEY_ID = "c9d784b0-f004-413d-a380-205288096083"
PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
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

logger.info("=== NYC Single City Test ===\n")

# Step 1: Fetch weather
logger.info("Step 1: Fetch real weather from Open-Meteo")
agg = WeatherAggregator()
weather = agg.get_complete_weather_data(LAT, LON, CITY_NAME, forecast_days=3, station_code=STATION_ID)
logger.info(f"✓ Weather fetched: {weather.daily_forecast[0].temperature:.1f}°F current\n")

# Step 2: Generate probabilities
logger.info("Step 2: Generate hybrid probabilities")
config = PredictorConfig(ensemble_weight=0.7, min_edge_threshold=0.05)
predictor = WeatherPredictor(config=config)
buckets = create_buckets_from_range(85, 105, 'F', step=1.0)
model_probs = predictor.hybrid_bucket_probabilities(weather, buckets, STATION_ID)
logger.info(f"✓ Generated {len(model_probs)} bucket probabilities\n")

# Step 3: Fetch Kalshi markets
logger.info(f"Step 3: Fetch real markets for {CITY_NAME}")
kalshi = KalshiAPIClient(API_KEY_ID, PRIVATE_KEY)
found_markets = kalshi.get_markets(status=None, series_ticker=SERIES_TICKER)
logger.info(f"✓ Found {len(found_markets)} markets\n")

# Step 4: Fetch orderbooks for recent markets only
logger.info("Step 4: Fetch orderbooks for recent markets")
now = datetime.now(timezone.utc)
cutoff_date = now.replace(day=now.day+5)  # Next 5 days

recent_count = 0
market_prices = {}

for market in found_markets[:20]:  # Limit to first 20 to avoid timeout
    ticker = market.get("ticker", "")
    try:
        # Extract date
        parts = ticker.split("-")
        if len(parts) >= 2:
            date_str = parts[1]
            market_date = datetime.strptime(date_str, "%d%b%y").replace(tzinfo=timezone.utc)
            if market_date > cutoff_date:
                continue

        recent_count += 1

        # Fetch orderbook
        orderbook = kalshi.get_orderbook(ticker)
        yes_bids = orderbook.get("yes_dollars", [])
        no_bids = orderbook.get("no_dollars", [])

        if yes_bids and no_bids:
            yes_price = float(yes_bids[-1][0])
            no_price = float(no_bids[-1][0])

            # Extract threshold
            strike_str = ticker.rsplit("-", 1)[-1]
            if strike_str.startswith("T"):
                threshold = float(strike_str[1:])
                market_prices[threshold] = {"yes": yes_price, "no": no_price}
                logger.info(f"  {ticker}: T={threshold}, YES=${yes_price:.2f}, NO=${no_price:.2f}")

    except Exception as e:
        logger.debug(f"  Skipped {ticker}: {e}")
        continue

logger.info(f"✓ Fetched {recent_count} recent markets with pricing\n")

# Step 5: Convert bucket probs to threshold probs
logger.info("Step 5: Convert bucket probabilities to threshold format")
thresholds_probs = {}
for threshold in range(75, 100):
    threshold_decimal = float(f"{threshold}.99")
    prob_above = sum(
        model_probs[bucket.label]['probability']
        for bucket in buckets
        if bucket.label in model_probs and bucket.midpoint() > threshold_decimal
    )
    thresholds_probs[threshold_decimal] = prob_above

logger.info(f"✓ Generated {len(thresholds_probs)} threshold probabilities")
logger.info(f"  Example: P(Temp > 75.99) = {thresholds_probs.get(75.99, 0):.2%}\n")

logger.info("=== TEST COMPLETE ===")
logger.info(f"✓ Real weather data: {weather.daily_forecast[0].temperature:.1f}°F")
logger.info(f"✓ Real market prices: {len(market_prices)} markets with bids")
logger.info(f"✓ Model probabilities: {len(model_probs)} buckets")
