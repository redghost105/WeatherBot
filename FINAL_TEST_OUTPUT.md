2026-05-18 23:15:41,409 - weather_aggregator - INFO - Current weather from open_meteo
2026-05-18 23:15:41,586 - weather_aggregator - INFO - Hourly forecast from open_meteo (168 points)
2026-05-18 23:15:41,763 - weather_aggregator - INFO - Daily forecast from open_meteo (7 points)
2026-05-18 23:15:41,941 - weather_aggregator - INFO - Daily forecast from open_meteo (7 points)
2026-05-18 23:15:42,119 - weather_aggregator - INFO - Ensemble forecast (7 points)
2026-05-18 23:15:42,119 - weather_aggregator - INFO - Complete weather data retrieved for (40.7128, -74.006)
2026-05-18 23:15:42,119 - weather_aggregator - INFO - Sources used: ['open_meteo']
2026-05-18 23:15:42,869 - weather_aggregator - INFO - Current weather from open_meteo
2026-05-18 23:15:43,171 - weather_aggregator - INFO - Ensemble forecast (5 points)
2026-05-18 23:15:43,172 - weather_aggregator - INFO - Complete weather data retrieved for (40.7128, -74.006)
2026-05-18 23:15:43,172 - weather_aggregator - INFO - Sources used: ['open_meteo']
2026-05-18 23:15:43,173 - weather_aggregator - INFO - Complete weather data retrieved for (40.7128, -74.006)
2026-05-18 23:15:43,173 - weather_aggregator - INFO - Sources used: ['open_meteo']
2026-05-18 23:15:43,173 - weather_aggregator - INFO - Complete weather data retrieved for (40.7128, -74.006)
2026-05-18 23:15:43,173 - weather_aggregator - INFO - Sources used: ['open_meteo']
2026-05-18 23:15:43,346 - weather_aggregator - INFO - Current weather from open_meteo
2026-05-18 23:15:43,521 - weather_aggregator - INFO - Current weather from open_meteo

🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 
WEATHER FOUNDATION - COMPREHENSIVE TEST SUITE
🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 🌦️ 

================================================================================
🧪 Test 1: Open-Meteo Source
================================================================================
✅ 1.1 Current Weather
   Temp: 22.7°C, Source: open_meteo

   📊 CurrentWeather Format:
   - timestamp: 2026-05-19 02:15:00 (type: datetime)
   - temperature: 22.7 (type: float, °C)
   - temperature_2m: 22.7 (type: float, °C at 2m height)
   - feels_like: 22.9 (type: float or None, °C)
   - humidity: 66 (type: float or None, 0-100%)
   - dew_point: None (type: float or None, °C)
   - wind_speed: 12.7 (type: float, km/h)
   - wind_direction: 205 (type: int or None, 0-360°)
   - wind_gust: 24.5 (type: float or None, km/h)
   - precipitation: 0.0 (type: float, mm)
   - precipitation_probability: None (type: float or None, 0-100%)
   - weather_code: 0 (type: int or None, WMO code)
   - weather_description: None (type: str or None)
   - cloud_cover: 0 (type: float or None, 0-100%)
   - visibility: 24200.0 (type: float or None, km)
   - pressure: 1018.9 (type: float or None, hPa)
   - source: open_meteo (type: WeatherSource enum)
✅ 1.2 Hourly Forecast (7 days)
   Retrieved 168 hourly points

   📊 ForecastPoint Format (Hourly):
   - timestamp: 2026-05-19 00:00:00 (type: datetime)
   - temperature: 24.8 (type: float, °C)
   - humidity: 56 (type: float or None, %)
   - wind_speed: 12.1 (type: float, km/h)
   - precipitation: 0.0 (type: float, mm)
   - precipitation_probability: 1 (type: float or None, %)
   - cloud_cover: 0 (type: float or None, %)
   - pressure: 1019.8 (type: float or None, hPa)
   Sample: 2026-05-19 00:00:00 - 24.8°C, 1% precip
✅ 1.3 Daily Forecast (30 days)
   Retrieved 7 daily points

   📊 ForecastPoint Format (Daily):
   - timestamp: 2026-05-19 00:00:00 (type: datetime, date)
   - temperature: 29.0 (type: float, °C, mean)
   - temperature_max: 36.4 (type: float, °C)
   - temperature_min: 21.6 (type: float, °C)
   - precipitation: 0.0 (type: float, mm daily total)
   - precipitation_probability: 8 (type: float or None, %)
   Sample: 2026-05-19 - High: 36.4°C, Low: 21.6°C
✅ 1.4 Ensemble Forecast
   Retrieved 5 ensemble points

   📊 EnsembleData Format:
   - timestamp: 2026-05-19 00:00:00 (type: datetime)
   - ensemble_members: 24 (type: int, number of models)
   - temperature_mean: 28.8625 (type: float, °C)
   - temperature_std: 5.476893160876171 (type: float, °C, standard deviation)
   - temperature_min: 21.6 (type: float, °C, across members)
   - temperature_max: 36.4 (type: float, °C, across members)
   - precipitation_mean: 0.0 (type: float, mm)
   - precipitation_std: 0.0 (type: float, mm, spread)
   Sample: 2026-05-19 00:00:00 - 28.9°C ± 5.5°C

================================================================================
🧪 Test 2: NOAA/NWS Source
================================================================================
✅ 2.1 Current Weather
   Temp: 21.11111111111111°C, Source: noaa
✅ 2.2 Hourly Forecast
   Retrieved 156 hourly points
✅ 2.3 Daily Forecast
   Retrieved 7 daily points

================================================================================
🧪 Test 3: Weather Aggregator (Fallback Logic)
================================================================================

   🔀 Fallback Sequence: Open-Meteo → NOAA → METAR
✅ 3.1 Current Weather (Auto-Fallback)
   Success from open_meteo
✅ 3.2 Hourly Forecast (Auto-Fallback)
   Retrieved 168 points from open_meteo
✅ 3.3 Daily Forecast (Auto-Fallback)
   Retrieved 7 days from open_meteo
✅ 3.4 Complete Weather Data
   Current: ✓, Hourly: 168, Daily: 7

   📦 LocationWeatherData Structure:
   - latitude: 40.7128 (type: float)
   - longitude: -74.006 (type: float)
   - location_name: NYC (type: str or None)
   - current: CurrentWeather (type: object or None)
   - hourly_forecast: List[ForecastPoint] (length: 168)
   - daily_forecast: List[ForecastPoint] (length: 7)
   - ensemble_forecast: List[EnsembleData] (length: 7)
   - historical_observations: List[HistoricalObservation] (length: 0)
   - sources_used: ['open_meteo']
   - last_updated: 2026-05-19 06:15:41.763957 (type: datetime)

================================================================================
🧪 Test 4: Caching System
================================================================================
✅ 4.1 Cache Performance
   Miss: 750ms → Hit: 0.1ms (13448x faster)

   ⚙️ Cache Parameters (Modifiable):
   - cache_ttl_minutes: 30 (default, configurable)
   - TTL: Time-to-Live for cached results
   - Clear: agg.clear_cache() to force refresh

================================================================================
🧪 Test 5: Ensemble Confidence Metrics
================================================================================
✅ 5.1 Confidence Score Calculation
   Temp Confidence: 49.0%

   📊 Confidence Metrics Format:
   - temperature_confidence: 0.49 (0-1, higher = more certain)
   - precipitation_confidence: 0.68 (0-1)
   - ensemble_members: 24 (type: int)
   - mean_spread_degrees: 3.07 (°C, lower = less uncertain)

================================================================================
🧪 Test 6: Feature Extraction (ML-Ready)
================================================================================
✅ 6.1 Current Conditions Dict
   Extracted 13 features

   📊 Current Features Format:
   Dict with keys: ['temperature', 'temperature_2m', 'feels_like', 'humidity', 'dew_point', 'wind_speed', 'wind_direction', 'wind_gust', 'precipitation', 'precipitation_probability', 'cloud_cover', 'visibility', 'pressure']
   Example values: temperature=22.7, humidity=66
✅ 6.2 Hourly Statistics (24h)
   Extracted 7 statistics

   📊 Hourly Stats Format (24h):
   Dict with keys: ['temp_mean_24h', 'temp_min_24h', 'temp_max_24h', 'temp_stdev_24h', 'wind_mean_24h', 'wind_max_24h', 'precip_prob_mean_24h']
   Example: temp_mean_24h=27.65806451612903, temp_min_24h=21.6
✅ 6.3 Daily Statistics
   Extracted 34 statistics
✅ 6.4 Ensemble Features
   Extracted 5 ensemble metrics

================================================================================
🧪 Test 7: Data Validation & Quality Checks
================================================================================
✅ 7.1 Location Data Validation
   No issues

   🔍 Validation Checks Performed:
   - Temperature range: [-60, 60]°C
   - Humidity: [0, 100]%
   - Wind speed: [0, 150] km/h
   - Precipitation: >= 0 mm
✅ 7.2 Individual Forecast Validation
   Valid

================================================================================
🧪 Test 8: Market-Specific Calculations
================================================================================
✅ 8.1 Temperature Exceedance
   P(T > 15°C in 24h) = 100.0%

   📊 Market Calculation Parameters:
   - threshold: 15 (°C, customizable)
   - hours_ahead: 24 (hours, customizable)
   - returns: probability 0-1
✅ 8.2 Precipitation Aggregation
   Mean precip prob: 263.3%
✅ 8.3 Wind Event Probability
   P(Wind > 25 km/h in 24h) = 3.2%

================================================================================
🧪 Test 9: Global Coverage Test
================================================================================
✅ 9.1 NYC (40.7128, -74.006)
   22.7°C from open_meteo
✅ 9.1 London (51.5074, -0.1278)
   11.4°C from open_meteo
✅ 9.1 Tokyo (35.6762, 139.6503)
   26.0°C from open_meteo2026-05-18 23:15:43,694 - weather_aggregator - INFO - Current weather from open_meteo

✅ 9.1 Sydney (-33.8688, 151.2093)
   17.4°C from open_meteo

================================================================================
🧪 TEST SUMMARY
================================================================================

Total Tests: 26
✅ Passed: 26
❌ Failed: 0
Success Rate: 100.0%

🎉 ALL TESTS PASSED!
