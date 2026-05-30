#!/usr/bin/env python3
"""Capture exact market tickers being fetched from Kalshi API."""

import logging
from kalshi_api_client import KalshiAPIClient
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

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

# City to series mapping with URL patterns
CITIES = {
    "New York City": ("KXHIGHNY", "highest-temperature-in-nyc"),
    "Chicago": ("KXHIGHCHI", "highest-temperature-in-chicago"),
    "Miami": ("KXHIGHMIA", "highest-temperature-in-miami"),
    "Los Angeles": ("KXHIGHLAX", "highest-temperature-in-los-angeles"),
    "Denver": ("KXHIGHDEN", "highest-temperature-in-denver"),
}

kalshi = KalshiAPIClient(API_KEY_ID, PRIVATE_KEY)

logger.info("=" * 100)
logger.info("KALSHI WEATHER MARKETS - CURRENT TICKERS BEING PROCESSED")
logger.info("=" * 100)
logger.info("")

now = datetime.now(timezone.utc)

for city_name, (series_ticker, url_slug) in CITIES.items():
    logger.info(f"\n📍 {city_name} ({series_ticker})")
    logger.info("-" * 100)

    # Fetch markets
    found_markets = kalshi.get_markets(status=None, series_ticker=series_ticker)

    if not found_markets:
        logger.info(f"  ⚠️  No markets found")
        continue

    # Filter to today and future
    recent_markets = []
    for market in found_markets:
        ticker = market.get("ticker", "")
        try:
            parts = ticker.split("-")
            if len(parts) >= 2:
                date_str = parts[1]
                market_date = datetime.strptime(date_str, "%y%b%d").replace(tzinfo=timezone.utc)
                if market_date.date() >= now.date():
                    recent_markets.append(market)
        except:
            recent_markets.append(market)

    # Show first 10
    for i, market in enumerate(recent_markets[:10], 1):
        ticker = market.get("ticker", "")
        title = market.get("title", "")[:70]

        # Extract event ticker from full market ticker (SERIES-DATE)
        # Full ticker format: KXHIGHNY-26MAY21-T75
        # Event ticker format: kxhighny-26may21 (lowercase, series-date only)
        parts = ticker.split("-")
        if len(parts) >= 2:
            event_ticker = f"{parts[0]}-{parts[1]}".lower()
            kalshi_url = f"https://kalshi.com/markets/{series_ticker.lower()}/{url_slug}/{event_ticker}"
        else:
            kalshi_url = "URL could not be generated"

        logger.info(f"\n  {i}. {ticker}")
        logger.info(f"     Title: {title}...")
        logger.info(f"     URL: {kalshi_url}")

    logger.info(f"\n  Total markets available: {len(found_markets)}")
    logger.info(f"  Markets for today+future: {len(recent_markets)}")

logger.info("\n" + "=" * 100)
logger.info("✅ COPY-PASTE URLS ABOVE INTO YOUR BROWSER TO VERIFY MARKETS")
logger.info("=" * 100)
