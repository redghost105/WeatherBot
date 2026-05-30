"""Configuration for Kalshi weather prediction markets

DEPRECATED: Use market_parser.CITIES_KALSHI instead. This is kept for backward compatibility
but should not be used for new code. market_parser.CITIES_KALSHI is the single source of truth.
"""

# This dict is kept for backward compatibility only
# DO NOT USE: Import from market_parser.CITIES_KALSHI instead
CITIES_KALSHI = {}  # Empty; use market_parser.CITIES_KALSHI

# Default cache TTL in minutes
DEFAULT_CACHE_TTL = 30

# API timeouts in seconds
API_TIMEOUT = 10

# Logging configuration
LOG_LEVEL = "INFO"
