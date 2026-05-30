#!/usr/bin/env python3
"""Quick test of Kalshi API weather market access."""

import logging
from kalshi_api_client import KalshiAPIClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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

# Initialize client
logger.info("Initializing Kalshi API client...")
kalshi = KalshiAPIClient(API_KEY_ID, PRIVATE_KEY)

# Test 1: Get series information
logger.info("\n=== Test 1: Get Series Info ===")
series_tickers = ["KXHIGHNY", "KXHIGHCHI", "KXHIGHMIA"]
for ticker in series_tickers:
    try:
        series = kalshi.get_series(ticker)
        if series:
            logger.info(f"✓ Series {ticker}: {series.get('title', 'N/A')}")
        else:
            logger.warning(f"✗ Series {ticker}: No data returned")
    except Exception as e:
        logger.error(f"✗ Series {ticker}: {e}")

# Test 2: Get markets with series_ticker
logger.info("\n=== Test 2: Get Markets by Series ===")
for ticker in series_tickers:
    try:
        markets = kalshi.get_markets(status=None, series_ticker=ticker)
        logger.info(f"✓ Series {ticker}: Found {len(markets)} markets")
        if markets:
            sample = markets[0]
            logger.info(f"  Sample market: {sample.get('ticker')} - {sample.get('title', 'N/A')[:50]}")
    except Exception as e:
        logger.error(f"✗ Series {ticker}: {e}")

# Test 3: Get orderbook for a specific market
logger.info("\n=== Test 3: Get Orderbook ===")
test_markets = [
    "KXHIGHNY-22NOV27-T57",
    "KXHIGHCHI-22NOV27-T75",
]
for market_ticker in test_markets:
    try:
        orderbook = kalshi.get_orderbook(market_ticker)
        if orderbook:
            yes_bids = orderbook.get("yes_dollars", [])
            no_bids = orderbook.get("no_dollars", [])
            logger.info(f"✓ Market {market_ticker}: YES bids={len(yes_bids)}, NO bids={len(no_bids)}")
            if yes_bids and no_bids:
                logger.info(f"  YES price: ${yes_bids[-1][0]}, NO price: ${no_bids[-1][0]}")
        else:
            logger.warning(f"✗ Market {market_ticker}: No orderbook data")
    except Exception as e:
        logger.error(f"✗ Market {market_ticker}: {e}")

logger.info("\n✨ API tests complete!")
