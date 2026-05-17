# Polymarket Weather Data Foundation

Complete weather data aggregation system for Kalshi prediction bot, pulling from 6+ sources with intelligent fallback, caching, ensemble confidence metrics, and forecast validation.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   WeatherAggregator                          │
│              (Main Entry Point - Smart Fallback)             │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   OpenMeteoSource    NOAASource      METARSource
   (Backbone)      (NWS Fallback)   (Observations)
   
        Current ▶ 
        Hourly  ▶─── Normalized Data Models ───► LocationWeatherData
        Daily   ▶     (CurrentWeather,           (Combined Results)
        Ensemble▶     ForecastPoint,
        Hist.   ▶     EnsembleData, etc.)
        
        Optional: Validation Metrics, Confidence Scores
```

## Features

### ✅ Real-Time Current Conditions
- Temperature, humidity, dew point, pressure
- Wind speed, direction, gusts
- Cloud cover, visibility
- Precipitation and weather descriptions
- Sources: Open-Meteo, NOAA/NWS, METAR

### ✅ Hourly Forecasts (7 Days)
- 1-hourly resolution for precise prediction markets
- Temperature, humidity, precipitation probability
- Wind metrics, cloud cover, visibility
- Consistent across all sources via normalization

### ✅ Daily Forecasts (30 Days)
- High/low temperatures, daily precipitation
- Weather codes and descriptions
- Extended outlook for seasonal trading

### ✅ Ensemble/Confidence Data
- Multi-member ensemble forecasts
- Temperature and precipitation spreads (standard deviation)
- Confidence scores derived from ensemble agreement
- Identifies high-uncertainty periods

### ✅ Historical Validation
- Compare forecasts to actual observations (METAR)
- Calculate MAE, RMSE, bias for model accuracy
- Validate predictions post-resolution

### ✅ Intelligent Features
- **Fallback Logic**: Tries Open-Meteo → NOAA → METAR automatically
- **Smart Caching**: Configurable TTL (default 30 min) to reduce API calls
- **Coordinate Flexibility**: Works with any lat/lon globally
- **Extensible**: Easy to add more sources (ECMWF, Wethr.net, DEMFI)

## Data Models

All data is normalized into these unified models:

### `LocationWeatherData`
Complete weather package for a location:
```python
data = agg.get_complete_weather_data(
    latitude=40.7128,
    longitude=-74.0060,
    location_name="New York City",
    forecast_days=7,
    historical_days=7,
    station_code="KJFK"  # Optional for METAR
)

# Access results:
data.current              # CurrentWeather object
data.hourly_forecast      # List[ForecastPoint] - 1-hourly
data.daily_forecast       # List[ForecastPoint] - daily
data.ensemble_forecast    # List[EnsembleData] - ensemble spreads
data.historical_observations  # List[HistoricalObservation] - actual obs
data.sources_used         # List[WeatherSource] - which sources were used
```

### `CurrentWeather`
Single point in time snapshot:
```python
current.timestamp              # datetime
current.temperature            # float (°C)
current.temperature_2m         # float (standard 2m height)
current.feels_like            # float (°C)
current.humidity              # float (0-100%)
current.dew_point             # float (°C)
current.wind_speed            # float (km/h)
current.wind_direction        # int (0-360°)
current.wind_gust             # float (km/h)
current.precipitation         # float (mm)
current.precipitation_probability  # float (0-100%)
current.weather_code          # int (WMO code)
current.weather_description   # str
current.cloud_cover           # float (0-100%)
current.visibility            # float (km)
current.pressure              # float (hPa)
current.source                # WeatherSource enum
```

### `ForecastPoint`
Single forecast time point (hourly or daily):
```python
forecast.timestamp            # datetime
forecast.temperature          # float (°C) - mean for daily
forecast.temperature_min      # float (°C)
forecast.temperature_max      # float (°C)
forecast.precipitation        # float (mm)
forecast.precipitation_probability  # float (0-100%)
forecast.wind_speed           # float (km/h)
forecast.source               # WeatherSource enum
# ... and many more fields
```

### `EnsembleData`
Ensemble forecast with confidence metrics:
```python
ensemble.timestamp                # datetime
ensemble.ensemble_members         # int (number of members)
ensemble.temperature_mean         # float (°C)
ensemble.temperature_std          # float (°C) - spread
ensemble.temperature_min/max      # float (°C)
ensemble.precipitation_mean       # float (mm)
ensemble.precipitation_std        # float (mm) - spread
ensemble.precipitation_probability # float (0-100%)
ensemble.weather_codes            # Dict[int, float] (code -> prob)
```

### `ValidationMetrics`
Forecast accuracy against observations:
```python
metrics.mae                   # Mean Absolute Error
metrics.rmse                  # Root Mean Square Error
metrics.bias                  # Mean signed error
metrics.matched_count         # How many pairs matched
metrics.variable              # "temperature", "wind_speed", etc.
```

## Installation

```bash
pip install -r requirements_weather.txt
```

Dependencies:
- `requests` - HTTP client
- `openmeteo-requests` - Open-Meteo specific client
- `python-dotenv` - Environment variables

## Quick Start

### Basic Usage

```python
from weather_aggregator import WeatherAggregator

# Initialize
agg = WeatherAggregator(cache_ttl_minutes=30)

# Get current weather (auto-fallback across sources)
current = agg.get_current_weather(latitude=40.7128, longitude=-74.0060)
print(f"Temperature: {current.temperature}°C")
print(f"Wind: {current.wind_speed} km/h")
print(f"Source: {current.source.value}")

# Get hourly forecast
hourly = agg.get_hourly_forecast(40.7128, -74.0060, days=7)
for point in hourly[:24]:
    print(f"{point.timestamp} - {point.temperature}°C, precip: {point.precipitation_probability}%")

# Get daily forecast
daily = agg.get_daily_forecast(40.7128, -74.0060, days=30)
for point in daily[:7]:
    print(f"{point.timestamp.date()} - High: {point.temperature_max}°C, Low: {point.temperature_min}°C")

# Get complete data from all sources
complete = agg.get_complete_weather_data(
    latitude=40.7128,
    longitude=-74.0060,
    location_name="New York City",
    forecast_days=7,
    historical_days=7,
    station_code="KJFK"
)
print(f"Sources used: {[s.value for s in complete.sources_used]}")
```

### Ensemble Confidence Scores

```python
# Get ensemble forecast
ensemble = agg.get_ensemble_forecast(lat, lon, days=5)

# Calculate confidence metrics
confidence = agg.ensemble_confidence_score(ensemble)
print(f"Temperature confidence: {confidence['temperature_confidence']:.1%}")
print(f"Precipitation confidence: {confidence['precipitation_confidence']:.1%}")
print(f"Mean spread: ±{confidence['mean_spread_degrees']:.2f}°C")

# Lower spread = higher confidence
for ens in ensemble:
    print(f"{ens.timestamp}: {ens.temperature_mean:.1f}°C ± {ens.temperature_std:.1f}°C")
```

### Forecast Validation

```python
# Get forecast and historical observations
hourly_forecast = agg.get_hourly_forecast(lat, lon, days=7)
observations = agg.get_historical_observations(
    lat, lon, 
    days_back=7,
    station_code="KJFK"  # Required for METAR data
)

# Validate temperature predictions
metrics = agg.validate_forecast_against_observations(
    hourly_forecast,
    observations,
    variable="temperature"
)

print(f"MAE: {metrics.mae:.2f}°C")
print(f"RMSE: {metrics.rmse:.2f}°C")
print(f"Bias: {metrics.bias:+.2f}°C")
print(f"Accuracy (paired): {metrics.matched_count}/{metrics.forecast_count}")
```

### Custom Source Priority

```python
from weather_models import WeatherSource

# Specify source priority
sources = [
    WeatherSource.OPEN_METEO,
    WeatherSource.NOAA,
    WeatherSource.METAR
]

current = agg.get_current_weather(
    latitude=40.7128,
    longitude=-74.0060,
    sources=sources
)
```

### Caching Control

```python
# Initialize with custom TTL
agg = WeatherAggregator(cache_ttl_minutes=60)

# Clear cache when needed
agg.clear_cache()

# Cache is automatic - same coordinates within TTL use cached results
```

## Weather Sources

### Open-Meteo (Recommended Backbone)
- **URL**: https://api.open-meteo.com/v1/forecast
- **Key Features**: 
  - No API key required
  - Excellent ensemble forecasts (experimental)
  - 16-day hourly, 90-day daily
  - Multiple weather models integrated
  - Bias correction available
- **Response Time**: ~200-500ms
- **Used For**: Primary source for all forecast types

### NOAA / National Weather Service
- **URL**: https://api.weather.gov
- **Key Features**:
  - US-focused, high resolution for NWS grid points
  - Kalshi resolution (matches market definitions)
  - 7-day hourly, 7-day daily
  - Free, no API key
- **Response Time**: ~300-800ms
- **Used For**: Fallback current conditions, hourly forecasts

### METAR (Aviation Weather)
- **URL**: https://aviationweather.gov/api/data/metar
- **Key Features**:
  - Real-time observations from airports
  - Requires METAR station code (e.g., KJFK, KLAX)
  - Historical observations for validation
  - No forecasting - observations only
- **Response Time**: ~200-400ms
- **Used For**: Historical validation, current conditions at airports

### ECMWF & Other Models
- Available through Open-Meteo integration
- Not directly exposed (use Open-Meteo wrapper)

## Extending the Foundation

### Add a New Weather Source

```python
from weather_sources import BaseWeatherSource
from weather_models import CurrentWeather, ForecastPoint, WeatherSource

class MyWeatherSource(BaseWeatherSource):
    BASE_URL = "https://api.example.com"
    
    def get_current_weather(self, latitude, longitude):
        # Implement custom logic
        # Return CurrentWeather object
        pass
    
    def get_hourly_forecast(self, latitude, longitude, days=7):
        # Return List[ForecastPoint]
        pass
    
    def get_daily_forecast(self, latitude, longitude, days=30):
        # Return List[ForecastPoint]
        pass
```

Then integrate into aggregator:

```python
# Add to weather_aggregator.py get_current_weather(), etc.
my_source = MyWeatherSource()
```

## METAR Station Codes

Common US stations:
- **KJFK** - New York (JFK)
- **KLGA** - New York (LaGuardia)
- **KEWR** - Newark
- **KLAX** - Los Angeles
- **KORD** - Chicago
- **KDFW** - Dallas-Fort Worth
- **KIAH** - Houston

Find more: https://www.airnav.com/ (search airport)

## Performance Notes

- **API Calls**: Open-Meteo is primary; fallback only if it fails
- **Cache**: Default 30-min TTL prevents excessive API calls
- **Timeout**: 10-second default per request
- **Rate Limits**: Open-Meteo free tier ~10,000/day; NOAA unlimited; METAR unlimited
- **Parallel Requests**: Can fetch multiple locations simultaneously

## Integration with Prediction Bot

This foundation feeds into your Kalshi bot:

```python
from weather_aggregator import WeatherAggregator

agg = WeatherAggregator()

# For each market location:
market_lat, market_lon = 40.7128, -74.0060

# Get prediction inputs
weather_data = agg.get_complete_weather_data(market_lat, market_lon)

# Extract features for your ML model
current_temp = weather_data.current.temperature
forecast_temps = [p.temperature for p in weather_data.hourly_forecast[:24]]
ensemble_confidence = agg.ensemble_confidence_score(weather_data.ensemble_forecast)

# Feed into your prediction model
prediction = model.predict(current_temp, forecast_temps, ensemble_confidence)
```

## Future Enhancements

- [ ] Wethr.net integration for market-specific views
- [ ] DEMFI Weather feed (X/@DEMFI_Weather)
- [ ] SQLite storage of predictions + observations
- [ ] Kalshi API integration for market metadata
- [ ] Multi-location batch processing
- [ ] Real-time alert system for extreme forecasts
- [ ] Advanced ensemble post-processing (quantile mapping)

## Troubleshooting

**Getting 404 on NOAA?**
- NOAA only covers US. Use Open-Meteo for global coverage.

**No ensemble data?**
- Ensemble endpoint is experimental. Falls back gracefully.

**METAR validation not working?**
- Need valid station code. Check: https://www.airnav.com/
- Data only goes back ~48 hours typically.

**Cache not clearing?**
- Call `agg.clear_cache()` explicitly

## License & Attribution

- Open-Meteo: https://open-meteo.com (Attribution not required for non-commercial)
- NOAA: Public domain
- METAR: Public domain

---

**Status**: Production-ready foundation
**Last Updated**: May 16, 2026
**Next Task**: Integrate with Kalshi bot for live predictions
