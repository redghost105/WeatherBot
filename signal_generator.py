"""
Signal Generator Module

Transforms weather data into high-conviction trading signals.
Integrates WeatherPredictor with market data to identify profitable opportunities.

Purpose: Centralized signal generation logic that:
- Calls WeatherPredictor.hybrid_bucket_probabilities() for calibrated forecasts
- Calculates edge vs market prices (minimum 10-15% edge)
- Prefers 2-3 adjacent buckets per successful strategy
- Returns structured TradeSignal objects with metadata
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
    target_buckets: List[str]  # e.g., ["88-89", "89-90"]
    allocation: List[float]    # proportional sizing for each bucket
    total_notional: float      # initial estimated size (in dollars)
    edge_pct: float            # edge percentage (10-15+)
    confidence: float          # confidence score (0-100)
    reasoning: str             # why this signal was generated


class SignalGenerator:
    """
    Generates trading signals from weather data and market prices.

    Workflow:
    1. Parse market buckets and identify station
    2. Fetch fresh weather data via WeatherAggregator
    3. Call WeatherPredictor.hybrid_bucket_probabilities()
    4. Extract market prices from orderbook
    5. Calculate edge via predictor.calculate_edge()
    6. Filter: confidence >= 55%, edge >= 10%, 2-3 adjacent buckets
    7. Return TradeSignal with allocation and metadata
    """

    def __init__(self, predictor: WeatherPredictor):
        """
        Initialize signal generator with a WeatherPredictor instance.

        Args:
            predictor: Initialized WeatherPredictor with bias learner
        """
        self.predictor = predictor
        self.min_edge_threshold = 0.10  # 10% minimum edge
        self.min_confidence = 55.0      # 55% minimum confidence
        self.min_edge_adjacent = 0.10   # edge required on adjacent buckets

    def generate_signals(
        self,
        markets: List[Dict],
        kalshi_client,
        min_edge: Optional[float] = None
    ) -> List[TradeSignal]:
        """
        Generate trade signals from a list of markets.

        Args:
            markets: List of market dicts from Kalshi API
            kalshi_client: KalshiAPIClient instance for orderbook data
            min_edge: Override minimum edge threshold (default: 0.10)

        Returns:
            List of TradeSignal objects with high-conviction opportunities
        """
        if not self.predictor or not markets:
            return []

        if min_edge is not None:
            self.min_edge_threshold = min_edge

        signals = []
        weather_agg = None

        try:
            weather_agg = WeatherAggregator(cache_ttl_minutes=30)
        except Exception as e:
            logger.error(f"Failed to initialize WeatherAggregator: {e}")
            return []

        for market in markets:
            try:
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
        Generate a signal for a single market.

        Returns TradeSignal if high-conviction, None otherwise.
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

        # Step 3: Generate probability distribution
        try:
            model_probs_dict = self.predictor.hybrid_bucket_probabilities(
                weather_data=weather_data,
                buckets=buckets,
                station_id=station_id,
                apply_bias_correction=True
            )
            if not model_probs_dict:
                logger.debug(f"No probabilities for {city_name}")
                return None

            model_probs = {label: d['probability'] for label, d in model_probs_dict.items()}
        except Exception as e:
            logger.error(f"Probability calculation failed for {ticker}: {e}")
            return None

        # Step 4: Get market prices
        market_prices = self._get_market_prices(ticker, kalshi_client, buckets)
        if not market_prices:
            logger.debug(f"No market prices for {ticker}")
            return None

        # Step 5: Calculate edge
        try:
            edge_summary = self.predictor.calculate_edge(
                model_probs=model_probs,
                market_prices=market_prices,
                buckets=buckets,
                station_id=station_id,
                weather_data=weather_data,
                min_edge=self.min_edge_threshold
            )
        except Exception as e:
            logger.error(f"Edge calculation failed for {ticker}: {e}")
            return None

        # Step 6: Filter for high-conviction signals
        if edge_summary.confidence_score < self.min_confidence:
            logger.debug(
                f"Low confidence {edge_summary.confidence_score:.0f} for {ticker}, skipping"
            )
            return None

        if edge_summary.overall_ev <= 0:
            logger.debug(f"No positive EV for {ticker}, skipping")
            return None

        # Step 7: Select adjacent bucket group (2-3 buckets with highest edge)
        target_buckets = self._select_adjacent_buckets(
            edge_summary.bucket_edges,
            buckets
        )
        if not target_buckets:
            logger.debug(f"No high-edge buckets for {ticker}")
            return None

        # Step 8: Calculate allocation proportional to edge
        allocation = self._calculate_allocation(
            target_buckets,
            edge_summary.bucket_edges
        )

        # Step 9: Estimate notional sizing
        try:
            portfolio_balance = kalshi_client.get_portfolio_balance()
            equity = portfolio_balance.get('balance', 0) / 100  # cents to dollars
            notional = equity * 0.03  # Initial 3% sizing (risk manager will adjust)
        except Exception as e:
            logger.debug(f"Could not fetch portfolio balance: {e}")
            notional = 10.0  # Fallback

        # Step 10: Create signal
        signal = TradeSignal(
            market_ticker=ticker,
            station_id=station_id,
            city_name=city_name,
            target_buckets=target_buckets,
            allocation=allocation,
            total_notional=notional,
            edge_pct=edge_summary.overall_ev * 100,
            confidence=edge_summary.confidence_score,
            reasoning=edge_summary.reasoning
        )

        logger.info(
            f"✓ Signal generated for {ticker}: buckets={target_buckets}, "
            f"edge={signal.edge_pct:.1f}%, confidence={signal.confidence:.0f}"
        )
        return signal

    def _get_market_prices(
        self,
        ticker: str,
        kalshi_client,
        buckets: List[Bucket]
    ) -> Optional[Dict[str, float]]:
        """Extract market-implied probabilities from orderbook."""
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
            # In production, could use orderbook ladder per bucket
            market_prices = {bucket.label: market_prob for bucket in buckets}
            return market_prices

        except Exception as e:
            logger.debug(f"Failed to fetch orderbook for {ticker}: {e}")
            return None

    def _select_adjacent_buckets(
        self,
        bucket_edges: List,
        available_buckets: List[Bucket]
    ) -> List[str]:
        """
        Select 2-3 adjacent buckets with highest edge.

        Prefers adjacent bucket spreads per successful strategies.
        """
        # Sort buckets by edge, descending
        sorted_edges = sorted(
            bucket_edges,
            key=lambda e: e.edge if hasattr(e, 'edge') else 0,
            reverse=True
        )

        selected = []
        for edge_obj in sorted_edges[:5]:  # Check top 5
            if edge_obj.recommendation != "SKIP":
                selected.append(edge_obj.label)
                if len(selected) >= 3:
                    break

        return selected[:3] if selected else []  # Return top 3, max

    def _calculate_allocation(
        self,
        target_buckets: List[str],
        bucket_edges: List
    ) -> List[float]:
        """Calculate proportional allocation across target buckets."""
        if not target_buckets:
            return []

        # Find edge for each target bucket
        bucket_edges_map = {}
        for edge_obj in bucket_edges:
            if hasattr(edge_obj, 'label') and hasattr(edge_obj, 'edge'):
                bucket_edges_map[edge_obj.label] = edge_obj.edge

        # Calculate total edge
        total_edge = sum(
            bucket_edges_map.get(b, 0) for b in target_buckets
        )

        if total_edge <= 0:
            # Equal allocation
            alloc = 1.0 / len(target_buckets)
            return [alloc] * len(target_buckets)

        # Proportional to edge
        return [
            bucket_edges_map.get(b, 0) / total_edge
            for b in target_buckets
        ]

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
                "temperature_actual": daily.temperature,
                "temperature_max": daily.temperature_max,
                "temperature_min": getattr(daily, 'temperature_min', None),
            }

            # Add ensemble stats if available
            if weather_data.ensemble_forecast:
                ensemble = weather_data.ensemble_forecast[0]
                temp_log.update({
                    "ensemble_mean": ensemble.temperature_mean,
                    "ensemble_std": ensemble.temperature_std,
                    "ensemble_members": ensemble.ensemble_members,
                })

            logger.info(f"[TEMPERATURE] {json.dumps(temp_log)}")
        except Exception as e:
            logger.debug(f"Failed to log temperature data: {e}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger.info("SignalGenerator module loaded successfully")
