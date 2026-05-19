"""
Example: Using weather API with Kalshi coordinates for prediction markets
"""

from weather_aggregator import WeatherAggregator
from weather_utils import WeatherFeatureExtractor, WeatherAggregations
from config import CITIES_KALSHI

def fetch_kalshi_weather(city_key: str, forecast_days: int = 7):
    """
    Fetch weather data for a Kalshi city using its configured coordinates

    Args:
        city_key: Key from CITIES_KALSHI (e.g., "NYC", "Chicago")
        forecast_days: Number of days to forecast (1-30)

    Returns:
        Complete weather data for the city
    """
    if city_key not in CITIES_KALSHI:
        print(f"❌ City '{city_key}' not found. Available cities: {list(CITIES_KALSHI.keys())}")
        return None

    city = CITIES_KALSHI[city_key]
    print(f"\n🌍 Fetching weather for {city['name']}")
    print(f"   Location: ({city['lat']}, {city['lon']})")
    print(f"   Station: {city['station']}")

    agg = WeatherAggregator(cache_ttl_minutes=30)

    try:
        weather = agg.get_complete_weather_data(
            latitude=city['lat'],
            longitude=city['lon'],
            location_name=city['name'],
            forecast_days=forecast_days,
            station_code=city['station']
        )

        if not weather:
            print("❌ Failed to fetch weather data")
            return None

        # Display current conditions
        if weather.current:
            print(f"\n📊 Current Conditions:")
            print(f"   Temperature: {weather.current.temperature:.1f}°C")
            print(f"   Feels like: {weather.current.feels_like:.1f}°C")
            print(f"   Humidity: {weather.current.humidity:.0f}%")
            print(f"   Wind: {weather.current.wind_speed:.1f} km/h")
            print(f"   Pressure: {weather.current.pressure:.1f} hPa")

        # Display forecasts
        print(f"\n📈 Forecasts:")
        print(f"   Hourly points: {len(weather.hourly_forecast)}")
        print(f"   Daily points: {len(weather.daily_forecast)}")
        if weather.daily_forecast:
            print(f"   First day: High {weather.daily_forecast[0].temperature_max:.1f}°C, Low {weather.daily_forecast[0].temperature_min:.1f}°C")

        # Display ensemble data
        if weather.ensemble_forecast:
            print(f"   Ensemble points: {len(weather.ensemble_forecast)}")
            first_ensemble = weather.ensemble_forecast[0]
            print(f"   First ensemble: {first_ensemble.temperature_mean:.1f}°C ± {first_ensemble.temperature_std:.1f}°C")

        # Extract ML features
        features = {
            **WeatherFeatureExtractor.current_conditions_dict(weather),
            **WeatherFeatureExtractor.hourly_statistics(weather.hourly_forecast, 24),
        }
        print(f"\n🤖 ML Features extracted: {len(features)}")

        # Calculate market-specific probabilities
        if weather.hourly_forecast:
            temp_prob = WeatherAggregations.temperature_exceedance_probability(
                weather.hourly_forecast, threshold=15, hours_ahead=24
            )
            wind_prob = WeatherAggregations.wind_event_probability(
                weather.hourly_forecast, threshold=25, hours_ahead=24
            )
            print(f"\n📊 Market Probabilities (next 24h):")
            print(f"   P(T > 15°C) = {temp_prob:.1%}")
            print(f"   P(Wind > 25 km/h) = {wind_prob:.1%}")

        return weather

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def compare_kalshi_cities():
    """
    Fetch and compare weather across all Kalshi cities
    """
    print("\n" + "="*80)
    print("🌦️ KALSHI CITIES WEATHER COMPARISON")
    print("="*80)

    results = {}
    for city_key in CITIES_KALSHI.keys():
        weather = fetch_kalshi_weather(city_key)
        if weather and weather.current:
            results[city_key] = {
                'temp': weather.current.temperature,
                'humidity': weather.current.humidity,
                'wind': weather.current.wind_speed,
            }

    if results:
        print("\n" + "="*80)
        print("📊 SUMMARY TABLE")
        print("="*80)
        print(f"{'City':<15} {'Temp (°C)':<12} {'Humidity':<12} {'Wind (km/h)':<12}")
        print("-"*80)
        for city, data in results.items():
            print(f"{city:<15} {data['temp']:<12.1f} {data['humidity']:<12.0f}% {data['wind']:<12.1f}")


if __name__ == "__main__":
    # Example 1: Fetch weather for a single city
    print("\n" + "="*80)
    print("Example 1: Single City Weather")
    print("="*80)
    nyc_weather = fetch_kalshi_weather("NYC", forecast_days=7)

    # Example 2: Compare all cities
    print("\n" + "="*80)
    print("Example 2: All Cities Comparison")
    print("="*80)
    compare_kalshi_cities()

    print("\n✅ Weather API examples complete!")
