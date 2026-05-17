"""
Example usage of the weather aggregation foundation.
Demonstrates all capabilities: current weather, forecasts, ensemble data, and validation.
"""
import logging
from datetime import datetime
from weather_aggregator import WeatherAggregator
from weather_models import WeatherSource

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_basic_current_weather():
    """Fetch current weather from multiple sources"""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Current Weather (Multi-Source Fallback)")
    print("=" * 60)

    agg = WeatherAggregator(cache_ttl_minutes=30)

    # New York City coordinates
    lat, lon = 40.7128, -74.0060
    location = "New York City"

    current = agg.get_current_weather(lat, lon)
    if current:
        print(f"\n📍 {location} ({lat}, {lon})")
        print(f"🌡️  Temperature: {current.temperature:.1f}°C")
        print(f"🌬️  Wind: {current.wind_speed:.1f} km/h @ {current.wind_direction}°")
        print(f"💧 Humidity: {current.humidity}%")
        print(f"☁️  Cloud Cover: {current.cloud_cover}%")
        print(f"📊 Source: {current.source.value}")
        print(f"⏰ Time: {current.timestamp}")
    else:
        print("Failed to fetch current weather")


def example_hourly_forecast():
    """Fetch hourly forecast for next 7 days"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Hourly Forecast (7 Days)")
    print("=" * 60)

    agg = WeatherAggregator()

    # San Francisco coordinates
    lat, lon = 37.7749, -122.4194
    location = "San Francisco"

    hourly = agg.get_hourly_forecast(lat, lon, days=7)
    if hourly:
        print(f"\n📍 {location} ({lat}, {lon})")
        print(f"Total hourly points: {len(hourly)}")
        print(f"Source: {hourly[0].source.value}")
        print("\nFirst 5 hours:")
        for forecast in hourly[:5]:
            print(f"  {forecast.timestamp} - {forecast.temperature:.1f}°C, "
                  f"Precip Prob: {forecast.precipitation_probability}%")
    else:
        print("Failed to fetch hourly forecast")


def example_daily_forecast():
    """Fetch daily forecast for next 30 days"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Daily Forecast (30 Days)")
    print("=" * 60)

    agg = WeatherAggregator()

    # London coordinates
    lat, lon = 51.5074, -0.1278
    location = "London"

    daily = agg.get_daily_forecast(lat, lon, days=30)
    if daily:
        print(f"\n📍 {location} ({lat}, {lon})")
        print(f"Total daily points: {len(daily)}")
        print(f"Source: {daily[0].source.value}")
        print("\nNext 10 days:")
        for forecast in daily[:10]:
            print(f"  {forecast.timestamp.date()} - "
                  f"High: {forecast.temperature_max:.1f}°C, "
                  f"Low: {forecast.temperature_min:.1f}°C, "
                  f"Precip: {forecast.precipitation:.1f}mm")
    else:
        print("Failed to fetch daily forecast")


def example_ensemble_forecast():
    """Fetch ensemble forecast with confidence metrics"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Ensemble Forecast (Confidence Metrics)")
    print("=" * 60)

    agg = WeatherAggregator()

    # Chicago coordinates
    lat, lon = 41.8781, -87.6298
    location = "Chicago"

    ensemble = agg.get_ensemble_forecast(lat, lon, days=5)
    if ensemble:
        print(f"\n📍 {location} ({lat}, {lon})")
        print(f"Ensemble points: {len(ensemble)}")

        if ensemble:
            # Show first 3 points
            print("\nFirst 3 ensemble points:")
            for ens in ensemble[:3]:
                print(f"  {ens.timestamp}")
                print(f"    Temperature: {ens.temperature_mean:.1f}°C ± {ens.temperature_std:.1f}°C")
                print(f"    Range: {ens.temperature_min:.1f}°C to {ens.temperature_max:.1f}°C")
                print(f"    Ensemble members: {ens.ensemble_members}")
                print(f"    Precipitation: {ens.precipitation_mean:.1f}mm ± {ens.precipitation_std:.1f}mm")

            # Calculate confidence scores
            confidence = agg.ensemble_confidence_score(ensemble)
            print(f"\n📊 Confidence Scores:")
            print(f"  Temperature Confidence: {confidence['temperature_confidence']:.2%}")
            print(f"  Precipitation Confidence: {confidence['precipitation_confidence']:.2%}")
            print(f"  Mean Spread: ±{confidence['mean_spread_degrees']:.2f}°C")
    else:
        print("Failed to fetch ensemble forecast")


def example_complete_weather_data():
    """Fetch all weather data for a location"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Complete Weather Data (All Sources)")
    print("=" * 60)

    agg = WeatherAggregator()

    # Miami coordinates
    lat, lon = 25.7617, -80.1918
    location = "Miami"

    complete_data = agg.get_complete_weather_data(
        latitude=lat,
        longitude=lon,
        location_name=location,
        forecast_days=7,
        historical_days=7,
        station_code=None  # Add METAR station code if available (e.g., "KMIA")
    )

    if complete_data:
        print(f"\n📍 {location}")
        print(f"Latitude: {complete_data.latitude}, Longitude: {complete_data.longitude}")
        print(f"Last Updated: {complete_data.last_updated}")
        print(f"Sources Used: {[s.value for s in complete_data.sources_used]}")

        if complete_data.current:
            print(f"\n📊 Current Conditions (from {complete_data.current.source.value}):")
            print(f"  Temperature: {complete_data.current.temperature:.1f}°C")
            print(f"  Conditions: {complete_data.current.weather_description or 'N/A'}")
            print(f"  Wind: {complete_data.current.wind_speed:.1f} km/h")

        print(f"\n📈 Hourly Forecast: {len(complete_data.hourly_forecast)} points")
        print(f"📅 Daily Forecast: {len(complete_data.daily_forecast)} points")
        print(f"🎲 Ensemble Forecast: {len(complete_data.ensemble_forecast)} points")
        print(f"📋 Historical Observations: {len(complete_data.historical_observations)} points")
    else:
        print("Failed to fetch complete weather data")


def example_cache_behavior():
    """Demonstrate caching behavior"""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Caching Behavior")
    print("=" * 60)

    agg = WeatherAggregator(cache_ttl_minutes=5)

    lat, lon = 48.8566, 2.3522  # Paris

    print(f"\n📍 Paris ({lat}, {lon})")
    print("First call (cache miss)...")
    start = datetime.utcnow()
    current1 = agg.get_current_weather(lat, lon)
    time1 = (datetime.utcnow() - start).total_seconds()
    print(f"  Time: {time1:.2f}s")

    print("Second call (cache hit)...")
    start = datetime.utcnow()
    current2 = agg.get_current_weather(lat, lon)
    time2 = (datetime.utcnow() - start).total_seconds()
    print(f"  Time: {time2:.2f}s")

    print(f"\nCache speedup: {time1 / time2:.1f}x faster")

    print("\nClearing cache...")
    agg.clear_cache()


def example_validation():
    """Demonstrate forecast validation against observations"""
    print("\n" + "=" * 60)
    print("EXAMPLE 7: Forecast Validation")
    print("=" * 60)

    agg = WeatherAggregator()

    # Get forecast and historical observations
    lat, lon = 40.7128, -74.0060
    location = "New York City"

    hourly_forecast = agg.get_hourly_forecast(lat, lon, days=7)

    # For METAR validation, you need the airport code
    # Common US airport codes: KJFK (JFK), KLGA (LaGuardia), KEWR (Newark)
    station_code = "KJFK"
    observations = agg.get_historical_observations(lat, lon, days_back=7, station_code=station_code)

    if hourly_forecast and observations:
        print(f"\n📍 {location}")
        print(f"Forecast points: {len(hourly_forecast)}")
        print(f"Observations: {len(observations)}")

        # Validate temperature predictions
        temp_metrics = agg.validate_forecast_against_observations(
            hourly_forecast, observations, variable="temperature"
        )

        if temp_metrics:
            print(f"\n🌡️  Temperature Validation:")
            print(f"  MAE: {temp_metrics.mae:.2f}°C")
            print(f"  RMSE: {temp_metrics.rmse:.2f}°C")
            print(f"  Bias: {temp_metrics.bias:.2f}°C (positive = forecast too warm)")
            print(f"  Matched pairs: {temp_metrics.matched_count}/{temp_metrics.forecast_count}")
        else:
            print("No matched forecast-observation pairs for validation")
    else:
        print("Insufficient data for validation")


if __name__ == "__main__":
    print("\n" + "🌦️ " * 30)
    print("POLYMARKET WEATHER FOUNDATION - USAGE EXAMPLES")
    print("🌦️ " * 30)

    # Run examples
    try:
        example_basic_current_weather()
        example_hourly_forecast()
        example_daily_forecast()
        example_ensemble_forecast()
        example_complete_weather_data()
        example_cache_behavior()
        # Note: example_validation() requires METAR station codes and may not have recent data
        # example_validation()
    except Exception as e:
        logger.error(f"Error running examples: {e}", exc_info=True)

    print("\n" + "=" * 60)
    print("Examples Complete!")
    print("=" * 60)
    print("\n📚 Next Steps:")
    print("  1. Customize coordinates to your target markets")
    print("  2. Add METAR station codes for validation")
    print("  3. Integrate with your prediction bot")
    print("  4. Fine-tune cache TTL based on your needs")
