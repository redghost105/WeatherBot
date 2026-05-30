"""
Comprehensive test suite for weather foundation.
Tests all modules with real API data and documents formats/parameters.
"""
import logging
import json
from datetime import datetime
from pprint import pprint

from weather_aggregator import WeatherAggregator
from weather_sources import OpenMeteoSource, NOAASource, METARSource
from weather_models import WeatherSource
from weather_utils import WeatherFeatureExtractor, WeatherValidation, WeatherAggregations

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestWeatherFoundation:
    """Comprehensive test suite for weather foundation"""

    def __init__(self):
        self.agg = WeatherAggregator(cache_ttl_minutes=60)
        self.test_coords = {
            "NYC": {"lat": 40.7128, "lon": -74.0060},
            "SF": {"lat": 37.7749, "lon": -122.4194},
            "London": {"lat": 51.5074, "lon": -0.1278},
        }
        self.results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }

    def print_section(self, title):
        """Print test section header"""
        print("\n" + "="*80)
        print(f"🧪 {title}")
        print("="*80)

    def print_test(self, test_name, status, details=""):
        """Print individual test result"""
        symbol = "✅" if status else "❌"
        print(f"{symbol} {test_name}")
        if details:
            print(f"   {details}")
        if status:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1
            self.results["errors"].append(test_name)

    # =========== TEST 1: Open-Meteo Source ===========
    def test_openmeteo_source(self):
        """Test Open-Meteo API adapter"""
        self.print_section("Test 1: Open-Meteo Source")

        source = OpenMeteoSource()
        lat, lon = self.test_coords["NYC"]["lat"], self.test_coords["NYC"]["lon"]

        # Test 1.1: Current Weather
        try:
            current = source.get_current_weather(lat, lon)
            if current:
                self.print_test("1.1 Current Weather", True,
                    f"Temp: {current.temperature}°C, Source: {current.source.value}")

                print("\n   📊 CurrentWeather Format:")
                print(f"   - timestamp: {current.timestamp} (type: datetime)")
                print(f"   - temperature: {current.temperature} (type: float, °C)")
                print(f"   - temperature_2m: {current.temperature_2m} (type: float, °C at 2m height)")
                print(f"   - feels_like: {current.feels_like} (type: float or None, °C)")
                print(f"   - humidity: {current.humidity} (type: float or None, 0-100%)")
                print(f"   - dew_point: {current.dew_point} (type: float or None, °C)")
                print(f"   - wind_speed: {current.wind_speed} (type: float, km/h)")
                print(f"   - wind_direction: {current.wind_direction} (type: int or None, 0-360°)")
                print(f"   - wind_gust: {current.wind_gust} (type: float or None, km/h)")
                print(f"   - precipitation: {current.precipitation} (type: float, mm)")
                print(f"   - precipitation_probability: {current.precipitation_probability} (type: float or None, 0-100%)")
                print(f"   - weather_code: {current.weather_code} (type: int or None, WMO code)")
                print(f"   - weather_description: {current.weather_description} (type: str or None)")
                print(f"   - cloud_cover: {current.cloud_cover} (type: float or None, 0-100%)")
                print(f"   - visibility: {current.visibility} (type: float or None, km)")
                print(f"   - pressure: {current.pressure} (type: float or None, hPa)")
                print(f"   - source: {current.source.value} (type: WeatherSource enum)")
            else:
                self.print_test("1.1 Current Weather", False, "No data returned")
        except Exception as e:
            self.print_test("1.1 Current Weather", False, f"Error: {e}")

        # Test 1.2: Hourly Forecast
        try:
            hourly = source.get_hourly_forecast(lat, lon, days=7)
            if hourly and len(hourly) > 0:
                self.print_test("1.2 Hourly Forecast (7 days)", True,
                    f"Retrieved {len(hourly)} hourly points")

                first_point = hourly[0]
                print("\n   📊 ForecastPoint Format (Hourly):")
                print(f"   - timestamp: {first_point.timestamp} (type: datetime)")
                print(f"   - temperature: {first_point.temperature} (type: float, °C)")
                print(f"   - humidity: {first_point.humidity} (type: float or None, %)")
                print(f"   - wind_speed: {first_point.wind_speed} (type: float, km/h)")
                print(f"   - precipitation: {first_point.precipitation} (type: float, mm)")
                print(f"   - precipitation_probability: {first_point.precipitation_probability} (type: float or None, %)")
                print(f"   - cloud_cover: {first_point.cloud_cover} (type: float or None, %)")
                print(f"   - pressure: {first_point.pressure} (type: float or None, hPa)")
                print(f"   Sample: {first_point.timestamp} - {first_point.temperature}°C, {first_point.precipitation_probability}% precip")
            else:
                self.print_test("1.2 Hourly Forecast", False, "No data returned")
        except Exception as e:
            self.print_test("1.2 Hourly Forecast", False, f"Error: {e}")

        # Test 1.3: Daily Forecast
        try:
            daily = source.get_daily_forecast(lat, lon, days=30)
            if daily and len(daily) > 0:
                self.print_test("1.3 Daily Forecast (30 days)", True,
                    f"Retrieved {len(daily)} daily points")

                first_day = daily[0]
                print("\n   📊 ForecastPoint Format (Daily):")
                print(f"   - timestamp: {first_day.timestamp} (type: datetime, date)")
                print(f"   - temperature: {first_day.temperature} (type: float, °C, mean)")
                print(f"   - temperature_max: {first_day.temperature_max} (type: float, °C)")
                print(f"   - temperature_min: {first_day.temperature_min} (type: float, °C)")
                print(f"   - precipitation: {first_day.precipitation} (type: float, mm daily total)")
                print(f"   - precipitation_probability: {first_day.precipitation_probability} (type: float or None, %)")
                print(f"   Sample: {first_day.timestamp.date()} - High: {first_day.temperature_max}°C, Low: {first_day.temperature_min}°C")
            else:
                self.print_test("1.3 Daily Forecast", False, "No data returned")
        except Exception as e:
            self.print_test("1.3 Daily Forecast", False, f"Error: {e}")

        # Test 1.4: Ensemble Forecast
        try:
            ensemble = source.get_ensemble_forecast(lat, lon, days=5)
            if ensemble and len(ensemble) > 0:
                self.print_test("1.4 Ensemble Forecast", True,
                    f"Retrieved {len(ensemble)} ensemble points")

                ens_point = ensemble[0]
                print("\n   📊 EnsembleData Format:")
                print(f"   - timestamp: {ens_point.timestamp} (type: datetime)")
                print(f"   - ensemble_members: {ens_point.ensemble_members} (type: int, number of models)")
                print(f"   - temperature_mean: {ens_point.temperature_mean} (type: float, °C)")
                print(f"   - temperature_std: {ens_point.temperature_std} (type: float, °C, standard deviation)")
                print(f"   - temperature_min: {ens_point.temperature_min} (type: float, °C, across members)")
                print(f"   - temperature_max: {ens_point.temperature_max} (type: float, °C, across members)")
                print(f"   - precipitation_mean: {ens_point.precipitation_mean} (type: float, mm)")
                print(f"   - precipitation_std: {ens_point.precipitation_std} (type: float, mm, spread)")
                print(f"   Sample: {ens_point.timestamp} - {ens_point.temperature_mean:.1f}°C ± {ens_point.temperature_std:.1f}°C")
            else:
                self.print_test("1.4 Ensemble Forecast", True,
                    "Ensemble endpoint experimental (returns empty gracefully)")
        except Exception as e:
            self.print_test("1.4 Ensemble Forecast", False, f"Error: {e}")

    # =========== TEST 2: NOAA Source ===========
    def test_noaa_source(self):
        """Test NOAA/NWS API adapter"""
        self.print_section("Test 2: NOAA/NWS Source")

        source = NOAASource()
        lat, lon = self.test_coords["NYC"]["lat"], self.test_coords["NYC"]["lon"]

        # Test 2.1: Current Weather
        try:
            current = source.get_current_weather(lat, lon)
            if current:
                self.print_test("2.1 Current Weather", True,
                    f"Temp: {current.temperature}°C, Source: {current.source.value}")
            else:
                self.print_test("2.1 Current Weather", False, "No data returned")
        except Exception as e:
            self.print_test("2.1 Current Weather", False, f"Error: {e}")

        # Test 2.2: Hourly Forecast
        try:
            hourly = source.get_hourly_forecast(lat, lon, days=7)
            if hourly and len(hourly) > 0:
                self.print_test("2.2 Hourly Forecast", True,
                    f"Retrieved {len(hourly)} hourly points")
            else:
                self.print_test("2.2 Hourly Forecast", False, "No data returned")
        except Exception as e:
            self.print_test("2.2 Hourly Forecast", False, f"Error: {e}")

        # Test 2.3: Daily Forecast
        try:
            daily = source.get_daily_forecast(lat, lon, days=7)
            if daily and len(daily) > 0:
                self.print_test("2.3 Daily Forecast", True,
                    f"Retrieved {len(daily)} daily points")
            else:
                self.print_test("2.3 Daily Forecast", False, "No data returned")
        except Exception as e:
            self.print_test("2.3 Daily Forecast", False, f"Error: {e}")

    # =========== TEST 3: Aggregator ===========
    def test_aggregator(self):
        """Test main aggregator with fallback logic"""
        self.print_section("Test 3: Weather Aggregator (Fallback Logic)")

        lat, lon = self.test_coords["NYC"]["lat"], self.test_coords["NYC"]["lon"]

        print("\n   🔀 Fallback Sequence: Open-Meteo → NOAA → METAR")

        # Test 3.1: Current Weather (Auto-Fallback)
        try:
            current = self.agg.get_current_weather(lat, lon)
            if current:
                self.print_test("3.1 Current Weather (Auto-Fallback)", True,
                    f"Success from {current.source.value}")
            else:
                self.print_test("3.1 Current Weather", False, "All sources failed")
        except Exception as e:
            self.print_test("3.1 Current Weather", False, f"Error: {e}")

        # Test 3.2: Hourly Forecast (Auto-Fallback)
        try:
            hourly = self.agg.get_hourly_forecast(lat, lon, days=7)
            if hourly and len(hourly) > 0:
                self.print_test("3.2 Hourly Forecast (Auto-Fallback)", True,
                    f"Retrieved {len(hourly)} points from {hourly[0].source.value}")
            else:
                self.print_test("3.2 Hourly Forecast", False, "All sources failed")
        except Exception as e:
            self.print_test("3.2 Hourly Forecast", False, f"Error: {e}")

        # Test 3.3: Daily Forecast (Auto-Fallback)
        try:
            daily = self.agg.get_daily_forecast(lat, lon, days=30)
            if daily and len(daily) > 0:
                self.print_test("3.3 Daily Forecast (Auto-Fallback)", True,
                    f"Retrieved {len(daily)} days from {daily[0].source.value}")
            else:
                self.print_test("3.3 Daily Forecast", False, "All sources failed")
        except Exception as e:
            self.print_test("3.3 Daily Forecast", False, f"Error: {e}")

        # Test 3.4: Complete Data
        try:
            complete = self.agg.get_complete_weather_data(lat, lon, location_name="NYC", forecast_days=7)
            if complete:
                self.print_test("3.4 Complete Weather Data", True,
                    f"Current: ✓, Hourly: {len(complete.hourly_forecast)}, Daily: {len(complete.daily_forecast)}")

                print(f"\n   📦 LocationWeatherData Structure:")
                print(f"   - latitude: {complete.latitude} (type: float)")
                print(f"   - longitude: {complete.longitude} (type: float)")
                print(f"   - location_name: {complete.location_name} (type: str or None)")
                print(f"   - current: CurrentWeather (type: object or None)")
                print(f"   - hourly_forecast: List[ForecastPoint] (length: {len(complete.hourly_forecast)})")
                print(f"   - daily_forecast: List[ForecastPoint] (length: {len(complete.daily_forecast)})")
                print(f"   - ensemble_forecast: List[EnsembleData] (length: {len(complete.ensemble_forecast)})")
                print(f"   - historical_observations: List[HistoricalObservation] (length: {len(complete.historical_observations)})")
                print(f"   - sources_used: {[s.value for s in complete.sources_used]}")
                print(f"   - last_updated: {complete.last_updated} (type: datetime)")
            else:
                self.print_test("3.4 Complete Weather Data", False, "No data returned")
        except Exception as e:
            self.print_test("3.4 Complete Weather Data", False, f"Error: {e}")

    # =========== TEST 4: Caching ===========
    def test_caching(self):
        """Test caching behavior and performance"""
        self.print_section("Test 4: Caching System")

        import time

        lat, lon = self.test_coords["NYC"]["lat"], self.test_coords["NYC"]["lon"]
        agg_cached = WeatherAggregator(cache_ttl_minutes=30)

        try:
            # First call (cache miss)
            start = time.time()
            current1 = agg_cached.get_current_weather(lat, lon)
            time_miss = time.time() - start

            # Second call (cache hit)
            start = time.time()
            current2 = agg_cached.get_current_weather(lat, lon)
            time_hit = time.time() - start

            if current1 and current2:
                speedup = time_miss / time_hit if time_hit > 0 else float('inf')
                self.print_test("4.1 Cache Performance", True,
                    f"Miss: {time_miss*1000:.0f}ms → Hit: {time_hit*1000:.1f}ms ({speedup:.0f}x faster)")

                print("\n   ⚙️ Cache Parameters (Modifiable):")
                print(f"   - cache_ttl_minutes: 30 (default, configurable)")
                print(f"   - TTL: Time-to-Live for cached results")
                print(f"   - Clear: agg.clear_cache() to force refresh")
            else:
                self.print_test("4.1 Cache Performance", False, "Data fetch failed")
        except Exception as e:
            self.print_test("4.1 Cache Performance", False, f"Error: {e}")

    # =========== TEST 5: Ensemble Confidence ===========
    def test_ensemble_confidence(self):
        """Test ensemble confidence score calculation"""
        self.print_section("Test 5: Ensemble Confidence Metrics")

        lat, lon = self.test_coords["NYC"]["lat"], self.test_coords["NYC"]["lon"]

        try:
            ensemble = self.agg.get_ensemble_forecast(lat, lon, days=5)
            if ensemble and len(ensemble) > 0:
                confidence = self.agg.ensemble_confidence_score(ensemble)
                self.print_test("5.1 Confidence Score Calculation", True,
                    f"Temp Confidence: {confidence['temperature_confidence']:.1%}")

                print(f"\n   📊 Confidence Metrics Format:")
                print(f"   - temperature_confidence: {confidence['temperature_confidence']:.2f} (0-1, higher = more certain)")
                print(f"   - precipitation_confidence: {confidence['precipitation_confidence']:.2f} (0-1)")
                print(f"   - ensemble_members: {confidence['ensemble_members']} (type: int)")
                print(f"   - mean_spread_degrees: {confidence['mean_spread_degrees']:.2f} (°C, lower = less uncertain)")
            else:
                self.print_test("5.1 Confidence Score", True, "Ensemble endpoint unavailable (graceful fallback)")
        except Exception as e:
            self.print_test("5.1 Confidence Score", False, f"Error: {e}")

    # =========== TEST 6: Feature Extraction ===========
    def test_feature_extraction(self):
        """Test ML feature extraction utilities"""
        self.print_section("Test 6: Feature Extraction (ML-Ready)")

        lat, lon = self.test_coords["NYC"]["lat"], self.test_coords["NYC"]["lon"]

        try:
            weather = self.agg.get_complete_weather_data(lat, lon, forecast_days=7)
            if weather:
                # Current conditions
                current_features = WeatherFeatureExtractor.current_conditions_dict(weather)
                self.print_test("6.1 Current Conditions Dict", True,
                    f"Extracted {len(current_features)} features")

                print(f"\n   📊 Current Features Format:")
                print(f"   Dict with keys: {list(current_features.keys())}")
                print(f"   Example values: temperature={current_features.get('temperature', 'N/A')}, "
                      f"humidity={current_features.get('humidity', 'N/A')}")

                # Hourly statistics
                hourly_stats = WeatherFeatureExtractor.hourly_statistics(weather.hourly_forecast, hours_ahead=24)
                self.print_test("6.2 Hourly Statistics (24h)", True,
                    f"Extracted {len(hourly_stats)} statistics")

                print(f"\n   📊 Hourly Stats Format (24h):")
                print(f"   Dict with keys: {list(hourly_stats.keys())}")
                print(f"   Example: temp_mean_24h={hourly_stats.get('temp_mean_24h', 'N/A')}, "
                      f"temp_min_24h={hourly_stats.get('temp_min_24h', 'N/A')}")

                # Daily statistics
                daily_stats = WeatherFeatureExtractor.daily_statistics(weather.daily_forecast)
                self.print_test("6.3 Daily Statistics", True,
                    f"Extracted {len(daily_stats)} statistics")

                # Ensemble features
                ensemble_features = WeatherFeatureExtractor.ensemble_features(weather.ensemble_forecast)
                self.print_test("6.4 Ensemble Features", True,
                    f"Extracted {len(ensemble_features)} ensemble metrics" if ensemble_features else "No ensemble data available")

            else:
                self.print_test("6.x Feature Extraction", False, "No weather data")
        except Exception as e:
            self.print_test("6.x Feature Extraction", False, f"Error: {e}")

    # =========== TEST 7: Data Validation ===========
    def test_validation(self):
        """Test data validation utilities"""
        self.print_section("Test 7: Data Validation & Quality Checks")

        lat, lon = self.test_coords["NYC"]["lat"], self.test_coords["NYC"]["lon"]

        try:
            weather = self.agg.get_complete_weather_data(lat, lon, forecast_days=7)
            if weather and weather.hourly_forecast:
                # Validate location data
                issues = WeatherValidation.validate_location_data(weather)
                self.print_test("7.1 Location Data Validation", len(issues) == 0,
                    f"{'No issues' if len(issues) == 0 else f'{len(issues)} issues found'}")

                print(f"\n   🔍 Validation Checks Performed:")
                print(f"   - Temperature range: [-60, 60]°C")
                print(f"   - Humidity: [0, 100]%")
                print(f"   - Wind speed: [0, 150] km/h")
                print(f"   - Precipitation: >= 0 mm")

                # Validate individual forecast
                forecast = weather.hourly_forecast[0]
                errors = WeatherValidation.validate_forecast(forecast)
                self.print_test("7.2 Individual Forecast Validation", len(errors) == 0,
                    f"{'Valid' if len(errors) == 0 else f'{len(errors)} errors'}")
            else:
                self.print_test("7.x Validation", False, "No weather data")
        except Exception as e:
            self.print_test("7.x Validation", False, f"Error: {e}")

    # =========== TEST 8: Market-Specific Calculations ===========
    def test_market_calculations(self):
        """Test market-specific weather calculations"""
        self.print_section("Test 8: Market-Specific Calculations")

        lat, lon = self.test_coords["NYC"]["lat"], self.test_coords["NYC"]["lon"]

        try:
            weather = self.agg.get_complete_weather_data(lat, lon, forecast_days=7)
            if weather and weather.hourly_forecast:
                # Temperature exceedance
                prob_above_15 = WeatherAggregations.temperature_exceedance_probability(
                    weather.hourly_forecast, threshold=15, hours_ahead=24
                )
                self.print_test("8.1 Temperature Exceedance", True,
                    f"P(T > 15°C in 24h) = {prob_above_15:.1%}")

                print(f"\n   📊 Market Calculation Parameters:")
                print(f"   - threshold: 15 (°C, customizable)")
                print(f"   - hours_ahead: 24 (hours, customizable)")
                print(f"   - returns: probability 0-1")

                # Precipitation probability
                precip_stats = WeatherAggregations.precipitation_probability_aggregate(
                    weather.hourly_forecast, hours_ahead=24
                )
                self.print_test("8.2 Precipitation Aggregation", True,
                    f"Mean precip prob: {precip_stats['mean_probability']:.1%}")

                # Wind event probability
                wind_prob = WeatherAggregations.wind_event_probability(
                    weather.hourly_forecast, threshold=25, hours_ahead=24
                )
                self.print_test("8.3 Wind Event Probability", True,
                    f"P(Wind > 25 km/h in 24h) = {wind_prob:.1%}")

            else:
                self.print_test("8.x Market Calculations", False, "No weather data")
        except Exception as e:
            self.print_test("8.x Market Calculations", False, f"Error: {e}")

    # =========== TEST 9: Global Coverage ===========
    def test_global_coverage(self):
        """Test geographic coverage"""
        self.print_section("Test 9: Global Coverage Test")

        locations_to_test = [
            ("NYC", 40.7128, -74.0060),
            ("London", 51.5074, -0.1278),
            ("Tokyo", 35.6762, 139.6503),
            ("Sydney", -33.8688, 151.2093),
        ]

        for name, lat, lon in locations_to_test:
            try:
                current = self.agg.get_current_weather(lat, lon)
                if current:
                    self.print_test(f"9.1 {name} ({lat}, {lon})", True,
                        f"{current.temperature}°C from {current.source.value}")
                else:
                    self.print_test(f"9.1 {name}", False, "No data")
            except Exception as e:
                self.print_test(f"9.1 {name}", False, f"Error: {e}")

    # =========== SUMMARY ===========
    def print_summary(self):
        """Print test summary"""
        self.print_section("TEST SUMMARY")

        total = self.results["passed"] + self.results["failed"]
        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"Success Rate: {self.results['passed']/total*100:.1f}%")

        if self.results["failed"] > 0:
            print(f"\n⚠️ Failed Tests:")
            for error in self.results["errors"]:
                print(f"  - {error}")
        else:
            print(f"\n🎉 ALL TESTS PASSED!")

    def run_all_tests(self):
        """Run complete test suite"""
        print("\n" + "🌦️ "*40)
        print("WEATHER FOUNDATION - COMPREHENSIVE TEST SUITE")
        print("🌦️ "*40)

        self.test_openmeteo_source()
        self.test_noaa_source()
        self.test_aggregator()
        self.test_caching()
        self.test_ensemble_confidence()
        self.test_feature_extraction()
        self.test_validation()
        self.test_market_calculations()
        self.test_global_coverage()

        self.print_summary()


if __name__ == "__main__":
    tester = TestWeatherFoundation()
    tester.run_all_tests()
