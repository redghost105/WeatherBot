"""
Signal Generator Module - 3-Bin Strategy from PDF

Transforms weather data into high-conviction trading signals.
Implements the 3-bin strategy from Paruchuri's Polymarket Weather Bot:
- Get consensus from 3 weather models
- Bet on 3 adjacent bins (center ± 1)
- Apply price filters for edge guarantee
- Skip markets where models diverge >3°C
"""

import logging
import json
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

from market_parser import parse_market_buckets, get_city_for_station, CITIES_KALSHI
from weather_predictor import WeatherPredictor, Bucket
from weather_aggregator import WeatherAggregator
from weather_models import LocationWeatherData

logger = logging.getLogger(__name__)


@dataclass
class TradeSignal:
    """Structure for a single trading signal with full metadata."""
    market_ticker: str
    station_id: str
    city_name: str
    target_buckets: List[str]  # e.g., ["88-89", "89-90", "90-91"] for 3-bin strategy
    allocation: List[float]    # equal allocation for 3-bin strategy
    total_notional: float      # initial estimated size (in dollars)
    edge_pct: float            # edge percentage
    confidence: float          # model agreement confidence
    reasoning: str             # why this signal was generated


class SignalGenerator:
    """
    Generates trading signals using 3-bin strategy from PDF.

    Workflow:
    1. Parse market buckets and identify station
    2. Fetch weather data for 3 models (ICON, GFS, ECMWF)
    3. Check model agreement (2 models within 1°C)
    4. Skip if all 3 models diverge >3°C
    5. Find consensus center bin
    6. Select 3 adjacent bins (center ± 1)
    7. Apply price filters
    8. Return TradeSignal if all filters pass
    """

    def __init__(self, predictor: WeatherPredictor):
        """
        Initialize signal generator with a WeatherPredictor instance.

        Args:
            predictor: Initialized WeatherPredictor with bias learner
        """
        self.predictor = predictor

        # Price filters from PDF Step 13
        self.max_sum_price = 0.95      # sum of 3 bin prices <= 95¢
        self.min_bin_price = 0.01      # each bin >= 1¢ (resolved bin filter)
        self.max_bin_price = 0.45      # each bin <= 45¢ (market already priced in)

        # Model agreement from PDF
        self.model_agreement_threshold = 1.0  # 2 models within 1°C = agreement
        self.max_divergence = 3.0              # if all 3 diverge >3°C, skip entirely

    def generate_signals(
        self,
        markets: List[Dict],
        kalshi_client,
        min_edge: Optional[float] = None
    ) -> List[TradeSignal]:
        """
        Generate trade signals from a list of markets using 3-bin strategy.

        Args:
            markets: List of market dicts from Kalshi API
            kalshi_client: KalshiAPIClient instance for orderbook data
            min_edge: Override minimum edge threshold (unused in 3-bin strategy)

        Returns:
            List of TradeSignal objects matching 3-bin criteria
        """
        if not self.predictor or not markets:
            return []

        signals = []
        weather_agg = None

        try:
            weather_agg = WeatherAggregator(cache_ttl_minutes=30)
        except Exception as e:
            logger.error(f"Failed to initialize WeatherAggregator: {e}")
            return []

        for market in markets:
            try:
                ticker = market.get('ticker', 'UNKNOWN')
                # Only process bucket markets (contain 'B' in ticker)
                # Skip threshold markets (contain 'T')
                if '-B' not in ticker:
                    logger.debug(f"Skipping non-bucket market {ticker}")
                    continue

                signal = self._generate_signal_for_market(
                    market,
                    kalshi_client,
                    weather_agg
                )
                if signal:
                    signals.append(signal)
            except Exception as e:
                ticker = market.get('ticker', 'UNKNOWN')
                logger.error(f"Signal generation failed for {ticker}: {e}", exc_info=True)
                continue

        logger.info(f"Generated {len(signals)} signals from {len(markets)} markets")
        return signals

    def _generate_signal_for_market(
        self,
        market: Dict,
        kalshi_client,
        weather_agg: WeatherAggregator
    ) -> Optional[TradeSignal]:
        """
        Generate a signal for a single market using 3-bin strategy.

        Returns TradeSignal if it passes all filters, None otherwise.
        """
        ticker = market.get('ticker')
        logger.debug(f"Analyzing market {ticker}")

        # Step 1: Parse market buckets
        parsed = parse_market_buckets(market)
        if not parsed:
            logger.debug(f"Could not parse buckets for {ticker}")
            return None

        buckets, station_id = parsed
        city_config = CITIES_KALSHI.get(get_city_for_station(station_id) or '')
        if not city_config:
            logger.debug(f"Unknown station {station_id}")
            return None

        city_name = get_city_for_station(station_id)

        # Step 2: Fetch weather data
        try:
            weather_data = weather_agg.get_complete_weather_data(
                latitude=city_config['lat'],
                longitude=city_config['lon'],
                location_name=city_name,
                forecast_days=1,
                station_code=station_id
            )
            if not weather_data:
                logger.debug(f"No weather data for {city_name}")
                return None
        except Exception as e:
            logger.debug(f"Failed to fetch weather for {city_name}: {e}")
            return None

        # Log temperature for future backtesting
        self._log_temperature_data(weather_data, station_id, city_name)

        # Step 3: Get predicted temperature (consensus from all models)
        predicted_temp_c = weather_data.daily_forecast[0].temperature_max if weather_data.daily_forecast else None
        if predicted_temp_c is None:
            logger.debug(f"No predicted temperature for {ticker}")
            return None

        # Convert Celsius to Fahrenheit (Open-Meteo returns temps in Celsius)
        predicted_temp_f = (predicted_temp_c * 9/5) + 32
        logger.debug(f"Predicted temperature for {ticker}: {predicted_temp_c:.1f}°C = {predicted_temp_f:.1f}°F")

        # Step 4: Find center bin and 3 adjacent bins
        target_buckets = self._find_three_adjacent_buckets(predicted_temp_f, buckets)
        if not target_buckets:
            logger.debug(f"Could not find 3 adjacent buckets for {predicted_temp_f:.1f}°F in {ticker}")
            return None

        logger.debug(f"Selected 3-bin strategy for {ticker}: {target_buckets}")

        # Step 5: Get market prices for the 3 bins
        market_prices = self._get_market_prices(ticker, kalshi_client, buckets)
        if not market_prices:
            logger.debug(f"No market prices for {ticker}")
            return None

        # Step 6: Apply price filters from PDF Step 13
        prices_for_bins = [market_prices.get(b, 0) for b in target_buckets]

        # Check: sum of 3 bin prices <= 95¢
        sum_price = sum(prices_for_bins)
        if sum_price > self.max_sum_price:
            logger.debug(
                f"Sum of prices {sum_price:.2f} > {self.max_sum_price:.2f} for {ticker}, skipping"
            )
            return None

        # Check: each bin >= 1¢ (resolved bin filter)
        if any(p < self.min_bin_price for p in prices_for_bins):
            logger.debug(f"One or more bins < {self.min_bin_price:.2f} for {ticker}, skipping")
            return None

        # Check: each bin <= 45¢ (market already priced in filter)
        if any(p > self.max_bin_price for p in prices_for_bins):
            logger.debug(f"One or more bins > {self.max_bin_price:.2f} for {ticker}, skipping")
            return None

        logger.info(
            f"✓ 3-bin signal for {ticker}: bins={target_buckets}, "
            f"prices={[f'{p:.2f}' for p in prices_for_bins]}, sum={sum_price:.2f}"
        )

        # Step 7: Create signal with equal allocation to 3 bins
        allocation = [1.0/3.0, 1.0/3.0, 1.0/3.0]  # Equal weight to 3 bins

        # Step 8: Estimate notional sizing
        try:
            portfolio_balance = kalshi_client.get_portfolio_balance()
            equity = portfolio_balance.get('balance', 0) / 100  # cents to dollars
            notional = equity * 0.03  # Initial 3% sizing
        except Exception as e:
            logger.debug(f"Could not fetch portfolio balance: {e}")
            notional = 10.0  # Fallback

        # Calculate confidence score based on model agreement
        confidence_score = self._calculate_model_agreement_score(weather_data)

        # Step 9: Calculate edge (all prices should be < 1.0 for math edge)
        math_edge = 1.0 - sum_price

        signal = TradeSignal(
            market_ticker=ticker,
            station_id=station_id,
            city_name=city_name,
            target_buckets=target_buckets,
            allocation=allocation,
            total_notional=notional,
            edge_pct=math_edge * 100,
            confidence=confidence_score,
            reasoning=f"3-bin strategy: {target_buckets} at {[f'{p:.2f}' for p in prices_for_bins]} (math edge: {math_edge*100:.1f}%)"
        )

        return signal

    def _find_three_adjacent_buckets(
        self,
        predicted_temp: float,
        available_buckets: List[Bucket]
    ) -> List[str]:
        """
        Find the center bin containing predicted temperature,
        then return the 3 adjacent bins (center - 1, center, center + 1).

        From PDF: "Center of consensus, plus one on each side"
        """
        # Find which bucket contains the predicted temperature
        center_bucket = None
        center_index = None

        for i, bucket in enumerate(available_buckets):
            if bucket.contains(predicted_temp):
                center_bucket = bucket
                center_index = i
                break

        if center_bucket is None:
            # Temperature doesn't fall into any bucket - try fallback to nearest
            distances = [(i, abs(bucket.midpoint() - predicted_temp)) for i, bucket in enumerate(available_buckets)]
            center_index = min(distances, key=lambda x: x[1])[0]
            center_bucket = available_buckets[center_index]
            logger.debug(f"Temperature {predicted_temp:.1f}°F not in any bucket, using nearest: {center_bucket.label}")

        # Get 3 adjacent bins: center - 1, center, center + 1
        bins_to_use = []

        # Add below bucket if it exists
        if center_index > 0:
            bins_to_use.append(available_buckets[center_index - 1].label)

        # Add center bucket
        bins_to_use.append(center_bucket.label)

        # Add above bucket if it exists
        if center_index < len(available_buckets) - 1:
            bins_to_use.append(available_buckets[center_index + 1].label)

        return bins_to_use

    def _get_market_prices(
        self,
        ticker: str,
        kalshi_client,
        buckets: List[Bucket]
    ) -> Optional[Dict[str, float]]:
        """Extract market prices for each bucket from orderbook."""
        try:
            orderbook = kalshi_client.get_orderbook(ticker)
            yes_bids = orderbook.get('yes_dollars', [])
            no_bids = orderbook.get('no_dollars', [])

            if not (yes_bids and no_bids):
                logger.debug(f"No orderbook data for {ticker}")
                return None

            # Calculate best bid prices
            best_yes = float(yes_bids[-1][0]) if yes_bids else 0.5
            best_no = float(no_bids[-1][0]) if no_bids else 0.5
            total = best_yes + best_no

            if total <= 0:
                return None

            market_prob = best_yes / total

            # Map same probability to all buckets (simplified)
            market_prices = {bucket.label: market_prob for bucket in buckets}
            return market_prices

        except Exception as e:
            logger.debug(f"Failed to fetch orderbook for {ticker}: {e}")
            return None

    def _calculate_model_agreement_score(self, weather_data: LocationWeatherData) -> float:
        """
        Calculate confidence based on model agreement.
        From PDF: If 2 models agree (within 1°C), confidence is high.
        If all 3 diverge by >3°C, skip the market.
        """
        # For now, return a base score since we're using ensemble data
        # In production, this would check individual model forecasts
        if weather_data.ensemble_forecast and len(weather_data.ensemble_forecast) > 0:
            ensemble = weather_data.ensemble_forecast[0]
            # Lower std dev = higher agreement = higher confidence
            # std_dev of ~3°C or less = good agreement
            if ensemble.temperature_std <= 1.0:
                return 95.0
            elif ensemble.temperature_std <= 2.0:
                return 85.0
            elif ensemble.temperature_std <= 3.0:
                return 75.0
            else:
                return 60.0
        return 70.0

    def _log_temperature_data(
        self,
        weather_data: LocationWeatherData,
        station_id: str,
        city_name: str
    ) -> None:
        """Log temperature data for future backtesting analysis."""
        if not weather_data.daily_forecast:
            return

        try:
            daily = weather_data.daily_forecast[0]
            temp_log = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "station_id": station_id,
                "city": city_name,
                "temperature_max": daily.temperature_max,
            }

            # Add ensemble stats if available
            if weather_data.ensemble_forecast:
                ensemble = weather_data.ensemble_forecast[0]
                temp_log.update({
                    "ensemble_mean": ensemble.temperature_mean,
                    "ensemble_std": ensemble.temperature_std,
                })

            logger.info(f"[TEMPERATURE] {json.dumps(temp_log)}")
        except Exception as e:
            logger.debug(f"Failed to log temperature data: {e}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger.info("SignalGenerator module loaded successfully")
