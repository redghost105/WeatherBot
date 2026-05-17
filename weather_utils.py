"""
Utility functions for weather data processing and Kalshi prediction integration.
Provides common operations, feature extraction, and data transformations.
"""
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from weather_models import (
    ForecastPoint,
    HistoricalObservation,
    LocationWeatherData,
    EnsembleData,
)


class WeatherFeatureExtractor:
    """Extract features from raw weather data for ML models"""

    @staticmethod
    def current_conditions_dict(weather_data: LocationWeatherData) -> Dict[str, float]:
        """Extract current weather as feature dict"""
        if not weather_data.current:
            return {}

        current = weather_data.current
        return {
            'temperature': current.temperature,
            'temperature_2m': current.temperature_2m,
            'feels_like': current.feels_like or current.temperature,
            'humidity': current.humidity or 50,
            'dew_point': current.dew_point or current.temperature - 5,
            'wind_speed': current.wind_speed,
            'wind_direction': current.wind_direction or 0,
            'wind_gust': current.wind_gust or current.wind_speed,
            'precipitation': current.precipitation,
            'precipitation_probability': current.precipitation_probability or 0,
            'cloud_cover': current.cloud_cover or 0,
            'visibility': current.visibility or 10,
            'pressure': current.pressure or 1013,
        }

    @staticmethod
    def hourly_statistics(forecasts: List[ForecastPoint],
                         hours_ahead: int = 24) -> Dict[str, float]:
        """Calculate statistics for next N hours"""
        relevant = [f for f in forecasts if f.timestamp <=
                   datetime.utcnow() + timedelta(hours=hours_ahead)]

        if not relevant:
            return {}

        temps = [f.temperature for f in relevant if f.temperature]
        winds = [f.wind_speed for f in relevant if f.wind_speed]
        precips = [f.precipitation for f in relevant if f.precipitation]
        precip_probs = [f.precipitation_probability for f in relevant
                       if f.precipitation_probability]

        stats = {}

        if temps:
            stats.update({
                f'temp_mean_{hours_ahead}h': statistics.mean(temps),
                f'temp_min_{hours_ahead}h': min(temps),
                f'temp_max_{hours_ahead}h': max(temps),
                f'temp_stdev_{hours_ahead}h': statistics.stdev(temps) if len(temps) > 1 else 0,
            })

        if winds:
            stats.update({
                f'wind_mean_{hours_ahead}h': statistics.mean(winds),
                f'wind_max_{hours_ahead}h': max(winds),
            })

        if precips:
            stats.update({
                f'precip_total_{hours_ahead}h': sum(precips),
                f'precip_max_{hours_ahead}h': max(precips),
            })

        if precip_probs:
            stats[f'precip_prob_mean_{hours_ahead}h'] = statistics.mean(precip_probs)

        return stats

    @staticmethod
    def daily_statistics(forecasts: List[ForecastPoint]) -> Dict[str, float]:
        """Calculate daily aggregate statistics"""
        if not forecasts:
            return {}

        stats = {}

        # Group by day
        by_day = defaultdict(list)
        for f in forecasts:
            day = f.timestamp.date()
            by_day[day].append(f)

        for day, points in sorted(by_day.items())[:7]:  # Next 7 days
            day_str = day.isoformat()

            temps = [p.temperature for p in points if p.temperature]
            if temps:
                stats[f'temp_mean_{day_str}'] = statistics.mean(temps)
                stats[f'temp_high_{day_str}'] = max(temps)
                stats[f'temp_low_{day_str}'] = min(temps)

            precips = [p.precipitation for p in points if p.precipitation]
            if precips:
                stats[f'precip_sum_{day_str}'] = sum(precips)

            precip_probs = [p.precipitation_probability for p in points
                           if p.precipitation_probability]
            if precip_probs:
                stats[f'precip_prob_max_{day_str}'] = max(precip_probs)

        return stats

    @staticmethod
    def ensemble_features(ensemble: List[EnsembleData]) -> Dict[str, float]:
        """Extract confidence and spread metrics from ensemble"""
        if not ensemble:
            return {}

        # Next 24 hours
        next_24h = [e for e in ensemble
                   if e.timestamp <= datetime.utcnow() + timedelta(hours=24)]

        if not next_24h:
            return {}

        temp_stds = [e.temperature_std for e in next_24h]
        precip_stds = [e.precipitation_std for e in next_24h]
        temp_ranges = [e.temperature_max - e.temperature_min for e in next_24h]

        return {
            'ensemble_temp_spread': statistics.mean(temp_stds),
            'ensemble_precip_spread': statistics.mean(precip_stds),
            'ensemble_temp_range': statistics.mean(temp_ranges),
            'ensemble_members': next_24h[0].ensemble_members if next_24h else 0,
            'ensemble_temp_confidence': max(0, min(1, 1 - (statistics.mean(temp_stds) / 10))),
        }


class WeatherValidation:
    """Validate and quality-check weather data"""

    @staticmethod
    def validate_temperature_range(value: float) -> Tuple[bool, Optional[str]]:
        """Check if temperature is within reasonable bounds"""
        if -60 <= value <= 60:
            return True, None
        return False, f"Temperature {value}°C outside valid range [-60, 60]"

    @staticmethod
    def validate_humidity(value: float) -> Tuple[bool, Optional[str]]:
        """Check if humidity is 0-100%"""
        if 0 <= value <= 100:
            return True, None
        return False, f"Humidity {value}% outside [0, 100]"

    @staticmethod
    def validate_wind_speed(value: float) -> Tuple[bool, Optional[str]]:
        """Check if wind speed is reasonable (0-100 km/h typical)"""
        if 0 <= value <= 150:
            return True, None
        return False, f"Wind speed {value} km/h outside [0, 150]"

    @staticmethod
    def validate_precipitation(value: float) -> Tuple[bool, Optional[str]]:
        """Check if precipitation is non-negative"""
        if value >= 0:
            return True, None
        return False, f"Precipitation {value}mm cannot be negative"

    @staticmethod
    def validate_forecast(forecast: ForecastPoint) -> Dict[str, Optional[str]]:
        """Validate all fields in a forecast point"""
        errors = {}

        if not WeatherValidation.validate_temperature_range(forecast.temperature)[0]:
            errors['temperature'] = WeatherValidation.validate_temperature_range(
                forecast.temperature)[1]

        if forecast.humidity and not WeatherValidation.validate_humidity(forecast.humidity)[0]:
            errors['humidity'] = WeatherValidation.validate_humidity(forecast.humidity)[1]

        if not WeatherValidation.validate_wind_speed(forecast.wind_speed)[0]:
            errors['wind_speed'] = WeatherValidation.validate_wind_speed(forecast.wind_speed)[1]

        if not WeatherValidation.validate_precipitation(forecast.precipitation)[0]:
            errors['precipitation'] = WeatherValidation.validate_precipitation(
                forecast.precipitation)[1]

        return {k: v for k, v in errors.items() if v is not None}

    @staticmethod
    def validate_location_data(data: LocationWeatherData) -> Dict[str, List[str]]:
        """Validate entire location weather data"""
        issues = defaultdict(list)

        if data.current:
            current_errors = WeatherValidation.validate_forecast(
                ForecastPoint(
                    timestamp=data.current.timestamp,
                    temperature=data.current.temperature,
                    humidity=data.current.humidity,
                    wind_speed=data.current.wind_speed,
                    precipitation=data.current.precipitation,
                )
            )
            if current_errors:
                issues['current'].extend(current_errors.values())

        for i, forecast in enumerate(data.hourly_forecast):
            forecast_errors = WeatherValidation.validate_forecast(forecast)
            if forecast_errors:
                issues[f'hourly_{i}'].extend(forecast_errors.values())

        return dict(issues)


class WeatherComparison:
    """Compare weather across sources or time periods"""

    @staticmethod
    def compare_sources(forecast1: ForecastPoint,
                       forecast2: ForecastPoint,
                       match_tolerance_hours: float = 1.0) -> Optional[Dict[str, float]]:
        """Compare two forecasts (from different sources) at similar times"""
        time_diff = abs((forecast1.timestamp - forecast2.timestamp).total_seconds() / 3600)

        if time_diff > match_tolerance_hours:
            return None

        differences = {
            'temperature_diff': abs(forecast1.temperature - forecast2.temperature),
            'wind_speed_diff': abs(forecast1.wind_speed - forecast2.wind_speed),
            'precipitation_diff': abs(forecast1.precipitation - forecast2.precipitation),
            'time_diff_hours': time_diff,
        }

        # Calculate agreement score (0-1, where 1 is perfect agreement)
        agreement = 1 - (
            (differences['temperature_diff'] / 10 +  # Normalize by typical variation
             differences['wind_speed_diff'] / 5 +
             differences['precipitation_diff'] / 5) / 3
        )
        differences['agreement_score'] = max(0, min(1, agreement))

        return differences

    @staticmethod
    def find_forecast_peaks(forecasts: List[ForecastPoint],
                           variable: str = 'temperature',
                           hours_ahead: int = 72) -> List[Dict]:
        """Find peak temperatures, wind, or precipitation in forecast"""
        relevant = [f for f in forecasts if f.timestamp <=
                   datetime.utcnow() + timedelta(hours=hours_ahead)]

        peaks = []

        if variable == 'temperature':
            values = [(f, f.temperature) for f in relevant if f.temperature]
        elif variable == 'wind_speed':
            values = [(f, f.wind_speed) for f in relevant if f.wind_speed]
        elif variable == 'precipitation':
            values = [(f, f.precipitation) for f in relevant if f.precipitation]
        elif variable == 'precipitation_probability':
            values = [(f, f.precipitation_probability or 0) for f in relevant]
        else:
            return []

        # Find local maxima
        for i, (forecast, value) in enumerate(values):
            is_peak = False

            if i == 0 or i == len(values) - 1:
                is_peak = True
            elif i > 0 and i < len(values) - 1:
                prev_val = values[i-1][1]
                next_val = values[i+1][1]
                if value >= prev_val and value >= next_val:
                    is_peak = True

            if is_peak:
                peaks.append({
                    'timestamp': forecast.timestamp,
                    'value': value,
                    'variable': variable,
                    'hours_ahead': (forecast.timestamp - datetime.utcnow()).total_seconds() / 3600,
                })

        return sorted(peaks, key=lambda x: x['value'], reverse=True)[:3]  # Top 3 peaks


class WeatherAggregations:
    """Aggregate weather data for market-specific operations"""

    @staticmethod
    def temperature_exceedance_probability(forecasts: List[ForecastPoint],
                                          threshold: float,
                                          hours_ahead: int = 24) -> float:
        """Probability that temperature exceeds threshold in next N hours"""
        relevant = [f for f in forecasts if f.timestamp <=
                   datetime.utcnow() + timedelta(hours=hours_ahead)]

        if not relevant:
            return 0.0

        exceeds = sum(1 for f in relevant if f.temperature >= threshold)
        return exceeds / len(relevant)

    @staticmethod
    def precipitation_probability_aggregate(forecasts: List[ForecastPoint],
                                           hours_ahead: int = 24) -> Dict[str, float]:
        """Aggregate precipitation probabilities"""
        relevant = [f for f in forecasts if f.timestamp <=
                   datetime.utcnow() + timedelta(hours=hours_ahead)]

        if not relevant:
            return {'mean': 0, 'max': 0, 'any_chance': 0}

        probs = [f.precipitation_probability or 0 for f in relevant if f.precipitation_probability]

        if not probs:
            probs = [0]

        return {
            'mean_probability': statistics.mean(probs),
            'max_probability': max(probs),
            'probability_any_precip': 1.0 if max(probs) > 0 else 0.0,
            'hours_with_precip_chance': sum(1 for p in probs if p > 0),
        }

    @staticmethod
    def wind_event_probability(forecasts: List[ForecastPoint],
                              threshold: float = 25,
                              hours_ahead: int = 24) -> float:
        """Probability of wind exceeding threshold in next N hours"""
        relevant = [f for f in forecasts if f.timestamp <=
                   datetime.utcnow() + timedelta(hours=hours_ahead)]

        if not relevant:
            return 0.0

        exceeds = sum(1 for f in relevant if f.wind_speed >= threshold)
        return exceeds / len(relevant)
