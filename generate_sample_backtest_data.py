"""
Generate sample historical data for backtesting framework.

Creates synthetic weather data, market snapshots, and resolution outcomes
for testing the Phase 10 backtesting engine without relying on live APIs.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict
from weather_models import LocationWeatherData, ForecastPoint, EnsembleData
from weather_predictor import Bucket

logger = logging.getLogger(__name__)


def create_synthetic_weather(
    city: str,
    date: str,
    base_temp: float = 75.0,
    temp_std: float = 2.0
) -> LocationWeatherData:
    """Create synthetic weather data for a city and date."""
    dt = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    # Generate ensemble members
    ensemble_forecast = [
        EnsembleData(
            timestamp=dt,
            ensemble_members=10,
            temperature_mean=base_temp + i * 0.5,
            temperature_std=temp_std,
            temperature_min=base_temp - 5,
            temperature_max=base_temp + 5,
            wind_speed_mean=10.0 + i,
            wind_speed_std=2.0,
            precipitation_mean=0.0,
            precipitation_std=0.1
        )
        for i in range(10)
    ]

    return LocationWeatherData(
        latitude=40.77 if city == "NYC" else (41.88 if city == "Chicago" else 34.05),
        longitude=-73.97 if city == "NYC" else (-87.63 if city == "Chicago" else -118.24),
        last_updated=dt,
        daily_forecast=[
            ForecastPoint(
                timestamp=dt,
                temperature=base_temp,
                temperature_max=base_temp + 5
            )
        ],
        ensemble_forecast=ensemble_forecast
    )


def create_synthetic_market_snapshot(
    city: str,
    date: str,
    base_price: float = 0.50
) -> Dict:
    """Create synthetic market snapshot for a city and date."""
    dt = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    # Create temperature buckets
    buckets = []
    prices = {}
    volume = {}

    for low in range(60, 100, 5):
        high = low + 5
        label = f"{low}-{high}"
        buckets.append({
            "low": low,
            "high": high,
            "label": label
        })

        # Prices slope down as temperature gets more extreme
        price = max(0.01, base_price - abs(75 - (low + 2.5)) * 0.01)
        prices[label] = price
        volume[label] = 100 + (50 - abs(75 - (low + 2.5)) * 2)

    return {
        "timestamp": dt.isoformat(),
        "city": city,
        "buckets": buckets,
        "prices": prices,
        "volume": volume
    }


def create_sample_historical_data(
    output_dir: str = "backtest_cache",
    num_days: int = 21,
    start_date: str = "2026-05-01"
) -> None:
    """Generate sample historical data for backtesting."""
    Path(output_dir).mkdir(exist_ok=True)

    cities = {
        "NYC": {"base_temp": 75.0, "code": "KNYC"},
        "Chicago": {"base_temp": 70.0, "code": "KCHI"},
        "LA": {"base_temp": 80.0, "code": "KLA"}
    }

    start = datetime.strptime(start_date, "%Y-%m-%d")

    for day_offset in range(num_days):
        current_date = (start + timedelta(days=day_offset)).strftime("%Y-%m-%d")

        for city_name, city_info in cities.items():
            try:
                # Create weather data
                weather = create_synthetic_weather(
                    city_name,
                    current_date,
                    base_temp=city_info["base_temp"]
                )

                weather_file = Path(output_dir) / f"weather_{city_name}_{current_date}.json"
                with open(weather_file, 'w') as f:
                    data = {
                        "latitude": weather.latitude,
                        "longitude": weather.longitude,
                        "last_updated": weather.last_updated.isoformat(),
                        "daily_forecast": [
                            {
                                "timestamp": fp.timestamp.isoformat(),
                                "temperature": fp.temperature,
                                "temperature_max": fp.temperature_max
                            }
                            for fp in weather.daily_forecast
                        ],
                        "ensemble_forecast": [
                            {
                                "timestamp": ep.timestamp.isoformat(),
                                "ensemble_members": ep.ensemble_members,
                                "temperature_mean": ep.temperature_mean,
                                "temperature_std": ep.temperature_std,
                                "temperature_min": ep.temperature_min,
                                "temperature_max": ep.temperature_max,
                                "wind_speed_mean": ep.wind_speed_mean,
                                "wind_speed_std": ep.wind_speed_std,
                                "precipitation_mean": ep.precipitation_mean,
                                "precipitation_std": ep.precipitation_std
                            }
                            for ep in weather.ensemble_forecast
                        ]
                    }
                    json.dump(data, f, indent=2)

                # Create market snapshot
                market = create_synthetic_market_snapshot(city_name, current_date)
                market_file = Path(output_dir) / f"market_{city_name}_{current_date}_09.json"
                with open(market_file, 'w') as f:
                    json.dump(market, f, indent=2)

                # Create resolution outcome (actual temperature)
                actual_temp = city_info["base_temp"] + (day_offset % 7) - 3
                resolution_file = Path(output_dir) / f"resolution_{city_name}_{current_date}.json"
                with open(resolution_file, 'w') as f:
                    json.dump({"temperature": actual_temp}, f)

                logger.info(f"Generated data for {city_name} on {current_date}")

            except Exception as e:
                logger.error(f"Failed to generate data for {city_name}: {e}")

    logger.info(f"Generated {num_days} days of sample historical data in {output_dir}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_sample_historical_data()
    print("\n✓ Sample historical data generated in backtest_cache/")
    print("  Run: python3 backtest_engine.py")
