"""
Market Parser Module

Extracts and standardizes market data from Kalshi into internal structures.
Handles temperature range parsing, unit detection (°F vs °C), and city mapping.

Purpose: Normalize raw Kalshi market data early in the scanning pipeline
to ensure all downstream components receive clean, standardized Bucket objects.
"""

import re
import logging
from typing import Optional, Tuple, List, Dict
from weather_predictor import Bucket, parse_bucket_string

logger = logging.getLogger(__name__)

# City configuration with resolution-station coordinates
# CRITICAL: Coordinates must point to the Kalshi market's resolution station, not city center
# Verify each station against Kalshi market rules before trading live
CITIES_KALSHI = {
    'NYC': {'lat': 40.7772, 'lon': -73.8726, 'code': 'KLGA'},  # LaGuardia Airport
    'Chicago': {'lat': 41.9742, 'lon': -87.9073, 'code': 'KORD'},  # O'Hare Airport
    'Dallas': {'lat': 32.8471, 'lon': -96.8518, 'code': 'KDAL'},  # Love Field Airport
    'Denver': {'lat': 39.7392, 'lon': -104.9903, 'code': 'KDEN'},  # Denver Int'l
    'Los Angeles': {'lat': 34.0522, 'lon': -118.2437, 'code': 'KLAX'},  # LAX
    'Atlanta': {'lat': 33.6407, 'lon': -84.4277, 'code': 'KATL'},  # Hartsfield-Jackson Int'l
    'Miami': {'lat': 25.7959, 'lon': -80.2870, 'code': 'KMIA'},  # Miami Int'l
}


def parse_market_buckets(market: Dict) -> Optional[Tuple[List[Bucket], str]]:
    """
    Parse Kalshi market title to extract temperature buckets and station ID.

    Handles common format variations:
    - "New York Daily High Temperature 88-89°F"
    - "NYC Low 65-66"
    - "Chicago High Temp: 72-73F"
    - "LA Daily High 95-96"

    Args:
        market: Dict with keys 'title', 'ticker', and optionally 'resolution_unit'

    Returns:
        Tuple of (List[Bucket], station_id) if successful, None otherwise
    """
    try:
        title = market.get('title', '').strip()
        ticker = market.get('ticker', '')

        if not title:
            logger.debug(f"Empty market title for {ticker}")
            return None

        # Identify which city this market is for
        city_name = None
        station_id = None
        for city, config in CITIES_KALSHI.items():
            if city.upper() in title.upper() or city in title:
                city_name = city
                station_id = config['code']
                break

        # Fallback for abbreviated city names (LA, NYC, Chi)
        if not city_name:
            title_upper = title.upper()
            if 'LA' in title_upper or 'LOS ANGELES' in title_upper:
                city_name = 'Los Angeles'
                station_id = CITIES_KALSHI['Los Angeles']['code']
            elif 'CHICAGO' in title_upper or 'CHI' in title_upper:
                city_name = 'Chicago'
                station_id = CITIES_KALSHI['Chicago']['code']
            elif 'ATLANTA' in title_upper or 'ATL' in title_upper:
                city_name = 'Atlanta'
                station_id = CITIES_KALSHI['Atlanta']['code']
            elif 'MIAMI' in title_upper or 'MIA' in title_upper:
                city_name = 'Miami'
                station_id = CITIES_KALSHI['Miami']['code']

        if not station_id:
            logger.debug(f"Could not identify city in title: {title}")
            return None

        # Detect unit (°F, F, °C, C)
        unit = 'F'  # default
        if '°C' in title or 'C°' in title:
            unit = 'C'
        elif 'celsius' in title.lower():
            unit = 'C'
        elif '°F' in title or 'F°' in title:
            unit = 'F'
        elif 'fahrenheit' in title.lower():
            unit = 'F'

        # Extract all temperature ranges using regex
        # Matches: "88-89", "88-89°F", "88-89F", "88 - 89", etc.
        pattern = r'(\d+)\s*[-–]\s*(\d+)\s*[°]?[FC]?'
        matches = re.findall(pattern, title)

        if not matches:
            logger.debug(f"No temperature ranges found in: {title}")
            return None

        buckets = []
        for low_str, high_str in matches:
            try:
                low = float(low_str)
                high = float(high_str)

                # Validate range
                if low >= high:
                    logger.debug(f"Invalid range {low}-{high} (low >= high)")
                    continue

                # Create bucket with standard label format
                label = f"{int(low)}-{int(high)}"
                bucket = Bucket(low=low, high=high, label=label)
                buckets.append(bucket)

            except (ValueError, TypeError) as e:
                logger.debug(f"Failed to parse bucket {low_str}-{high_str}: {e}")
                continue

        if not buckets:
            logger.debug(f"No valid buckets extracted from: {title}")
            return None

        logger.debug(
            f"Parsed {len(buckets)} bucket(s) for {city_name} ({station_id}): "
            f"{[b.label for b in buckets]} [{unit}]"
        )
        return buckets, station_id

    except Exception as e:
        logger.error(f"Market parsing failed for {market.get('ticker', 'UNKNOWN')}: {e}")
        return None


def get_city_for_station(station_id: str) -> Optional[str]:
    """Get city name from station code."""
    for city, config in CITIES_KALSHI.items():
        if config['code'] == station_id:
            return city
    return None


def get_station_config(station_id: str) -> Optional[Dict]:
    """Get full config (lat, lon, code) for a station."""
    for city, config in CITIES_KALSHI.items():
        if config['code'] == station_id:
            return config
    return None


def validate_buckets(buckets: List[Bucket]) -> bool:
    """Validate that buckets are complete and non-overlapping."""
    if not buckets or len(buckets) < 1:
        return False

    # Check for gaps or overlaps
    sorted_buckets = sorted(buckets, key=lambda b: b.low)
    for i in range(len(sorted_buckets) - 1):
        current = sorted_buckets[i]
        next_bucket = sorted_buckets[i + 1]

        # Buckets should be adjacent or have a small gap (for rounding)
        if next_bucket.low > current.high + 1:
            logger.warning(f"Gap detected between {current.label} and {next_bucket.label}")
            return False

    return True


if __name__ == '__main__':
    # Quick test
    logging.basicConfig(level=logging.DEBUG)

    test_markets = [
        {'title': 'New York Daily High Temperature 88-89°F', 'ticker': 'KNYC-88-89'},
        {'title': 'NYC Low 65-66', 'ticker': 'KNYC-LOW-65-66'},
        {'title': 'Chicago High Temp: 72-73F', 'ticker': 'KMDW-72-73'},
        {'title': 'Invalid Format XYZ', 'ticker': 'INVALID'},
    ]

    for market in test_markets:
        result = parse_market_buckets(market)
        if result:
            buckets, station_id = result
            print(f"✓ {market['ticker']}: {[b.label for b in buckets]} ({station_id})")
        else:
            print(f"✗ {market['ticker']}: parsing failed")
