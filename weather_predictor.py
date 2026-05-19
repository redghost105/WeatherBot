"""
WeatherPredictor - Core intelligence engine for Kalshi/Polymarket weather trading bot.

Transforms clean weather data from WeatherAggregator into calibrated probability
distributions across market temperature buckets, identifies trading edges, and
continuously improves through historical bias learning.

Philosophy: Hybrid approach combining ensemble counting, statistical modeling,
and station-specific historical bias correction.
"""

import json
import logging
import statistics
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from scipy import stats
import numpy as np

from weather_models import LocationWeatherData, ForecastPoint

logger = logging.getLogger(__name__)


# ============================================================================
# PHASE 1: Core Data Structures & Historical Learner
# ============================================================================

@dataclass
class Bucket:
    """
    Represents a single market temperature bucket.

    Example: 92–93°F bucket would have low=92, high=93, label="92-93"
    """
    low: float
    high: float
    label: str

    def contains(self, temperature: float) -> bool:
        """Check if temperature falls within this bucket."""
        return self.low <= temperature < self.high

    def midpoint(self) -> float:
        """Return the midpoint of the bucket."""
        return (self.low + self.high) / 2.0

    def width(self) -> float:
        """Return the width of the bucket."""
        return self.high - self.low


class HistoricalBiasLearner:
    """
    Maintains rolling history of forecast vs. actual temperatures per station.

    Computes station-specific biases (e.g., "KNYC runs 1.2°F warm on average")
    and provides bias correction values for future predictions.

    Automatically persists to JSON for historical continuity.
    """

    def __init__(self, bias_file: Optional[str] = None, max_history: int = 365):
        """
        Initialize the bias learner.

        Args:
            bias_file: Path to JSON file for persistence. If None, uses default.
            max_history: Maximum number of historical records to maintain per station.
        """
        self.max_history = max_history
        self.bias_file = Path(bias_file or "station_bias_history.json")
        self.station_biases: Dict[str, List[Dict]] = {}

        # Load existing bias data if file exists
        if self.bias_file.exists():
            try:
                with open(self.bias_file, 'r') as f:
                    self.station_biases = json.load(f)
                logger.info(f"Loaded bias history from {self.bias_file}")
            except Exception as e:
                logger.warning(f"Failed to load bias history: {e}. Starting fresh.")
                self.station_biases = {}
        else:
            logger.info(f"Starting fresh bias history (will save to {self.bias_file})")

    def update(self, station_id: str, forecast_high: float, actual_high: float,
               date: Optional[str] = None) -> None:
        """
        Record a (forecast_high, actual_high) pair for a station.

        Args:
            station_id: Station code (e.g., "KNYC", "KMDW")
            forecast_high: Forecasted high temperature
            actual_high: Observed high temperature
            date: Date string (ISO format). If None, uses today.
        """
        if station_id not in self.station_biases:
            self.station_biases[station_id] = []

        date = date or datetime.now().isoformat()
        bias = forecast_high - actual_high  # Positive = forecast too warm

        record = {
            'date': date,
            'forecast_high': forecast_high,
            'actual_high': actual_high,
            'bias': bias
        }

        self.station_biases[station_id].append(record)

        # Trim to max_history
        if len(self.station_biases[station_id]) > self.max_history:
            self.station_biases[station_id] = self.station_biases[station_id][-self.max_history:]

        logger.debug(f"Updated bias for {station_id}: forecast={forecast_high}, actual={actual_high}, bias={bias:.2f}")

        # Persist to file
        self._save()

    def get_bias(self, station_id: str, lookback_days: int = 90) -> float:
        """
        Get the average bias correction for a station.

        Returns the mean forecast bias (forecast - actual) over recent history.
        Positive value = forecast runs warm on average.

        Args:
            station_id: Station code (e.g., "KNYC")
            lookback_days: Number of days to consider (default: 90 days)

        Returns:
            Average bias in degrees. Returns 0.0 if no history exists.
        """
        if station_id not in self.station_biases or not self.station_biases[station_id]:
            logger.debug(f"No bias history for {station_id}, returning 0.0")
            return 0.0

        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        recent_records = [
            r for r in self.station_biases[station_id]
            if datetime.fromisoformat(r['date']) >= cutoff_date
        ]

        if not recent_records:
            logger.debug(f"No recent bias history for {station_id} ({lookback_days}d), returning 0.0")
            return 0.0

        biases = [r['bias'] for r in recent_records]
        avg_bias = statistics.mean(biases)

        logger.debug(f"Bias for {station_id}: {avg_bias:.2f}°F ({len(biases)} records)")
        return avg_bias

    def get_bias_std(self, station_id: str, lookback_days: int = 90) -> float:
        """
        Get the standard deviation of bias for a station (uncertainty in the bias correction).

        Args:
            station_id: Station code
            lookback_days: Number of days to consider

        Returns:
            Standard deviation of bias. Returns 0.5 if insufficient history.
        """
        if station_id not in self.station_biases or not self.station_biases[station_id]:
            return 0.5

        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        recent_records = [
            r for r in self.station_biases[station_id]
            if datetime.fromisoformat(r['date']) >= cutoff_date
        ]

        if len(recent_records) < 2:
            return 0.5

        biases = [r['bias'] for r in recent_records]
        return statistics.stdev(biases)

    def _save(self) -> None:
        """Persist bias data to JSON file."""
        try:
            with open(self.bias_file, 'w') as f:
                json.dump(self.station_biases, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save bias history: {e}")


# ============================================================================
# PHASE 2: WeatherPredictor Core Class – Hybrid Logic
# ============================================================================

class WeatherPredictor:
    """
    Main orchestration class for weather-based probability prediction.

    Uses a hybrid approach:
    1. Ensemble counting - count fraction of ensemble members in each bucket
    2. Statistical fitting - Normal distribution on bias-adjusted forecast mean
    3. Blending - weighted combination (60-75% ensemble when available)
    4. Post-processing - normalize and clamp to reasonable bounds

    Station-aware bias correction learned from historical observations.
    """

    def __init__(self, bias_learner: Optional[HistoricalBiasLearner] = None,
                 ensemble_weight: float = 0.7, temp_unit: str = 'F'):
        """
        Initialize the WeatherPredictor.

        Args:
            bias_learner: HistoricalBiasLearner instance. Creates one if None.
            ensemble_weight: Weight for ensemble probabilities in blend (0.0-1.0).
                            Defaults to 0.7 (70% ensemble, 30% statistical).
            temp_unit: Temperature unit ('F' for Fahrenheit, 'C' for Celsius).
        """
        self.bias_learner = bias_learner or HistoricalBiasLearner()
        self.ensemble_weight = ensemble_weight
        self.temp_unit = temp_unit

        logger.info(f"WeatherPredictor initialized: ensemble_weight={ensemble_weight}, temp_unit={temp_unit}")

    def hybrid_bucket_probabilities(self,
                                    weather_data: LocationWeatherData,
                                    buckets: List[Bucket],
                                    station_id: str,
                                    use_ensemble: bool = True,
                                    use_statistics: bool = True,
                                    apply_bias_correction: bool = True) -> Dict[str, Dict]:
        """
        Main method: Calculate probability distribution across market buckets using hybrid approach.

        Args:
            weather_data: LocationWeatherData object from WeatherAggregator
            buckets: List of Bucket objects representing market temperature bins
            station_id: Station identifier (e.g., "KNYC", "KMDW")
            use_ensemble: Whether to use ensemble method if data available
            use_statistics: Whether to use statistical fallback
            apply_bias_correction: Whether to apply historical bias correction

        Returns:
            Dict mapping bucket_label → {
                'probability': float (0-1),
                'method': str (ensemble, statistical, or blended),
                'confidence': float (0-1),
                'reasoning': str
            }
        """
        logger.info(f"Calculating probabilities for {station_id}, {len(buckets)} buckets")

        # Extract forecast mean
        forecast_mean = self._extract_forecast_mean(weather_data)
        if forecast_mean is None:
            logger.error(f"Could not extract forecast mean for {station_id}")
            return {}

        # Apply bias correction
        bias_correction = 0.0
        if apply_bias_correction:
            bias_correction = self.bias_learner.get_bias(station_id)
            adjusted_mean = forecast_mean - bias_correction
            logger.debug(f"Bias correction: {bias_correction:.2f}°, adjusted mean: {adjusted_mean:.2f}°")
        else:
            adjusted_mean = forecast_mean

        # Calculate ensemble probabilities if available
        ensemble_probs = None
        ensemble_confidence = 0.0
        if use_ensemble and weather_data.ensemble_forecast:
            ensemble_probs, ensemble_confidence = self._calculate_ensemble_probs(
                weather_data.ensemble_forecast, buckets
            )

        # Calculate statistical probabilities
        statistical_probs = None
        statistical_confidence = 0.0
        if use_statistics:
            statistical_probs, statistical_confidence = self._calculate_statistical_probs(
                adjusted_mean, weather_data, buckets
            )

        # Blend probabilities
        if ensemble_probs and statistical_probs:
            final_probs, method, confidence = self._blend_probabilities(
                ensemble_probs, statistical_probs,
                ensemble_confidence, statistical_confidence
            )
        elif ensemble_probs:
            final_probs = ensemble_probs
            method = "ensemble"
            confidence = ensemble_confidence
        elif statistical_probs:
            final_probs = statistical_probs
            method = "statistical"
            confidence = statistical_confidence
        else:
            logger.error(f"No probabilities calculated for {station_id}")
            return {}

        # Package results
        result = {}
        for bucket in buckets:
            result[bucket.label] = {
                'probability': final_probs.get(bucket.label, 0.0),
                'method': method,
                'confidence': confidence,
                'reasoning': f"Forecast mean: {forecast_mean:.1f}°, bias-adjusted: {adjusted_mean:.1f}°, method: {method}"
            }

        logger.info(f"Calculated {len(result)} bucket probabilities using {method} (confidence: {confidence:.2%})")
        return result

    def _extract_forecast_mean(self, weather_data: LocationWeatherData) -> Optional[float]:
        """
        Extract the best estimate of the day's high temperature.

        Priority:
        1. Daily forecast temperature_max (if available)
        2. Hourly forecast max over next 24h
        3. Current temperature + safety margin

        Args:
            weather_data: LocationWeatherData object

        Returns:
            Forecast high temperature, or None if extraction fails.
        """
        # Try daily forecast first (most reliable for daily high)
        if weather_data.daily_forecast:
            first_day = weather_data.daily_forecast[0]
            if first_day.temperature_max is not None:
                logger.debug(f"Using daily forecast max: {first_day.temperature_max:.1f}°")
                return first_day.temperature_max

        # Fall back to hourly forecast maximum
        if weather_data.hourly_forecast:
            temps_24h = [
                p.temperature for p in weather_data.hourly_forecast[:24]
                if p.temperature is not None
            ]
            if temps_24h:
                hourly_max = max(temps_24h)
                logger.debug(f"Using hourly forecast max (24h): {hourly_max:.1f}°")
                return hourly_max

        # Last resort: current temperature + safety margin
        if weather_data.current and weather_data.current.temperature is not None:
            current_temp = weather_data.current.temperature
            safety_margin = 3.0  # Assume +3° warmth during the day
            forecast = current_temp + safety_margin
            logger.debug(f"Using current temp + margin: {current_temp:.1f}° + {safety_margin}° = {forecast:.1f}°")
            return forecast

        logger.warning("Could not extract forecast mean from any source")
        return None

    def _calculate_ensemble_probs(self,
                                  ensemble_data: List,
                                  buckets: List[Bucket]) -> Tuple[Dict[str, float], float]:
        """
        Calculate bucket probabilities using ensemble member counting.

        Method: For each ensemble data point, extract the temperature and count
        how many members fall into each bucket. Normalize to probabilities.

        Args:
            ensemble_data: List of EnsembleData objects
            buckets: List of Bucket objects

        Returns:
            Tuple of (probabilities dict, confidence score)
        """
        if not ensemble_data:
            return {}, 0.0

        # Count members in each bucket
        bucket_counts = {b.label: 0 for b in buckets}
        total_members = 0

        for ensemble_point in ensemble_data:
            # Use ensemble mean as representative value
            if ensemble_point.temperature_mean is not None:
                temp = ensemble_point.temperature_mean
                total_members += 1

                for bucket in buckets:
                    if bucket.contains(temp):
                        bucket_counts[bucket.label] += 1

        # Normalize to probabilities
        probs = {}
        confidence = min(1.0, total_members / 10.0)  # Higher confidence with more members

        if total_members > 0:
            for label, count in bucket_counts.items():
                probs[label] = count / total_members

        logger.debug(f"Ensemble probs: {total_members} members, confidence: {confidence:.2%}")
        return probs, confidence

    def _calculate_statistical_probs(self,
                                     mean_temp: float,
                                     weather_data: LocationWeatherData,
                                     buckets: List[Bucket]) -> Tuple[Dict[str, float], float]:
        """
        Calculate bucket probabilities using Normal distribution fitting.

        Method: Fit a Normal distribution to (bias-adjusted) forecast mean
        with standard deviation derived from extracted features (temp_stdev_24h, etc).
        Slightly inflate std for conservatism.

        Args:
            mean_temp: Bias-adjusted forecast mean
            weather_data: LocationWeatherData for feature extraction
            buckets: List of Bucket objects

        Returns:
            Tuple of (probabilities dict, confidence score)
        """
        # Extract standard deviation from features
        stdev = self._calculate_smart_stdev(weather_data)

        # Inflate stdev slightly for conservatism (avoid overconfidence)
        stdev_inflated = stdev * 1.15

        logger.debug(f"Statistical fit: mean={mean_temp:.1f}°, stdev={stdev:.1f}° → {stdev_inflated:.1f}° (inflated)")

        # Calculate CDF-based probabilities for each bucket
        probs = {}
        normal_dist = stats.norm(loc=mean_temp, scale=stdev_inflated)

        for bucket in buckets:
            # Probability that temperature falls in [low, high)
            prob_low = normal_dist.cdf(bucket.low)
            prob_high = normal_dist.cdf(bucket.high)
            probs[bucket.label] = max(0.0, prob_high - prob_low)

        # Confidence based on ensemble std if available
        confidence = 0.6  # Baseline
        if weather_data.ensemble_forecast:
            ensemble_stdevs = [
                e.temperature_std for e in weather_data.ensemble_forecast
                if e.temperature_std is not None and e.temperature_std > 0
            ]
            if ensemble_stdevs:
                avg_ensemble_std = statistics.mean(ensemble_stdevs)
                # Lower confidence if ensemble shows high disagreement
                confidence = min(0.8, 2.0 / (1.0 + avg_ensemble_std))

        logger.debug(f"Statistical probs: {len(probs)} buckets, confidence: {confidence:.2%}")
        return probs, confidence

    def _calculate_smart_stdev(self, weather_data: LocationWeatherData) -> float:
        """
        Calculate forecast standard deviation using extracted features.

        Uses hourly statistics when available, with seasonal/weather regime awareness.

        Args:
            weather_data: LocationWeatherData object

        Returns:
            Estimated standard deviation in degrees
        """
        # If ensemble data available, use its spread
        if weather_data.ensemble_forecast:
            ensemble_stds = [
                e.temperature_std for e in weather_data.ensemble_forecast
                if e.temperature_std is not None and e.temperature_std > 0
            ]
            if ensemble_stds:
                avg_stdev = statistics.mean(ensemble_stds)
                logger.debug(f"Using ensemble std: {avg_stdev:.2f}°")
                return avg_stdev

        # Fall back to extracted hourly statistics
        # Look for temp_stdev_24h in features if available
        # Default conservative estimate: 2.5–4.0° depending on season
        default_stdev = 3.0

        # Could extract from weather_data.current if it had a features dict
        # For now, use default
        logger.debug(f"Using default stdev: {default_stdev:.2f}°")
        return default_stdev

    def _blend_probabilities(self,
                            ensemble_probs: Dict[str, float],
                            statistical_probs: Dict[str, float],
                            ensemble_confidence: float,
                            statistical_confidence: float) -> Tuple[Dict[str, float], str, float]:
        """
        Blend ensemble and statistical probabilities using weighted average.

        Weight by confidence scores, normalize, clamp extremes.

        Args:
            ensemble_probs: Probabilities from ensemble method
            statistical_probs: Probabilities from statistical method
            ensemble_confidence: Confidence in ensemble (0-1)
            statistical_confidence: Confidence in statistical (0-1)

        Returns:
            Tuple of (blended probs dict, 'blended', overall confidence)
        """
        # Normalize confidences
        total_conf = ensemble_confidence + statistical_confidence
        if total_conf == 0:
            total_conf = 1.0

        ensemble_weight = ensemble_confidence / total_conf
        statistical_weight = statistical_confidence / total_conf

        # Blend
        blended = {}
        all_labels = set(ensemble_probs.keys()) | set(statistical_probs.keys())

        for label in all_labels:
            e_prob = ensemble_probs.get(label, 0.0)
            s_prob = statistical_probs.get(label, 0.0)
            blended[label] = (e_prob * ensemble_weight + s_prob * statistical_weight)

        # Normalize to ensure sum ≈ 1.0
        total = sum(blended.values())
        if total > 0:
            blended = {k: v / total for k, v in blended.items()}

        # Clamp extremes (avoid 0.0 or 1.0)
        blended = {k: max(0.001, min(0.999, v)) for k, v in blended.items()}

        # Re-normalize after clamping
        total = sum(blended.values())
        if total > 0:
            blended = {k: v / total for k, v in blended.items()}

        overall_confidence = (ensemble_confidence + statistical_confidence) / 2.0

        logger.debug(f"Blended: {ensemble_weight:.1%} ensemble + {statistical_weight:.1%} statistical")
        return blended, "blended", overall_confidence


# ============================================================================
# Helper Functions
# ============================================================================

def parse_bucket_string(bucket_str: str, unit: str = 'F') -> Bucket:
    """
    Parse a bucket label like "92-93" into a Bucket object.

    Args:
        bucket_str: String like "92-93" or "28-29"
        unit: Temperature unit ('F' or 'C')

    Returns:
        Bucket object
    """
    parts = bucket_str.split('-')
    if len(parts) != 2:
        raise ValueError(f"Invalid bucket string: {bucket_str}")

    low = float(parts[0])
    high = float(parts[1])

    return Bucket(low=low, high=high, label=bucket_str)


def create_buckets_from_range(low: float, high: float, unit: str = 'F') -> List[Bucket]:
    """
    Create a list of consecutive 1-degree buckets covering a range.

    Args:
        low: Lower bound (inclusive)
        high: Upper bound (exclusive)
        unit: Temperature unit

    Returns:
        List of Bucket objects
    """
    buckets = []
    current = int(low)
    while current < high:
        bucket = Bucket(low=current, high=current + 1, label=f"{current}-{current + 1}")
        buckets.append(bucket)
        current += 1
    return buckets
