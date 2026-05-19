"""Configuration for Kalshi weather prediction markets"""

# KALSHI CITIES optimized for Open-Meteo
CITIES_KALSHI = {
    "NYC": {
        "name": "New York City",
        "lat": 40.7789,      # Central Park (KNYC)
        "lon": -73.9692,
        "station": "KNYC",
        "platform": "kalshi"
    },

    "Chicago": {
        "name": "Chicago",
        "lat": 41.7842,      # Midway Airport (KMDW)
        "lon": -87.7553,
        "station": "KMDW",
        "platform": "kalshi"
    },

    "Miami": {
        "name": "Miami",
        "lat": 25.7933,
        "lon": -80.2906,
        "station": "KMIA",
        "platform": "kalshi"
    },

    "Atlanta": {
        "name": "Atlanta",
        "lat": 33.6407,
        "lon": -84.4277,
        "station": "KATL",
        "platform": "kalshi"
    },

    "Dallas": {
        "name": "Dallas",
        "lat": 32.8968,      # DFW (most common)
        "lon": -97.0380,
        "station": "KDFW",
        "platform": "kalshi"
    },

    "LosAngeles": {
        "name": "Los Angeles",
        "lat": 33.9425,
        "lon": -118.4081,
        "station": "KLAX",
        "platform": "kalshi"
    },

    "Denver": {
        "name": "Denver",
        "lat": 39.8561,
        "lon": -104.6737,
        "station": "KDEN",
        "platform": "kalshi"
    }
}

# Default cache TTL in minutes
DEFAULT_CACHE_TTL = 30

# API timeouts in seconds
API_TIMEOUT = 10

# Logging configuration
LOG_LEVEL = "INFO"
