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
import re
import statistics
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from scipy import stats
import numpy as np

from weather_models import LocationWeatherData, ForecastPoint

logger = logging.getLogger(__name__)


# ============================================================================
# PHASE 4: Configuration & Tunables
# ============================================================================

@dataclass
class PredictorConfig:
    """
    Central configuration for WeatherPredictor tunables.

    Pass an instance to WeatherPredictor(config=...) to override any default
    without modifying core code. All parameters are configurable and optional.
    """
    ensemble_weight: float = 0.7
    min_edge_threshold: float = 0.10
    min_stdev: float = 1.2            # SD floor — prevents overconfidence on flat forecasts
    max_stdev: float = 3.5            # SD cap — prevents absurd uncertainty estimates
    confidence_formula_weights: Dict[str, int] = field(default_factory=lambda: {
        "ensemble": 25,               # Ensemble tightness (0-25 pts)
        "bias": 25,                   # Bias stability (0-25 pts)
        "freshness": 25,              # Data freshness (0-25 pts)
        "volatility": 25,             # Volatility indicators (0-25 pts)
    })
    temp_unit: str = 'F'
    bias_file: str = 'station_bias_history.json'
    max_history: int = 365


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

        date = date or datetime.now(timezone.utc).isoformat()
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

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        recent_records = []
        for r in self.station_biases[station_id]:
            parsed_date = datetime.fromisoformat(r['date'])
            # Normalize naive datetimes to UTC
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
            if parsed_date >= cutoff_date:
                recent_records.append(r)

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

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        recent_records = []
        for r in self.station_biases[station_id]:
            parsed_date = datetime.fromisoformat(r['date'])
            # Normalize naive datetimes to UTC
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
            if parsed_date >= cutoff_date:
                recent_records.append(r)

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
# PHASE 3: Edge Detection & Trading Intelligence
# ============================================================================

@dataclass
class BucketEdge:
    """
    Analysis of one bucket's trading edge: model probability vs market probability.

    Used by calculate_edge() to report per-bucket opportunity details and recommendations.
    """
    label: str                              # e.g., "92-93"
    model_prob: float                       # Model's probability (0–1)
    market_prob: float                      # Market-implied probability (0–1)
    edge: float                             # model_prob - market_prob (signed, can be negative)
    recommendation: str                     # "BUY", "STRONG_BUY", "SELL_NO", or "SKIP"
    conviction: float                       # 0–1, after risk adjustments and adjacency bonuses
    is_adjacent_group_member: bool          # True if part of 2+ bucket positive-edge run
    group_id: Optional[int]                 # Index of adjacent group; None if isolated


@dataclass
class MarketEdgeSummary:
    """
    Complete market-level trading opportunity analysis.

    Returned by calculate_edge() with comprehensive per-bucket analysis,
    confidence scoring, risk flags, and recommendations.
    """
    station_id: str                         # Station identifier (e.g., "KNYC")
    confidence_score: float                 # 0–100 composite confidence
    overall_ev: float                       # Expected value sum (edge × conviction) for BUY/STRONG_BUY
    bucket_edges: List[BucketEdge]          # All buckets (including SKIPs)
    top_buckets: List[str]                  # Up to 3 highest-conviction positive-edge bucket labels
    recommended_exposure: str               # "NONE", "LOW", "MEDIUM", or "HIGH"
    risk_flags: List[str]                   # Active risk modifier flags
    reasoning: str                          # Human-readable summary


@dataclass
class BacktestResult:
    """
    Aggregate calibration metrics from BacktestRunner.run().

    Provides comprehensive assessment of predictor accuracy, confidence calibration,
    and trading edge capture across a historical data replay.
    """
    n_resolved: int                         # Number of observations processed
    brier_score: float                      # Mean Brier Score across all obs (0-1, lower = better)
    hit_rate: float                         # Fraction where max-prob bucket = actual (0-1)
    avg_confidence: float                   # Mean confidence_score across all observations
    per_observation: List[Dict]             # Raw per-observation records for inspection/audit
    simulated_roi: Optional[float] = None   # Mean overall_ev if market_prices provided
    calibration_sharpness: Optional[float] = None  # Variance of probs for resolved buckets


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
                 ensemble_weight: float = 0.7, temp_unit: str = 'F',
                 config: Optional[PredictorConfig] = None):
        """
        Initialize the WeatherPredictor.

        Args:
            bias_learner: HistoricalBiasLearner instance. Creates one if None.
            ensemble_weight: Weight for ensemble probabilities in blend (0.0-1.0).
                            Defaults to 0.7 (70% ensemble, 30% statistical).
                            Ignored if config is provided.
            temp_unit: Temperature unit ('F' for Fahrenheit, 'C' for Celsius).
                      Ignored if config is provided.
            config: Optional PredictorConfig object. If provided, it takes precedence
                   over ensemble_weight and temp_unit. If not provided, creates a
                   config from the individual parameters for backward compatibility.
        """
        # Resolve configuration
        if config is not None:
            self.config = config
        else:
            # Backward compatibility: create config from individual parameters
            self.config = PredictorConfig(ensemble_weight=ensemble_weight, temp_unit=temp_unit)

        # Store convenience attributes for backward compatibility
        self.ensemble_weight = self.config.ensemble_weight
        self.temp_unit = self.config.temp_unit

        # Initialize bias learner: explicit arg wins over config
        if bias_learner is not None:
            self.bias_learner = bias_learner
        else:
            self.bias_learner = HistoricalBiasLearner(
                bias_file=self.config.bias_file,
                max_history=self.config.max_history
            )

        logger.info(f"WeatherPredictor initialized: ensemble_weight={self.ensemble_weight}, temp_unit={self.temp_unit}, config_provided={config is not None}")

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

        # Structured audit logging for full traceability
        audit = {
            "station_id": station_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "method": method,
            "forecast_mean": round(forecast_mean, 2),
            "bias_applied": round(bias_correction, 3),
            "adjusted_mean": round(adjusted_mean, 2),
            "ensemble_count": len(weather_data.ensemble_forecast) if weather_data.ensemble_forecast else 0,
            "confidence": round(confidence, 3),
            "prob_sum": round(sum(d['probability'] for d in result.values()), 5),
            "n_buckets": len(result)
        }
        logger.info(f"AUDIT|{json.dumps(audit)}")

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

        Uses ensemble spread when available, with fallback to a conservative default.
        Applied bounds (min_stdev, max_stdev) prevent overconfidence and absurd estimates.

        Philosophy:
        - Lower bound (min_stdev, default 1.2°): prevents overconfidence on flat, stable
          forecasts. Even when multiple models agree, some uncertainty always exists.
        - Upper bound (max_stdev, default 3.5°): prevents absurdly wide distributions
          that would make every bucket equally likely. This keeps the model responsive
          to actual forecast divergence without going to extremes.

        Args:
            weather_data: LocationWeatherData object

        Returns:
            Estimated standard deviation in degrees, bounded by config min/max
        """
        raw_stdev = None

        # If ensemble data available, use its spread (most reliable signal)
        if weather_data.ensemble_forecast:
            ensemble_stds = [
                e.temperature_std for e in weather_data.ensemble_forecast
                if e.temperature_std is not None and e.temperature_std > 0
            ]
            if ensemble_stds:
                raw_stdev = statistics.mean(ensemble_stds)
                logger.debug(f"Ensemble std (raw): {raw_stdev:.2f}°")

        # If no ensemble or it failed, use conservative default
        if raw_stdev is None:
            raw_stdev = (self.config.min_stdev + self.config.max_stdev) / 2.0
            logger.debug(f"Using default stdev: {raw_stdev:.2f}°")

        # Apply configured bounds (critical to prevent extreme overconfidence/uncertainty)
        stdev_used = max(self.config.min_stdev, min(self.config.max_stdev, raw_stdev))

        if stdev_used != raw_stdev:
            logger.debug(f"Clamped stdev from {raw_stdev:.2f}° to {stdev_used:.2f}° [min={self.config.min_stdev}, max={self.config.max_stdev}]")

        return stdev_used

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

    # ========================================================================
    # PHASE 3: Edge Detection & Trading Intelligence
    # ========================================================================

    def calculate_edge(self,
                      model_probs: Dict[str, float],
                      market_prices: Dict[str, float],
                      buckets: List[Bucket],
                      station_id: str,
                      weather_data: LocationWeatherData,
                      min_edge: float = 0.10) -> MarketEdgeSummary:
        """
        Compare model probabilities to market-implied probabilities and surface +EV opportunities.

        Performs comprehensive edge analysis: computes 4-factor confidence score, applies risk
        modifiers, detects adjacent bucket grouping, adjusts conviction, and generates trading
        recommendations (BUY, STRONG_BUY, SELL_NO, SKIP).

        Args:
            model_probs: Dict mapping bucket label → model probability (from hybrid_bucket_probabilities)
            market_prices: Dict mapping bucket label → market-implied probability (0–1)
            buckets: List of Bucket objects (must be ordered low→high for adjacency detection)
            station_id: Station identifier (e.g., "KNYC")
            weather_data: LocationWeatherData object (for confidence & risk calculations)
            min_edge: Minimum raw edge threshold for BUY recommendation (default 0.10)

        Returns:
            MarketEdgeSummary with per-bucket edges, recommendations, confidence score, and risk flags
        """
        logger.info(f"Calculating edge for {station_id}: {len(model_probs)} model buckets")

        # Guard: check for common labels
        common_labels = set(model_probs.keys()) & set(market_prices.keys())
        if not common_labels:
            logger.warning(f"No common bucket labels between model and market for {station_id}")
            return MarketEdgeSummary(
                station_id=station_id,
                confidence_score=0.0,
                overall_ev=0.0,
                bucket_edges=[],
                top_buckets=[],
                recommended_exposure="NONE",
                risk_flags=["no_common_buckets"],
                reasoning="No common bucket labels between model and market."
            )

        # Compute 4-factor confidence score
        confidence_score, global_risk_flags = self._compute_confidence_score(weather_data, station_id)
        logger.debug(f"Confidence score: {confidence_score:.1f}/100, risk flags: {global_risk_flags}")

        # Safety gate: confidence < 25 → force all recommendations to SKIP
        safety_override = confidence_score < 25

        # Build initial bucket edges
        bucket_edges = []
        for label in common_labels:
            model_prob = model_probs[label]
            market_prob = market_prices[label]
            edge = model_prob - market_prob

            # Base conviction from confidence score
            base_conviction = confidence_score / 100.0

            # Apply risk modifiers
            conviction, per_bucket_flags = self._apply_risk_modifiers(base_conviction, weather_data)

            # Initial recommendation (before adjacency adjustments)
            if safety_override:
                recommendation = "SKIP"
            elif edge >= min_edge * 2 and conviction >= 0.80:
                recommendation = "STRONG_BUY"
            elif edge >= min_edge:
                recommendation = "BUY"
            elif edge <= -min_edge:
                recommendation = "SELL_NO"
            else:
                recommendation = "SKIP"

            bucket_edges.append(BucketEdge(
                label=label,
                model_prob=model_prob,
                market_prob=market_prob,
                edge=edge,
                recommendation=recommendation,
                conviction=conviction,
                is_adjacent_group_member=False,
                group_id=None
            ))

        # Detect adjacent groups (2+ consecutive positive-edge buckets)
        bucket_edges = self._detect_adjacent_groups(bucket_edges, buckets)

        # Apply spread bonus to adjacent group members
        for be in bucket_edges:
            if be.is_adjacent_group_member and be.recommendation in ["BUY", "STRONG_BUY"]:
                be.conviction = min(1.0, be.conviction * 1.15)
                logger.debug(f"Spread bonus applied to {be.label}: conviction → {be.conviction:.3f}")

        # Apply isolation penalty to isolated buckets
        for be in bucket_edges:
            if not be.is_adjacent_group_member and be.recommendation in ["BUY", "STRONG_BUY"] and be.conviction < 0.80:
                old_conviction = be.conviction
                be.conviction *= 0.80
                logger.debug(f"Isolation penalty applied to {be.label}: conviction {old_conviction:.3f} → {be.conviction:.3f}")

        # Re-evaluate recommendations after conviction adjustments
        for be in bucket_edges:
            if safety_override:
                be.recommendation = "SKIP"
            elif be.edge >= min_edge * 2 and be.conviction >= 0.80:
                be.recommendation = "STRONG_BUY"
            elif be.edge >= min_edge:
                be.recommendation = "BUY"
            elif be.edge <= -min_edge:
                be.recommendation = "SELL_NO"
            else:
                be.recommendation = "SKIP"

        # Compute market-level outputs
        buy_buckets = [be for be in bucket_edges if be.recommendation in ["BUY", "STRONG_BUY"]]
        overall_ev = sum(be.edge * be.conviction for be in buy_buckets)

        # Top buckets (up to 3, sorted by conviction descending)
        top_buckets = sorted(
            [be for be in bucket_edges if be.recommendation in ["BUY", "STRONG_BUY"]],
            key=lambda x: x.conviction,
            reverse=True
        )[:3]
        top_bucket_labels = [be.label for be in top_buckets]

        # Recommended exposure
        if not buy_buckets or confidence_score < 40:
            recommended_exposure = "NONE"
        elif confidence_score < 55:
            recommended_exposure = "LOW"
        elif confidence_score < 70:
            recommended_exposure = "MEDIUM"
        else:
            recommended_exposure = "HIGH"

        # Reasoning summary
        reasoning = f"{len(buy_buckets)} BUY opportunities, overall EV: {overall_ev:.3f}, confidence: {confidence_score:.1f}/100"
        if global_risk_flags:
            reasoning += f", risk flags: {', '.join(global_risk_flags)}"

        summary = MarketEdgeSummary(
            station_id=station_id,
            confidence_score=confidence_score,
            overall_ev=overall_ev,
            bucket_edges=bucket_edges,
            top_buckets=top_bucket_labels,
            recommended_exposure=recommended_exposure,
            risk_flags=global_risk_flags,
            reasoning=reasoning
        )

        logger.info(f"Edge summary for {station_id}: {recommended_exposure} exposure, EV={overall_ev:.3f}")
        return summary

    def _compute_confidence_score(self,
                                  weather_data: LocationWeatherData,
                                  station_id: str) -> Tuple[float, List[str]]:
        """
        Compute 4-factor confidence score (0–100) and active risk flags.

        Factors weighted by config.confidence_formula_weights (default all 25 pts each):
        1. Ensemble Tightness - low temperature std = high confidence
        2. Bias Stability - low bias std = high confidence
        3. Data Freshness - recent data = high confidence
        4. Volatility Indicators - low wind/cloud/pressure variability = high confidence

        Each factor contributes up to its configured weight (default 25 pts, total 100 max).
        All factors are equally weighted by default but can be tuned per-city/season.

        Args:
            weather_data: LocationWeatherData object
            station_id: Station identifier

        Returns:
            Tuple of (confidence_score 0-100, list of active risk flags)
        """
        risk_flags = []

        # Get configured max points per factor (default 25 each)
        max_ensemble = self.config.confidence_formula_weights.get("ensemble", 25)
        max_bias = self.config.confidence_formula_weights.get("bias", 25)
        max_freshness = self.config.confidence_formula_weights.get("freshness", 25)
        max_volatility = self.config.confidence_formula_weights.get("volatility", 25)

        # Factor 1: Ensemble Tightness (temperature std)
        # Default fallback: 40% of max (neutral when no ensemble data)
        f1_points = int(max_ensemble * 0.4)
        ensemble_stds = []
        if weather_data.ensemble_forecast:
            for ep in weather_data.ensemble_forecast:
                if ep.temperature_std is not None:
                    ensemble_stds.append(ep.temperature_std)

        if ensemble_stds:
            avg_temp_std = statistics.mean(ensemble_stds)
            # Thresholds: 1.0°, 2.0°, 3.0°, 4.5° → award proportional points
            if avg_temp_std <= 1.0:
                f1_points = max_ensemble
            elif avg_temp_std <= 2.0:
                f1_points = int(max_ensemble * (20/25))
            elif avg_temp_std <= 3.0:
                f1_points = int(max_ensemble * (13/25))
            elif avg_temp_std <= 4.5:
                f1_points = int(max_ensemble * (6/25))
            else:
                f1_points = 0
                risk_flags.append("high_temp_std")

        if ensemble_stds and statistics.mean(ensemble_stds) > 3.5:
            if "high_temp_std" not in risk_flags:
                risk_flags.append("high_temp_std")

        # Factor 2: Bias Stability
        bias_std = self.bias_learner.get_bias_std(station_id)
        if bias_std <= 0.5:
            f2_points = max_bias
        elif bias_std <= 0.75:
            f2_points = int(max_bias * (22/25))
        elif bias_std <= 1.0:
            f2_points = int(max_bias * (17/25))
        elif bias_std <= 1.5:
            f2_points = int(max_bias * (10/25))
        elif bias_std <= 2.5:
            f2_points = int(max_bias * (5/25))
        else:
            f2_points = 0
            risk_flags.append("unstable_bias")

        # Factor 3: Data Freshness
        age_minutes = (datetime.now(timezone.utc) - weather_data.last_updated).total_seconds() / 60.0
        if age_minutes <= 15:
            f3_points = max_freshness
        elif age_minutes <= 30:
            f3_points = int(max_freshness * (20/25))
        elif age_minutes <= 60:
            f3_points = int(max_freshness * (13/25))
        elif age_minutes <= 120:
            f3_points = int(max_freshness * (6/25))
        else:
            f3_points = 0

        if age_minutes > 90:
            risk_flags.append("stale_data")

        # Factor 4: Volatility Indicators (wind, cloud, pressure)
        # Three independent penalties that reduce from max_volatility
        wind_penalty = 0
        cloud_penalty = 0
        pressure_penalty = 0

        if weather_data.ensemble_forecast:
            wind_stds = []
            for ep in weather_data.ensemble_forecast:
                if ep.wind_speed_std is not None:
                    wind_stds.append(ep.wind_speed_std)
            if wind_stds:
                avg_wind_std = statistics.mean(wind_stds)
                if avg_wind_std > 5:
                    wind_penalty = min(10, (avg_wind_std - 5) * 2)
                if avg_wind_std > 10:
                    risk_flags.append("high_wind_volatility")

        if weather_data.hourly_forecast:
            cloud_covers = [p.cloud_cover for p in weather_data.hourly_forecast[:24] if p.cloud_cover is not None]
            if cloud_covers and len(cloud_covers) >= 2:
                cloud_std = statistics.stdev(cloud_covers) if len(cloud_covers) > 1 else 0
                if cloud_std > 15:
                    cloud_penalty = min(10, (cloud_std - 15) * 0.5)
                if cloud_std > 30:
                    risk_flags.append("high_cloud_variability")

            pressures = [p.pressure for p in weather_data.hourly_forecast[:24] if p.pressure is not None]
            if pressures and len(pressures) >= 2:
                pressure_std = statistics.stdev(pressures) if len(pressures) > 1 else 0
                if pressure_std > 2:
                    pressure_penalty = min(5, (pressure_std - 2) * 1.5)
                if pressure_std > 5:
                    risk_flags.append("high_pressure_variability")

        f4_points = max(0, max_volatility - wind_penalty - cloud_penalty - pressure_penalty)

        # Total confidence (can exceed 100 if weights are customized, but typically 100)
        confidence_score = f1_points + f2_points + f3_points + f4_points
        logger.debug(f"Confidence factors: F1={f1_points}/{max_ensemble}, F2={f2_points}/{max_bias}, F3={f3_points}/{max_freshness}, F4={f4_points}/{max_volatility}")

        return confidence_score, risk_flags

    def _apply_risk_modifiers(self,
                             base_conviction: float,
                             weather_data: LocationWeatherData) -> Tuple[float, List[str]]:
        """
        Apply compounding risk multipliers to reduce conviction under volatile conditions.

        Multipliers stack:
        - High temp_std: ×0.60 (very_high) or ×0.80 (high)
        - High wind_std: ×0.70 (very_high) or ×0.88 (elevated)
        - High cloud_std: ×0.75 (very_high) or ×0.90 (elevated)

        Args:
            base_conviction: Starting conviction (0–1)
            weather_data: LocationWeatherData object

        Returns:
            Tuple of (adjusted_conviction, list of fired_flags)
        """
        conviction = base_conviction
        fired_flags = []

        # Temperature std penalties
        avg_temp_std = 0
        if weather_data.ensemble_forecast:
            stds = [ep.temperature_std for ep in weather_data.ensemble_forecast if ep.temperature_std is not None]
            if stds:
                avg_temp_std = statistics.mean(stds)

        if avg_temp_std > 4.5:
            conviction *= 0.60
            fired_flags.append("very_high_temp_std")
        elif avg_temp_std > 3.0:
            conviction *= 0.80
            fired_flags.append("high_temp_std")

        # Wind std penalties
        avg_wind_std = 0
        if weather_data.ensemble_forecast:
            wstds = [ep.wind_speed_std for ep in weather_data.ensemble_forecast if ep.wind_speed_std is not None]
            if wstds:
                avg_wind_std = statistics.mean(wstds)

        if avg_wind_std > 15:
            conviction *= 0.70
            fired_flags.append("very_high_wind_std")
        elif avg_wind_std > 8:
            conviction *= 0.88
            fired_flags.append("elevated_wind_std")

        # Cloud variability penalties
        cloud_std = 0
        if weather_data.hourly_forecast:
            clouds = [p.cloud_cover for p in weather_data.hourly_forecast[:24] if p.cloud_cover is not None]
            if clouds and len(clouds) > 1:
                cloud_std = statistics.stdev(clouds)

        if cloud_std > 35:
            conviction *= 0.75
            fired_flags.append("very_high_cloud_variability")
        elif cloud_std > 22:
            conviction *= 0.90
            fired_flags.append("elevated_cloud_variability")

        conviction = max(0.0, min(1.0, conviction))
        return conviction, fired_flags

    def _detect_adjacent_groups(self,
                               bucket_edges: List[BucketEdge],
                               buckets: List[Bucket]) -> List[BucketEdge]:
        """
        Identify runs of 2+ consecutive buckets with positive edge.

        Marks adjacent group members with is_adjacent_group_member=True and assigns group_id.
        Encourages spreading strategies by clustering related opportunities.

        Args:
            bucket_edges: List of BucketEdge objects (unsorted initially)
            buckets: List of Bucket objects (must be ordered low→high)

        Returns:
            Updated bucket_edges with adjacency information populated
        """
        # Build edge map
        edge_map = {be.label: be for be in bucket_edges}

        # Build positive edge set
        positive_set = {be.label for be in bucket_edges if be.edge > 0}

        logger.debug(f"Detecting adjacent groups: {len(positive_set)} buckets with positive edge")

        # Walk buckets in order, identifying runs
        current_run = []
        group_id = 0

        for bucket in buckets:
            if bucket.label in edge_map:
                if bucket.label in positive_set:
                    # Extend current run
                    current_run.append(bucket.label)
                else:
                    # End of run
                    if len(current_run) >= 2:
                        for label in current_run:
                            edge_map[label].is_adjacent_group_member = True
                            edge_map[label].group_id = group_id
                        group_id += 1
                    current_run = []

        # Flush remaining run
        if len(current_run) >= 2:
            for label in current_run:
                edge_map[label].is_adjacent_group_member = True
                edge_map[label].group_id = group_id

        return list(edge_map.values())


# ============================================================================
# PHASE 4: Backtesting Framework
# ============================================================================

class BacktestRunner:
    """
    Replay sequences of historical (LocationWeatherData, actual_temperature) pairs
    through WeatherPredictor and compute calibration metrics.

    Brier Score formula: BS = (1/N) * Σ(p_i - o_i)²
      p_i = predicted probability for bucket i
      o_i = 1 if that bucket resolved, 0 otherwise
      N   = total number of buckets per observation

    Hit Rate: fraction of observations where the max-probability bucket resolved.
    Calibration Sharpness: variance of predicted probabilities for the correct buckets
      (higher = more confident in correct predictions).
    """

    def __init__(
        self,
        predictor: 'WeatherPredictor',
        buckets: List[Bucket],
        station_id: str,
        min_edge: float = 0.10,
    ):
        """
        Initialize the BacktestRunner.

        Args:
            predictor: WeatherPredictor instance (already configured)
            buckets: List of Bucket objects — the market structure
            station_id: Station code for bias lookups and edge analysis
            min_edge: Edge threshold passed to calculate_edge()
        """
        self.predictor = predictor
        self.buckets = buckets
        self.station_id = station_id
        self.min_edge = min_edge
        self._observations: List[Dict] = []

    def add_observation(
        self,
        weather_data: LocationWeatherData,
        actual_temperature: float,
        market_prices: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Record one historical data point for replay.

        Args:
            weather_data: LocationWeatherData as it existed at prediction time
            actual_temperature: Observed high temperature (ground truth)
            market_prices: Optional Kalshi prices at prediction time (for EV tracking)
        """
        self._observations.append({
            'weather_data': weather_data,
            'actual_temperature': actual_temperature,
            'market_prices': market_prices,
        })

    def run(self) -> BacktestResult:
        """
        Replay all added observations and compute aggregate metrics.

        Returns:
            BacktestResult with comprehensive calibration and performance metrics
        """
        if not self._observations:
            logger.warning("BacktestRunner.run() called with no observations")
            return BacktestResult(
                n_resolved=0,
                brier_score=0.0,
                hit_rate=0.0,
                avg_confidence=0.0,
                per_observation=[],
            )

        per_obs_records = []
        brier_scores = []
        hits = []
        confidences = []
        evs = []

        for obs in self._observations:
            weather_data = obs['weather_data']
            actual_temp = obs['actual_temperature']
            market_prices = obs['market_prices']

            # Get model probabilities
            model_probs_dict = self.predictor.hybrid_bucket_probabilities(
                weather_data=weather_data,
                buckets=self.buckets,
                station_id=self.station_id,
            )
            model_probs = {label: data['probability'] for label, data in model_probs_dict.items()}

            # Compute Brier Score
            bs = self.brier_score(model_probs, actual_temp, self.buckets)
            brier_scores.append(bs)

            # Determine hit: find max-prob bucket
            max_prob_label = max(model_probs.items(), key=lambda x: x[1])[0]
            max_prob_bucket = next((b for b in self.buckets if b.label == max_prob_label), None)
            is_hit = max_prob_bucket and max_prob_bucket.contains(actual_temp) if max_prob_bucket else False
            hits.append(1.0 if is_hit else 0.0)

            # Get confidence score
            confidence, _ = self.predictor._compute_confidence_score(weather_data, self.station_id)
            confidences.append(confidence)

            # Optionally compute EV if market prices provided
            overall_ev = 0.0
            if market_prices:
                summary = self.predictor.calculate_edge(
                    model_probs=model_probs,
                    market_prices=market_prices,
                    buckets=self.buckets,
                    station_id=self.station_id,
                    weather_data=weather_data,
                    min_edge=self.min_edge,
                )
                overall_ev = summary.overall_ev
                evs.append(overall_ev)

            # Record per-observation data
            per_obs_records.append({
                'actual_temperature': actual_temp,
                'brier_score': bs,
                'hit': is_hit,
                'confidence': confidence,
                'overall_ev': overall_ev,
                'max_prob_bucket': max_prob_label,
            })

        # Compute aggregates
        mean_brier = statistics.mean(brier_scores) if brier_scores else 0.0
        mean_hit = statistics.mean(hits) if hits else 0.0
        mean_confidence = statistics.mean(confidences) if confidences else 0.0
        mean_ev = statistics.mean(evs) if evs else None

        # Compute calibration sharpness: variance of probs for resolved buckets
        resolved_probs = []
        for obs, rec in zip(self._observations, per_obs_records):
            weather_data = obs['weather_data']
            actual_temp = obs['actual_temperature']
            model_probs_dict = self.predictor.hybrid_bucket_probabilities(
                weather_data=weather_data,
                buckets=self.buckets,
                station_id=self.station_id,
            )
            model_probs = {label: data['probability'] for label, data in model_probs_dict.items()}
            # Find bucket containing actual temperature
            for bucket in self.buckets:
                if bucket.contains(actual_temp):
                    resolved_probs.append(model_probs.get(bucket.label, 0.0))
                    break

        calibration_sharpness = statistics.variance(resolved_probs) if len(resolved_probs) > 1 else None

        return BacktestResult(
            n_resolved=len(self._observations),
            brier_score=mean_brier,
            hit_rate=mean_hit,
            avg_confidence=mean_confidence,
            per_observation=per_obs_records,
            simulated_roi=mean_ev,
            calibration_sharpness=calibration_sharpness,
        )

    @staticmethod
    def brier_score(
        probs: Dict[str, float],
        actual_temperature: float,
        buckets: List[Bucket],
    ) -> float:
        """
        Compute Brier Score for a single observation.

        Brier Score measures the accuracy of predicted probabilities.
        BS = (1/N) * Σ(p_i - o_i)² where:
          p_i = predicted probability for bucket i
          o_i = 1 if bucket i resolved, 0 otherwise
          N   = total number of buckets

        BS ranges from 0 (perfect) to 1 (worst).

        Args:
            probs: Dict of bucket label → predicted probability
            actual_temperature: Observed temperature (ground truth)
            buckets: List of Bucket objects defining the probability space

        Returns:
            Brier Score (float, 0-1)
        """
        total = 0.0
        n = len(buckets)

        for bucket in buckets:
            p_i = probs.get(bucket.label, 0.0)
            o_i = 1.0 if bucket.contains(actual_temperature) else 0.0
            total += (p_i - o_i) ** 2

        return total / n if n > 0 else 0.0


# ============================================================================
# Helper Functions
# ============================================================================

def parse_bucket_string(bucket_str: str, unit: str = 'F') -> Bucket:
    """
    Parse a Kalshi market bucket label into a Bucket object.

    Supports all common bucket formats:
        "92-93"          → low=92, high=93 (plain integer range)
        "92-93°F"        → low=92, high=93 (with unit suffix)
        "20-21°C"        → low=20, high=21 (Celsius)
        ">=95", "≥95"    → low=95, high=float('inf') (open-ended high)
        "<80", "≤80"     → low=float('-inf'), high=80 (open-ended low)
        "95+", "70-"     → open-ended ranges
        "-5-0"           → handles negative temperatures

    Auto-detects unit suffix (°F, °C) and overrides the unit parameter if found.
    Open-ended buckets use float('inf') and float('-inf') for the unbounded side.

    Args:
        bucket_str: Bucket label string (e.g., "92-93", "20-21°C", ">=95")
        unit: Temperature unit ('F' or 'C') — overridden if unit suffix detected

    Returns:
        Bucket object with properly set low, high, and canonical label

    Raises:
        ValueError: If the string format is not recognized or low >= high
    """
    working_str = bucket_str.strip()
    detected_unit = unit

    # Step 1: Detect and strip unit suffix (°F, °C, etc.)
    unit_match = re.search(r'°([FC])|([FC])$', working_str)
    if unit_match:
        detected_unit = unit_match.group(1) or unit_match.group(2)
        working_str = re.sub(r'°?[FC]$', '', working_str).strip()

    # Step 2: Check for open-ended patterns (before range split)
    # >= or ≥ patterns
    open_high_match = re.match(r'^(>=|≥|=>)\s*(-?\d+\.?\d*)$', working_str)
    if open_high_match:
        value = float(open_high_match.group(2))
        label = f"≥{int(value) if value == int(value) else value}"
        return Bucket(low=value, high=float('inf'), label=label)

    # Trailing + pattern (e.g., "95+")
    plus_match = re.match(r'^(-?\d+\.?\d*)\+$', working_str)
    if plus_match:
        value = float(plus_match.group(1))
        label = f"≥{int(value) if value == int(value) else value}"
        return Bucket(low=value, high=float('inf'), label=label)

    # <= or ≤ patterns
    open_low_match = re.match(r'^(<=|≤|=<|<)\s*(-?\d+\.?\d*)$', working_str)
    if open_low_match:
        value = float(open_low_match.group(2))
        label = f"<{int(value) if value == int(value) else value}"
        return Bucket(low=float('-inf'), high=value, label=label)

    # Trailing - pattern (e.g., "70-")
    minus_match = re.match(r'^(-?\d+\.?\d*)-$', working_str)
    if minus_match:
        value = float(minus_match.group(1))
        label = f"<{int(value) if value == int(value) else value}"
        return Bucket(low=float('-inf'), high=value, label=label)

    # Step 3: Range pattern with regex to handle negatives safely
    range_match = re.match(r'^(-?\d+\.?\d*)-(-?\d+\.?\d*)$', working_str)
    if range_match:
        low_str = range_match.group(1)
        high_str = range_match.group(2)
        low = float(low_str)
        high = float(high_str)

        if low >= high:
            raise ValueError(f"Invalid bucket range: low ({low}) must be < high ({high})")

        # Canonical label: use integers if possible
        low_label = int(low) if low == int(low) else low
        high_label = int(high) if high == int(high) else high
        label = f"{low_label}-{high_label}"

        return Bucket(low=low, high=high, label=label)

    # If we reach here, the format was not recognized
    raise ValueError(
        f"Invalid bucket string format: '{bucket_str}'. "
        "Expected formats: '92-93', '20-21°C', '>=95', '<80', '95+', '70-'"
    )


def create_buckets_from_range(low: float, high: float, unit: str = 'F', step: float = 1.0) -> List[Bucket]:
    """
    Create a list of consecutive temperature buckets covering a range.

    Generates buckets from low to high with the specified step size.
    Default step=1.0 creates 1-degree buckets (the most common case).

    Args:
        low: Lower bound (inclusive)
        high: Upper bound (exclusive)
        unit: Temperature unit ('F' or 'C')
        step: Bucket size (default 1.0 for 1-degree buckets)

    Returns:
        List of Bucket objects ordered from low to high

    Examples:
        create_buckets_from_range(88, 95, unit='F')     # [88-89, 89-90, ..., 94-95]
        create_buckets_from_range(20, 28, unit='C', step=0.5)  # [20-20.5, 20.5-21, ...]
    """
    buckets = []
    current = low

    while current < high:
        next_val = current + step
        # Format label: use integers if both bounds are integers, else use 1 decimal
        if current == int(current) and next_val == int(next_val):
            label = f"{int(current)}-{int(next_val)}"
        else:
            label = f"{current:.1f}-{next_val:.1f}"

        bucket = Bucket(low=current, high=next_val, label=label)
        buckets.append(bucket)
        current = next_val

    return buckets
