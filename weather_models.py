"""
Unified weather data models for normalization across all sources.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class WeatherSource(Enum):
    OPEN_METEO = "open_meteo"
    NOAA = "noaa"
    METAR = "metar"
    ECMWF = "ecmwf"


@dataclass
class CurrentWeather:
    """Real-time current conditions"""
    timestamp: datetime
    temperature: float  # Celsius
    temperature_2m: float  # Standard 2m height
    feels_like: Optional[float] = None
    humidity: Optional[float] = None  # 0-100 %
    dew_point: Optional[float] = None
    wind_speed: float = 0.0  # km/h
    wind_direction: Optional[int] = None  # 0-360 degrees
    wind_gust: Optional[float] = None
    precipitation: float = 0.0  # mm
    precipitation_probability: Optional[float] = None  # 0-100 %
    weather_code: Optional[int] = None  # WMO code
    weather_description: Optional[str] = None
    cloud_cover: Optional[float] = None  # 0-100 %
    visibility: Optional[float] = None  # km
    pressure: Optional[float] = None  # hPa
    source: WeatherSource = WeatherSource.OPEN_METEO
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ForecastPoint:
    """Single forecast time point"""
    timestamp: datetime
    temperature: float
    temperature_min: Optional[float] = None
    temperature_max: Optional[float] = None
    humidity: Optional[float] = None
    dew_point: Optional[float] = None
    wind_speed: float = 0.0
    wind_direction: Optional[int] = None
    wind_gust: Optional[float] = None
    precipitation: float = 0.0
    precipitation_probability: Optional[float] = None
    weather_code: Optional[int] = None
    weather_description: Optional[str] = None
    cloud_cover: Optional[float] = None
    visibility: Optional[float] = None
    pressure: Optional[float] = None
    source: WeatherSource = WeatherSource.OPEN_METEO
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnsembleData:
    """Ensemble forecast data with spread/confidence"""
    timestamp: datetime
    ensemble_members: int
    temperature_mean: float
    temperature_std: float  # Standard deviation
    temperature_min: float
    temperature_max: float
    wind_speed_mean: float
    wind_speed_std: float
    precipitation_mean: float
    precipitation_std: float
    precipitation_probability: Optional[float] = None
    precipitation_probability_std: Optional[float] = None
    weather_codes: Dict[int, float] = field(default_factory=dict)  # code -> probability
    source: WeatherSource = WeatherSource.OPEN_METEO
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WeatherTimeseries:
    """Collection of forecast points"""
    timestamps: List[datetime]
    data: List[ForecastPoint]
    source: WeatherSource = WeatherSource.OPEN_METEO


@dataclass
class HistoricalObservation:
    """Historical weather observation for validation"""
    timestamp: datetime
    temperature: float
    humidity: Optional[float] = None
    wind_speed: float = 0.0
    wind_direction: Optional[int] = None
    precipitation: float = 0.0
    weather_code: Optional[int] = None
    source: WeatherSource = WeatherSource.METAR
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LocationWeatherData:
    """Complete weather data for a location"""
    latitude: float
    longitude: float
    elevation: Optional[float] = None
    timezone: Optional[str] = None
    location_name: Optional[str] = None

    current: Optional[CurrentWeather] = None
    hourly_forecast: List[ForecastPoint] = field(default_factory=list)
    daily_forecast: List[ForecastPoint] = field(default_factory=list)
    ensemble_forecast: List[EnsembleData] = field(default_factory=list)
    historical_observations: List[HistoricalObservation] = field(default_factory=list)

    last_updated: datetime = field(default_factory=datetime.utcnow)
    sources_used: List[WeatherSource] = field(default_factory=list)

    def add_source(self, source: WeatherSource):
        """Track which sources were used"""
        if source not in self.sources_used:
            self.sources_used.append(source)


@dataclass
class ValidationMetrics:
    """Metrics comparing forecast to actual observations"""
    mae: float  # Mean Absolute Error
    rmse: float  # Root Mean Square Error
    bias: float  # Mean signed error
    forecast_count: int
    observation_count: int
    matched_count: int
    variable: str  # e.g., "temperature", "wind_speed"
    source: WeatherSource = WeatherSource.OPEN_METEO
    timestamp: datetime = field(default_factory=datetime.utcnow)
