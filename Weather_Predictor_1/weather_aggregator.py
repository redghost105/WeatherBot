"""
Weather aggregator that combines data from multiple sources with smart fallback,
caching, and validation logic.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from functools import lru_cache
import statistics

from weather_models import (
    LocationWeatherData,
    CurrentWeather,
    ForecastPoint,
    ValidationMetrics,
    WeatherSource,
    EnsembleData,
    HistoricalObservation,
)
from weather_sources import (
    OpenMeteoSource,
    NOAASource,
    METARSource,
    BaseWeatherSource,
)

logger = logging.getLogger(__name__)


class WeatherAggregator:
    """
    Coordinates multiple weather sources with intelligent fallback,
    caching, and cross-validation logic.
    """

    def __init__(self, cache_ttl_minutes: int = 30):
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self.open_meteo = OpenMeteoSource()
        self.noaa = NOAASource()
        self.metar = METARSource()
        self.cache: Dict[tuple, tuple] = {}  # (lat, lon, query_type) -> (data, timestamp)

    def _cache_key(self, latitude: float, longitude: float, query_type: str) -> tuple:
        """Create cache key"""
        return (round(latitude, 4), round(longitude, 4), query_type)

    def _get_cached(self, cache_key: tuple) -> Optional[any]:
        """Retrieve from cache if not expired"""
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            if datetime.utcnow() - timestamp < self.cache_ttl:
                logger.debug(f"Cache hit: {cache_key}")
                return data
            else:
                del self.cache[cache_key]
        return None

    def _set_cache(self, cache_key: tuple, data: any):
        """Store in cache"""
        self.cache[cache_key] = (data, datetime.utcnow())

    def get_current_weather(self, latitude: float, longitude: float,
                           sources: Optional[List[WeatherSource]] = None,
                           station_code: Optional[str] = None) -> Optional[CurrentWeather]:
        """
        Fetch current weather with intelligent fallback.
        Tries sources in order, falls back if any fail.
        """
        if sources is None:
            sources = [WeatherSource.OPEN_METEO, WeatherSource.NOAA, WeatherSource.METAR]

        cache_key = self._cache_key(latitude, longitude, "current")
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        for source in sources:
            try:
                if source == WeatherSource.OPEN_METEO:
                    current = self.open_meteo.get_current_weather(latitude, longitude)
                elif source == WeatherSource.NOAA:
                    current = self.noaa.get_current_weather(latitude, longitude)
                elif source == WeatherSource.METAR:
                    if not station_code:
                        continue
                    current = self.metar.get_current_weather(latitude, longitude, station_code)
                else:
                    continue

                if current:
                    self._set_cache(cache_key, current)
                    logger.info(f"Current weather from {source.value}")
                    return current
            except Exception as e:
                logger.warning(f"Failed to get current from {source.value}: {e}")
                continue

        logger.warning(f"All current weather sources failed for ({latitude}, {longitude})")
        return None

    def get_hourly_forecast(self, latitude: float, longitude: float,
                           days: int = 7,
                           sources: Optional[List[WeatherSource]] = None) -> List[ForecastPoint]:
        """
        Fetch hourly forecast with intelligent fallback.
        Open-Meteo is primary, NOAA as backup.
        """
        if sources is None:
            sources = [WeatherSource.OPEN_METEO, WeatherSource.NOAA]

        cache_key = self._cache_key(latitude, longitude, f"hourly_{days}")
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        for source in sources:
            try:
                if source == WeatherSource.OPEN_METEO:
                    forecasts = self.open_meteo.get_hourly_forecast(latitude, longitude, days)
                elif source == WeatherSource.NOAA:
                    forecasts = self.noaa.get_hourly_forecast(latitude, longitude, days)
                else:
                    continue

                if forecasts:
                    self._set_cache(cache_key, forecasts)
                    logger.info(f"Hourly forecast from {source.value} ({len(forecasts)} points)")
                    return forecasts
            except Exception as e:
                logger.warning(f"Failed hourly forecast from {source.value}: {e}")
                continue

        logger.warning(f"All hourly sources failed for ({latitude}, {longitude})")
        return []

    def get_daily_forecast(self, latitude: float, longitude: float,
                          days: int = 30,
                          sources: Optional[List[WeatherSource]] = None) -> List[ForecastPoint]:
        """
        Fetch daily forecast with intelligent fallback.
        Open-Meteo is primary, NOAA as backup.
        """
        if sources is None:
            sources = [WeatherSource.OPEN_METEO, WeatherSource.NOAA]

        cache_key = self._cache_key(latitude, longitude, f"daily_{days}")
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        for source in sources:
            try:
                if source == WeatherSource.OPEN_METEO:
                    forecasts = self.open_meteo.get_daily_forecast(latitude, longitude, days)
                elif source == WeatherSource.NOAA:
                    forecasts = self.noaa.get_daily_forecast(latitude, longitude, days)
                else:
                    continue

                if forecasts:
                    self._set_cache(cache_key, forecasts)
                    logger.info(f"Daily forecast from {source.value} ({len(forecasts)} points)")
                    return forecasts
            except Exception as e:
                logger.warning(f"Failed daily forecast from {source.value}: {e}")
                continue

        logger.warning(f"All daily sources failed for ({latitude}, {longitude})")
        return []

    def get_ensemble_forecast(self, latitude: float, longitude: float,
                             days: int = 7) -> List[EnsembleData]:
        """
        Fetch ensemble forecast from Open-Meteo.
        Provides confidence intervals and spread metrics.
        """
        cache_key = self._cache_key(latitude, longitude, f"ensemble_{days}")
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            ensemble = self.open_meteo.get_ensemble_forecast(latitude, longitude, days)
            if ensemble:
                self._set_cache(cache_key, ensemble)
                logger.info(f"Ensemble forecast ({len(ensemble)} points)")
            return ensemble
        except Exception as e:
            logger.warning(f"Ensemble forecast failed: {e}")
            return []

    def get_historical_observations(self, latitude: float, longitude: float,
                                   days_back: int = 7,
                                   station_code: Optional[str] = None) -> List[HistoricalObservation]:
        """
        Fetch historical observations for validation.
        Uses METAR if station code provided, otherwise returns empty.
        """
        if not station_code:
            return []

        cache_key = self._cache_key(latitude, longitude, f"historical_{days_back}")
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            observations = self.metar.get_historical_observations(
                latitude, longitude, station_code, days_back
            )
            if observations:
                self._set_cache(cache_key, observations)
                logger.info(f"Historical observations ({len(observations)} points)")
            return observations
        except Exception as e:
            logger.warning(f"Historical observations failed: {e}")
            return []

    def get_complete_weather_data(self, latitude: float, longitude: float,
                                 location_name: Optional[str] = None,
                                 forecast_days: int = 7,
                                 historical_days: int = 7,
                                 station_code: Optional[str] = None) -> Optional[LocationWeatherData]:
        """
        Fetch complete weather data from all available sources.
        This is the main entry point for getting all weather data.
        """
        data = LocationWeatherData(
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
        )

        # Current conditions
        current = self.get_current_weather(latitude, longitude, station_code=station_code)
        if current:
            data.current = current
            data.add_source(current.source)

        # Hourly forecast
        hourly = self.get_hourly_forecast(latitude, longitude, forecast_days)
        if hourly:
            data.hourly_forecast = hourly
            if hourly:
                data.add_source(hourly[0].source)

        # Daily forecast
        daily = self.get_daily_forecast(latitude, longitude, forecast_days)
        if daily:
            data.daily_forecast = daily
            if daily:
                data.add_source(daily[0].source)

        # Ensemble forecast
        ensemble = self.get_ensemble_forecast(latitude, longitude, forecast_days)
        if ensemble:
            data.ensemble_forecast = ensemble
            if ensemble:
                data.add_source(ensemble[0].source)

        # Historical observations
        historical = self.get_historical_observations(latitude, longitude, historical_days, station_code)
        if historical:
            data.historical_observations = historical
            if historical:
                data.add_source(historical[0].source)

        logger.info(f"Complete weather data retrieved for ({latitude}, {longitude})")
        logger.info(f"Sources used: {[s.value for s in data.sources_used]}")

        return data

    def validate_forecast_against_observations(self, forecasts: List[ForecastPoint],
                                               observations: List[HistoricalObservation],
                                               variable: str = "temperature") -> Optional[ValidationMetrics]:
        """
        Compare forecast data to actual observations.
        Calculates MAE, RMSE, and bias for specified variable.
        """
        if not forecasts or not observations:
            return None

        matched_pairs = []
        for forecast in forecasts:
            # Find matching observation (within 1 hour)
            for obs in observations:
                time_diff = abs((forecast.timestamp - obs.timestamp).total_seconds() / 3600)
                if time_diff < 1:
                    matched_pairs.append((forecast, obs))
                    break

        if not matched_pairs:
            logger.warning(f"No matched forecast-observation pairs for {variable}")
            return None

        forecast_values = []
        observation_values = []

        for forecast, obs in matched_pairs:
            if variable == "temperature":
                f_val = forecast.temperature
                o_val = obs.temperature
            elif variable == "wind_speed":
                f_val = forecast.wind_speed
                o_val = obs.wind_speed
            elif variable == "precipitation":
                f_val = forecast.precipitation
                o_val = obs.precipitation
            else:
                continue

            forecast_values.append(f_val)
            observation_values.append(o_val)

        if not forecast_values:
            return None

        # Calculate metrics
        errors = [abs(f - o) for f, o in zip(forecast_values, observation_values)]
        mae = statistics.mean(errors)

        squared_errors = [(f - o) ** 2 for f, o in zip(forecast_values, observation_values)]
        rmse = (statistics.mean(squared_errors)) ** 0.5

        signed_errors = [f - o for f, o in zip(forecast_values, observation_values)]
        bias = statistics.mean(signed_errors)

        return ValidationMetrics(
            mae=mae,
            rmse=rmse,
            bias=bias,
            forecast_count=len(forecasts),
            observation_count=len(observations),
            matched_count=len(matched_pairs),
            variable=variable,
            source=forecasts[0].source,
        )

    def ensemble_confidence_score(self, ensemble_data: List[EnsembleData]) -> Dict[str, float]:
        """
        Calculate confidence scores from ensemble spread.
        Lower spread = higher confidence.
        """
        if not ensemble_data:
            return {}

        # Normalize standard deviations to confidence scores (0-1, where 1 is highest confidence)
        temp_stds = [e.temperature_std for e in ensemble_data]
        precip_stds = [e.precipitation_std for e in ensemble_data]

        max_temp_std = max(temp_stds) if temp_stds else 1
        max_precip_std = max(precip_stds) if precip_stds else 1

        avg_temp_confidence = 1 - (statistics.mean(temp_stds) / max_temp_std) if max_temp_std > 0 else 0.5
        avg_precip_confidence = 1 - (statistics.mean(precip_stds) / max_precip_std) if max_precip_std > 0 else 0.5

        return {
            "temperature_confidence": max(0, min(1, avg_temp_confidence)),
            "precipitation_confidence": max(0, min(1, avg_precip_confidence)),
            "ensemble_members": ensemble_data[0].ensemble_members if ensemble_data else 0,
            "mean_spread_degrees": statistics.mean(temp_stds),
        }

    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
        logger.info("Weather cache cleared")
