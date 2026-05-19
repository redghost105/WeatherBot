"""
Individual weather source adapters for Open-Meteo, NOAA, METAR, and others.
Each source is wrapped in a consistent interface that returns normalized LocationWeatherData.
"""
import requests
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from urllib.parse import urlencode

from weather_models import (
    CurrentWeather,
    ForecastPoint,
    EnsembleData,
    HistoricalObservation,
    LocationWeatherData,
    WeatherSource,
)

logger = logging.getLogger(__name__)


class BaseWeatherSource(ABC):
    """Abstract base class for all weather sources"""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Polymarket-Weather-Bot/1.0 (+https://github.com/polymarket/weather-bot)'
        })

    @abstractmethod
    def get_current_weather(self, latitude: float, longitude: float) -> Optional[CurrentWeather]:
        """Fetch real-time current conditions"""
        pass

    @abstractmethod
    def get_hourly_forecast(self, latitude: float, longitude: float, days: int = 7) -> List[ForecastPoint]:
        """Fetch hourly forecast"""
        pass

    @abstractmethod
    def get_daily_forecast(self, latitude: float, longitude: float, days: int = 30) -> List[ForecastPoint]:
        """Fetch daily forecast"""
        pass

    def get_ensemble_forecast(self, latitude: float, longitude: float, days: int = 7) -> List[EnsembleData]:
        """Fetch ensemble forecast (optional, returns empty if not supported)"""
        return []

    def get_historical_observations(self, latitude: float, longitude: float,
                                   days_back: int = 7) -> List[HistoricalObservation]:
        """Fetch historical observations (optional, returns empty if not supported)"""
        return []

    def get_complete_data(self, latitude: float, longitude: float,
                         location_name: Optional[str] = None,
                         forecast_days: int = 7,
                         historical_days: int = 7) -> Optional[LocationWeatherData]:
        """Fetch all available data for a location"""
        try:
            data = LocationWeatherData(
                latitude=latitude,
                longitude=longitude,
                location_name=location_name,
            )

            current = self.get_current_weather(latitude, longitude)
            if current:
                data.current = current
                data.add_source(current.source)

            hourly = self.get_hourly_forecast(latitude, longitude, forecast_days)
            if hourly:
                data.hourly_forecast = hourly
                if hourly:
                    data.add_source(hourly[0].source)

            daily = self.get_daily_forecast(latitude, longitude, forecast_days)
            if daily:
                data.daily_forecast = daily
                if daily:
                    data.add_source(daily[0].source)

            ensemble = self.get_ensemble_forecast(latitude, longitude, forecast_days)
            if ensemble:
                data.ensemble_forecast = ensemble
                if ensemble:
                    data.add_source(ensemble[0].source)

            historical = self.get_historical_observations(latitude, longitude, historical_days)
            if historical:
                data.historical_observations = historical
                if historical:
                    data.add_source(historical[0].source)

            return data
        except Exception as e:
            logger.error(f"Error fetching complete data: {e}")
            return None


class OpenMeteoSource(BaseWeatherSource):
    """Open-Meteo API - Recommended backbone for all data"""
    BASE_URL = "https://api.open-meteo.com/v1"

    def get_current_weather(self, latitude: float, longitude: float) -> Optional[CurrentWeather]:
        """Fetch current weather from Open-Meteo"""
        try:
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'current': 'temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m,cloud_cover,pressure_msl,visibility',
                'timezone': 'auto',
            }
            response = self.session.get(f"{self.BASE_URL}/forecast", params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if 'current' not in data:
                return None

            current = data['current']
            return CurrentWeather(
                timestamp=datetime.fromisoformat(current['time']),
                temperature=current.get('temperature_2m', 0),
                temperature_2m=current.get('temperature_2m', 0),
                feels_like=current.get('apparent_temperature'),
                humidity=current.get('relative_humidity_2m'),
                wind_speed=current.get('wind_speed_10m', 0),
                wind_direction=current.get('wind_direction_10m'),
                wind_gust=current.get('wind_gusts_10m'),
                precipitation=current.get('precipitation', 0),
                weather_code=current.get('weather_code'),
                cloud_cover=current.get('cloud_cover'),
                visibility=current.get('visibility'),
                pressure=current.get('pressure_msl'),
                source=WeatherSource.OPEN_METEO,
                raw_data=current,
            )
        except Exception as e:
            logger.error(f"Open-Meteo current weather error: {e}")
            return None

    def get_hourly_forecast(self, latitude: float, longitude: float, days: int = 7) -> List[ForecastPoint]:
        """Fetch hourly forecast from Open-Meteo"""
        try:
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'hourly': 'temperature_2m,relative_humidity_2m,dew_point_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m,cloud_cover,visibility,pressure_msl',
                'timezone': 'auto',
                'forecast_days': min(days, 16),  # Open-Meteo limit
            }
            response = self.session.get(f"{self.BASE_URL}/forecast", params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if 'hourly' not in data:
                return []

            hourly = data['hourly']
            forecasts = []
            for i, timestamp_str in enumerate(hourly['time']):
                forecast = ForecastPoint(
                    timestamp=datetime.fromisoformat(timestamp_str),
                    temperature=hourly['temperature_2m'][i],
                    humidity=hourly.get('relative_humidity_2m', [None])[i],
                    dew_point=hourly.get('dew_point_2m', [None])[i],
                    precipitation_probability=hourly.get('precipitation_probability', [None])[i],
                    precipitation=hourly.get('precipitation', [0])[i],
                    weather_code=hourly.get('weather_code', [None])[i],
                    wind_speed=hourly.get('wind_speed_10m', [0])[i],
                    wind_direction=hourly.get('wind_direction_10m', [None])[i],
                    wind_gust=hourly.get('wind_gusts_10m', [None])[i],
                    cloud_cover=hourly.get('cloud_cover', [None])[i],
                    visibility=hourly.get('visibility', [None])[i],
                    pressure=hourly.get('pressure_msl', [None])[i],
                    source=WeatherSource.OPEN_METEO,
                    raw_data={'index': i},
                )
                forecasts.append(forecast)
            return forecasts
        except Exception as e:
            logger.error(f"Open-Meteo hourly forecast error: {e}")
            return []

    def get_daily_forecast(self, latitude: float, longitude: float, days: int = 30) -> List[ForecastPoint]:
        """Fetch daily forecast from Open-Meteo"""
        try:
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code,wind_speed_10m_max,wind_direction_10m_dominant,wind_gusts_10m_max,cloud_cover_mean',
                'temperature_unit': 'celsius',
                'timezone': 'auto',
            }
            response = self.session.get(f"{self.BASE_URL}/forecast", params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if 'daily' not in data:
                return []

            daily = data['daily']
            forecasts = []
            for i, timestamp_str in enumerate(daily['time']):
                temp_max = daily['temperature_2m_max'][i]
                temp_min = daily['temperature_2m_min'][i]
                forecast = ForecastPoint(
                    timestamp=datetime.fromisoformat(timestamp_str),
                    temperature=(temp_max + temp_min) / 2,
                    temperature_max=temp_max,
                    temperature_min=temp_min,
                    precipitation=daily.get('precipitation_sum', [0])[i],
                    precipitation_probability=daily.get('precipitation_probability_max', [None])[i],
                    weather_code=daily.get('weather_code', [None])[i],
                    wind_speed=daily.get('wind_speed_10m_max', [0])[i],
                    wind_direction=daily.get('wind_direction_10m_dominant', [None])[i],
                    wind_gust=daily.get('wind_gusts_10m_max', [None])[i],
                    cloud_cover=daily.get('cloud_cover_mean', [None])[i],
                    source=WeatherSource.OPEN_METEO,
                    raw_data={'index': i},
                )
                forecasts.append(forecast)
            return forecasts
        except Exception as e:
            logger.error(f"Open-Meteo daily forecast error: {e}")
            return []

    def get_ensemble_forecast(self, latitude: float, longitude: float, days: int = 7) -> List[EnsembleData]:
        """Fetch ensemble forecast from Open-Meteo using GFS ensemble"""
        try:
            import statistics

            params = {
                'latitude': latitude,
                'longitude': longitude,
                'hourly': 'temperature_2m,wind_speed_10m,precipitation',
                'models': 'gfs_seamless',
                'timezone': 'auto',
                'forecast_days': min(days, 10),
            }
            response = self.session.get(f"{self.BASE_URL}/forecast", params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if 'hourly' not in data:
                return []

            hourly = data['hourly']
            ensembles = []

            # Get time and data arrays
            times = hourly.get('time', [])
            temps = hourly.get('temperature_2m', [])
            winds = hourly.get('wind_speed_10m', [])
            precips = hourly.get('precipitation', [])

            # Create daily aggregates from hourly data
            for day_idx in range(min(len(times) // 24, days)):
                start_idx = day_idx * 24
                end_idx = start_idx + 24

                if start_idx >= len(times):
                    break

                day_temps = [t for t in temps[start_idx:end_idx] if t is not None]
                day_winds = [w for w in winds[start_idx:end_idx] if w is not None]
                day_precips = [p for p in precips[start_idx:end_idx] if p is not None]

                if not day_temps:
                    continue

                ensemble = EnsembleData(
                    timestamp=datetime.fromisoformat(times[start_idx]),
                    ensemble_members=len(day_temps),
                    temperature_mean=statistics.mean(day_temps),
                    temperature_std=statistics.stdev(day_temps) if len(day_temps) > 1 else 0,
                    temperature_min=min(day_temps),
                    temperature_max=max(day_temps),
                    wind_speed_mean=statistics.mean(day_winds) if day_winds else 0,
                    wind_speed_std=statistics.stdev(day_winds) if len(day_winds) > 1 else 0,
                    precipitation_mean=statistics.mean(day_precips) if day_precips else 0,
                    precipitation_std=statistics.stdev(day_precips) if len(day_precips) > 1 else 0,
                    source=WeatherSource.OPEN_METEO,
                    raw_data={'day_index': day_idx},
                )
                ensembles.append(ensemble)

            return ensembles
        except Exception as e:
            logger.error(f"Open-Meteo ensemble forecast error: {e}")
            return []


class NOAASource(BaseWeatherSource):
    """NOAA/National Weather Service API - Kalshi resolution"""
    BASE_URL = "https://api.weather.gov"

    def _get_grid_point(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """Get grid point metadata for coordinates"""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/points/{latitude},{longitude}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"NOAA grid point lookup error: {e}")
            return None

    def get_current_weather(self, latitude: float, longitude: float) -> Optional[CurrentWeather]:
        """Fetch current weather from NOAA/NWS"""
        try:
            grid = self._get_grid_point(latitude, longitude)
            if not grid or 'properties' not in grid:
                return None

            properties = grid['properties']
            forecast_url = properties.get('forecast')
            if not forecast_url:
                return None

            response = self.session.get(forecast_url, timeout=self.timeout)
            response.raise_for_status()
            forecast = response.json()

            if 'properties' not in forecast or not forecast['properties'].get('periods'):
                return None

            period = forecast['properties']['periods'][0]
            # NOAA returns temperature in Fahrenheit; convert to Celsius
            temp_f = float(period.get('temperature', 0))
            temp_c = (temp_f - 32) * 5/9
            return CurrentWeather(
                timestamp=datetime.fromisoformat(period['startTime']),
                temperature=temp_c,
                temperature_2m=temp_c,
                weather_description=period.get('shortForecast'),
                wind_speed=self._parse_wind_speed(period.get('windSpeed', '0 mph')),
                wind_direction=self._wind_to_degrees(period.get('windDirection', 'N')),
                source=WeatherSource.NOAA,
                raw_data=period,
            )
        except Exception as e:
            logger.error(f"NOAA current weather error: {e}")
            return None

    def get_hourly_forecast(self, latitude: float, longitude: float, days: int = 7) -> List[ForecastPoint]:
        """Fetch hourly forecast from NOAA"""
        try:
            from datetime import timezone as tz

            grid = self._get_grid_point(latitude, longitude)
            if not grid or 'properties' not in grid:
                return []

            properties = grid['properties']
            hourly_url = properties.get('forecastHourly')
            if not hourly_url:
                return []

            response = self.session.get(hourly_url, timeout=self.timeout)
            response.raise_for_status()
            forecast = response.json()

            if 'properties' not in forecast or not forecast['properties'].get('periods'):
                return []

            forecasts = []
            cutoff_time = datetime.now(tz.utc) + timedelta(days=days)
            for period in forecast['properties']['periods'][:24 * days]:
                start_time = datetime.fromisoformat(period['startTime'])
                if start_time > cutoff_time:
                    break

                # Convert NOAA temperature from Fahrenheit to Celsius
                temp_f = float(period.get('temperature', 0))
                temp_c = (temp_f - 32) * 5/9
                forecast_obj = ForecastPoint(
                    timestamp=start_time,
                    temperature=temp_c,
                    weather_description=period.get('shortForecast'),
                    wind_speed=self._parse_wind_speed(period.get('windSpeed', '0 mph')),
                    wind_direction=self._wind_to_degrees(period.get('windDirection', 'N')),
                    precipitation_probability=float(period.get('probabilityOfPrecipitation', {}).get('value', 0)) if isinstance(period.get('probabilityOfPrecipitation'), dict) else 0,
                    source=WeatherSource.NOAA,
                    raw_data=period,
                )
                forecasts.append(forecast_obj)

            return forecasts
        except Exception as e:
            logger.error(f"NOAA hourly forecast error: {e}")
            return []

    def get_daily_forecast(self, latitude: float, longitude: float, days: int = 30) -> List[ForecastPoint]:
        """Fetch daily forecast from NOAA"""
        try:
            from datetime import timezone as tz

            grid = self._get_grid_point(latitude, longitude)
            if not grid or 'properties' not in grid:
                return []

            properties = grid['properties']
            forecast_url = properties.get('forecast')
            if not forecast_url:
                return []

            response = self.session.get(forecast_url, timeout=self.timeout)
            response.raise_for_status()
            forecast = response.json()

            if 'properties' not in forecast or not forecast['properties'].get('periods'):
                return []

            forecasts = []
            cutoff_time = datetime.now(tz.utc) + timedelta(days=days)
            for period in forecast['properties']['periods'][:min(14, days * 2)]:
                start_time = datetime.fromisoformat(period['startTime'])
                if start_time > cutoff_time:
                    break

                if period['isDaytime']:
                    # Convert NOAA temperature from Fahrenheit to Celsius
                    temp_f = float(period.get('temperature', 0))
                    temp_c = (temp_f - 32) * 5/9
                    forecast_obj = ForecastPoint(
                        timestamp=start_time,
                        temperature=temp_c,
                        temperature_max=temp_c,
                        weather_description=period.get('shortForecast'),
                        wind_speed=self._parse_wind_speed(period.get('windSpeed', '0 mph')),
                        precipitation_probability=float(period.get('probabilityOfPrecipitation', {}).get('value', 0)) if isinstance(period.get('probabilityOfPrecipitation'), dict) else 0,
                        source=WeatherSource.NOAA,
                        raw_data=period,
                    )
                    forecasts.append(forecast_obj)

            return forecasts
        except Exception as e:
            logger.error(f"NOAA daily forecast error: {e}")
            return []

    @staticmethod
    def _parse_wind_speed(wind_str: str) -> float:
        """Parse wind speed from NOAA format (e.g., '10 mph')"""
        try:
            parts = wind_str.split()
            if parts:
                return float(parts[0]) * 1.60934  # mph to km/h
        except:
            pass
        return 0.0

    @staticmethod
    def _wind_to_degrees(wind_dir: str) -> Optional[int]:
        """Convert wind direction letters to degrees"""
        directions = {
            'N': 0, 'NNE': 22.5, 'NE': 45, 'ENE': 67.5,
            'E': 90, 'ESE': 112.5, 'SE': 135, 'SSE': 157.5,
            'S': 180, 'SSW': 202.5, 'SW': 225, 'WSW': 247.5,
            'W': 270, 'WNW': 292.5, 'NW': 315, 'NNW': 337.5,
        }
        return int(directions.get(wind_dir.upper(), 0))


class METARSource(BaseWeatherSource):
    """METAR - Real-time aviation observations"""
    BASE_URL = "https://aviationweather.gov/api/data/metar"

    def _get_station_code(self, latitude: float, longitude: float) -> Optional[str]:
        """Find nearest METAR station (requires external mapping or hardcoding)"""
        # This is a simplified approach - in production, use NOAA station database
        # For now, return None and users should provide station codes directly
        return None

    def get_current_weather(self, latitude: float, longitude: float, station_code: Optional[str] = None) -> Optional[CurrentWeather]:
        """Fetch current METAR observation"""
        if not station_code:
            return None

        try:
            params = {
                'ids': station_code,
                'format': 'json',
            }
            response = self.session.get(self.BASE_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if not data.get('results'):
                return None

            metar = data['results'][0]
            return CurrentWeather(
                timestamp=datetime.fromisoformat(metar.get('obsTime', datetime.utcnow().isoformat())),
                temperature=float(metar.get('temp', {}).get('value', 0)),
                temperature_2m=float(metar.get('temp', {}).get('value', 0)),
                humidity=float(metar.get('dewp', {}).get('value', 0)) if 'dewp' in metar else None,
                dew_point=float(metar.get('dewp', {}).get('value', 0)) if 'dewp' in metar else None,
                wind_speed=float(metar.get('wdir', {}).get('value', 0)) if 'wdir' in metar else 0,
                wind_direction=int(metar.get('wdir', {}).get('value', 0)) if 'wdir' in metar else None,
                precipitation=float(metar.get('precp1H', {}).get('value', 0)) if 'precp1H' in metar else 0,
                visibility=float(metar.get('vis', {}).get('value', 0)) if 'vis' in metar else None,
                pressure=float(metar.get('altim', {}).get('value', 0)) if 'altim' in metar else None,
                source=WeatherSource.METAR,
                raw_data=metar,
            )
        except Exception as e:
            logger.error(f"METAR fetch error for {station_code}: {e}")
            return None

    def get_hourly_forecast(self, latitude: float, longitude: float, days: int = 7) -> List[ForecastPoint]:
        """METAR doesn't provide forecasts, only observations"""
        return []

    def get_daily_forecast(self, latitude: float, longitude: float, days: int = 30) -> List[ForecastPoint]:
        """METAR doesn't provide forecasts, only observations"""
        return []

    def get_historical_observations(self, latitude: float, longitude: float,
                                   station_code: Optional[str] = None,
                                   days_back: int = 7) -> List[HistoricalObservation]:
        """Fetch historical METAR observations"""
        if not station_code:
            return []

        try:
            params = {
                'ids': station_code,
                'format': 'json',
            }
            response = self.session.get(self.BASE_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            observations = []
            for metar in data.get('results', []):
                obs = HistoricalObservation(
                    timestamp=datetime.fromisoformat(metar.get('obsTime', datetime.utcnow().isoformat())),
                    temperature=float(metar.get('temp', {}).get('value', 0)),
                    humidity=float(metar.get('dewp', {}).get('value', 0)) if 'dewp' in metar else None,
                    wind_speed=float(metar.get('wdir', {}).get('value', 0)) if 'wdir' in metar else 0,
                    wind_direction=int(metar.get('wdir', {}).get('value', 0)) if 'wdir' in metar else None,
                    precipitation=float(metar.get('precp1H', {}).get('value', 0)) if 'precp1H' in metar else 0,
                    source=WeatherSource.METAR,
                    raw_data=metar,
                )
                observations.append(obs)

            return observations
        except Exception as e:
            logger.error(f"METAR historical fetch error: {e}")
            return []
