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
import re
from datetime import datetime, timezone, date, timedelta
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
        Uses event-centric grouping: groups markets by (city, date) to fetch
        per-bin prices for the 3-bin portfolio.

        Args:
            markets: List of market dicts from Kalshi API
            kalshi_client: KalshiAPIClient instance for orderbook data
            min_edge: Override minimum edge threshold (unused in 3-bin strategy)

        Returns:
            List of TradeSignal objects matching 3-bin criteria
        """
        if not self.predictor or not markets:
            return []

        # Group markets by (city, date) to identify events
        events = self._group_markets_by_event(markets)
        signals = []

        for (city, date_key), event_markets in events.items():
            try:
                signal = self._generate_signal_for_event(
                    city,
                    date_key,
                    event_markets,
                    kalshi_client
                )
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Signal generation failed for {city} {date_key}: {e}", exc_info=True)
                continue

        logger.info(f"Generated {len(signals)} signals from {len(events)} events ({len(markets)} markets)")
        return signals

    def _group_markets_by_event(self, markets: List[Dict]) -> Dict[Tuple[str, str], List[Dict]]:
        """
        Group markets by (city, date_key) to identify events.
        Each event is a set of bucket markets for the same city and date.

        Returns:
            Dict mapping (city, date_key) to list of markets for that event
        """
        events = {}
        for market in markets:
            ticker = market.get('ticker', '')
            title = market.get('title', '')

            # Only process bucket markets
            if '-B' not in ticker:
                continue

            # Parse city and date from ticker or title
            parsed = parse_market_buckets(market)
            if not parsed:
                continue

            buckets, station_id = parsed
            city = get_city_for_station(station_id)
            if not city:
                continue

            # Extract date from ticker (e.g., KXHIGHNY-29MAY26-B88 → 29MAY26)
            m = re.search(r'-(\d{2}[A-Z]{3}\d{2})-', ticker)
            if not m:
                continue

            date_key = m.group(1)
            event_key = (city, date_key)

            if event_key not in events:
                events[event_key] = []
            events[event_key].append(market)

        return events

    def _generate_signal_for_event(
        self,
        city: str,
        date_key: str,
        event_markets: List[Dict],
        kalshi_client
    ) -> Optional[TradeSignal]:
        """
        Generate a signal for a single event (city + date).
        Fetches 3-model consensus once, builds portfolio, then fetches per-bin prices.
        """
        logger.debug(f"Analyzing event {city} {date_key} with {len(event_markets)} bucket markets")

        # Step 1: Parse date from event_markets
        target_date = self._parse_date_from_ticker(event_markets[0].get('ticker', ''))
        if not target_date:
            logger.debug(f"Could not parse date for {city} {date_key}")
            return None

        # Step 2: Check entry window (18-30 hours before resolution)
        if not self._in_entry_window_for_date(target_date):
            logger.debug(f"Event {city} {date_key} outside 18–30 hour entry window")
            return None

        # Step 3: Get city config and fetch 3-model consensus
        city_config = CITIES_KALSHI.get(city)
        if not city_config:
            logger.debug(f"Unknown city {city}")
            return None

        try:
            from weather_sources import OpenMeteoSource
            om = OpenMeteoSource()
            forecast = om.get_three_model_consensus(city_config['lat'], city_config['lon'], target_date)
            if forecast is None or not forecast.get('agree'):
                logger.info(
                    f"Skipping {city} {date_key}: models disagree (spread={forecast.get('spread', 'N/A')}°C)"
                )
                return None

            logger.debug(
                f"3-model consensus for {city}: ICON={forecast['icon']:.1f}°C, "
                f"GFS={forecast['gfs']:.1f}°C, ECMWF={forecast['ecmwf']:.1f}°C"
            )
        except Exception as e:
            logger.debug(f"Failed to fetch 3-model consensus for {city} {date_key}: {e}")
            return None

        # Step 4: Parse available buckets from event markets
        available_buckets = []
        market_by_bin = {}  # Map bin_label → market dict
        for market in event_markets:
            parsed = parse_market_buckets(market)
            if not parsed:
                continue
            buckets, _ = parsed
            for bucket in buckets:
                available_buckets.append(bucket)
                market_by_bin[bucket.label] = market

        if not available_buckets:
            logger.debug(f"No buckets found for {city} {date_key}")
            return None

        # Step 5: Build portfolio using outlier-aware bin selection
        target_bins = self._build_portfolio_from_consensus(forecast, available_buckets)
        if not target_bins:
            logger.debug(f"Could not find viable bins for {city} {date_key}")
            return None

        logger.debug(f"Selected portfolio for {city} {date_key}: {target_bins}")

        # Step 6: Fetch per-bin prices using actual bucket-market tickers
        prices_for_bins = []
        for bin_label in target_bins:
            if bin_label not in market_by_bin:
                logger.debug(f"No market found for bin {bin_label} in {city} {date_key}")
                return None

            bin_market = market_by_bin[bin_label]
            bin_ticker = bin_market.get('ticker')
            price = self._get_bin_price(bin_ticker, kalshi_client)
            if price is None:
                logger.debug(f"Could not fetch price for {bin_ticker}")
                return None
            prices_for_bins.append(price)

        # Step 7: Apply price filters from PDF Step 13
        sum_price = sum(prices_for_bins)
        if sum_price > self.max_sum_price:
            logger.debug(f"Sum of prices {sum_price:.2f} > {self.max_sum_price:.2f} for {city}, skipping")
            return None

        if any(p < self.min_bin_price for p in prices_for_bins):
            logger.debug(f"One or more bins < {self.min_bin_price:.2f} for {city}, skipping")
            return None

        if any(p > self.max_bin_price for p in prices_for_bins):
            logger.debug(f"One or more bins > {self.max_bin_price:.2f} for {city}, skipping")
            return None

        logger.info(
            f"✓ 3-bin signal for {city} {date_key}: bins={target_bins}, "
            f"prices={[f'{p:.2f}' for p in prices_for_bins]}, sum={sum_price:.2f}"
        )

        # Step 8: Create signal with equal allocation
        allocation = [1.0/3.0, 1.0/3.0, 1.0/3.0]

        try:
            portfolio_balance = kalshi_client.get_portfolio_balance()
            equity = portfolio_balance.get('balance', 0) / 100
            notional = equity * 0.03
        except Exception as e:
            logger.debug(f"Could not fetch portfolio balance: {e}")
            notional = 10.0

        # Calculate confidence and edge
        spread = forecast.get('spread', 3.0)
        if spread <= 1.0:
            confidence_score = 95.0
        elif spread <= 2.0:
            confidence_score = 85.0
        elif spread <= 3.0:
            confidence_score = 75.0
        else:
            confidence_score = 60.0

        math_edge = 1.0 - sum_price

        # Use the first market's ticker as reference (for city/date identification)
        ref_ticker = event_markets[0].get('ticker', '')

        signal = TradeSignal(
            market_ticker=ref_ticker,
            station_id=city_config['code'],
            city_name=city,
            target_buckets=target_bins,
            allocation=allocation,
            total_notional=notional,
            edge_pct=math_edge * 100,
            confidence=confidence_score,
            reasoning=f"3-bin strategy: {target_bins} at {[f'{p:.2f}' for p in prices_for_bins]} (math edge: {math_edge*100:.1f}%)"
        )

        return signal

    def _parse_date_from_ticker(self, ticker: str) -> Optional[date]:
        """Extract target date from Kalshi ticker (e.g., KXHIGHNY-29MAY26 → 2026-05-29)."""
        m = re.search(r'-(\d{2})([A-Z]{3})(\d{2})-', ticker)
        if not m:
            return None

        day, mon_str, yr2 = int(m.group(1)), m.group(2), int(m.group(3))
        month_map = {
            'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
            'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12,
        }
        month = month_map.get(mon_str)
        if not month:
            return None

        return date(2000 + yr2, month, day)

    def _in_entry_window_for_date(self, target_date: date) -> bool:
        """Check if target_date resolves 18–30 hours from now."""
        from datetime import datetime, timezone, timedelta
        WIN_MIN_H, WIN_MAX_H = 18.0, 30.0
        resolve_time = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc) + timedelta(hours=24)
        hours_until = (resolve_time - datetime.now(timezone.utc)).total_seconds() / 3600
        return WIN_MIN_H <= hours_until <= WIN_MAX_H

    def _get_bin_price(self, ticker: str, kalshi_client) -> Optional[float]:
        """
        Fetch the YES best bid price for a specific bucket-market ticker.
        Returns the price as a float (0.0-1.0), or None if unavailable.
        """
        try:
            orderbook = kalshi_client.get_orderbook(ticker)
            yes_bids = orderbook.get('yes_dollars', [])

            if not yes_bids:
                logger.debug(f"No YES bids for {ticker}")
                return None

            # Return best bid price (highest bid)
            best_bid = float(yes_bids[-1][0])
            return best_bid

        except Exception as e:
            logger.debug(f"Failed to fetch orderbook for {ticker}: {e}")
            return None

    def _generate_signal_for_market(
        self,
        market: Dict,
        kalshi_client
    ) -> Optional[TradeSignal]:
        """
        Generate a signal for a single market using Paruchh v3 3-bin strategy.
        Uses 3-model consensus (ICON+GFS+ECMWF) with outlier-aware bin selection.

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

        # Step 2: Check if within entry window (18-30 hours before resolution)
        if not self._in_entry_window(ticker):
            logger.debug(f"Market {ticker} outside 18-30 hour entry window, skipping")
            return None

        # Step 3: Fetch 3-model consensus (ICON, GFS, ECMWF)
        from datetime import date
        import re

        m = re.search(r'-(\d{2})([A-Z]{3})(\d{2})-', ticker)
        if not m:
            logger.debug(f"Could not parse date from {ticker}")
            return None

        day, mon_str, yr2 = int(m.group(1)), m.group(2), int(m.group(3))
        month_map = {
            'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
            'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12,
        }
        month = month_map.get(mon_str)
        if not month:
            logger.debug(f"Could not parse month from {ticker}")
            return None

        target_date = date(2000 + yr2, month, day)

        try:
            from weather_sources import OpenMeteoSource
            om = OpenMeteoSource()
            forecast = om.get_three_model_consensus(city_config['lat'], city_config['lon'], target_date)
            if forecast is None:
                logger.debug(f"Failed to fetch 3-model consensus for {ticker}")
                return None

            # Check model agreement
            if not forecast['agree']:
                logger.info(
                    f"Skipping {ticker}: models disagree (spread={forecast['spread']:.1f}°C > 3°C)"
                )
                return None

            logger.debug(
                f"3-model consensus for {ticker}: ICON={forecast['icon']:.1f}°C, "
                f"GFS={forecast['gfs']:.1f}°C, ECMWF={forecast['ecmwf']:.1f}°C, "
                f"spread={forecast['spread']:.1f}°C"
            )
        except Exception as e:
            logger.debug(f"Failed to fetch 3-model consensus for {ticker}: {e}")
            return None

        # Step 4: Build portfolio using outlier-aware bin selection
        target_buckets = self._build_portfolio_from_consensus(forecast, buckets)
        if not target_buckets:
            logger.debug(f"Could not find viable bins for {ticker}")
            return None

        logger.debug(f"Selected portfolio for {ticker}: {target_buckets}")

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
        spread = forecast.get('spread', 3.0)
        if spread <= 1.0:
            confidence_score = 95.0
        elif spread <= 2.0:
            confidence_score = 85.0
        elif spread <= 3.0:
            confidence_score = 75.0
        else:
            confidence_score = 60.0

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

    def _build_portfolio_from_consensus(
        self,
        forecast: Dict,
        available_buckets: List[Bucket]
    ) -> Optional[List[str]]:
        """
        Paruchh v3 portfolio builder: outlier-aware bin selection.

        Args:
            forecast: {'icon': C, 'gfs': C, 'ecmwf': C, 'spread': x, 'agree': bool}
            available_buckets: List of Bucket objects

        Returns:
            List of 2–3 bucket labels, or None to skip this market.
        """
        icon, gfs, ecmwf = forecast['icon'], forecast['gfs'], forecast['ecmwf']

        # Find closest pair of models
        distances = {
            ('icon', 'gfs'): abs(icon - gfs),
            ('icon', 'ecmwf'): abs(icon - ecmwf),
            ('gfs', 'ecmwf'): abs(gfs - ecmwf),
        }
        closest = min(distances, key=distances.get)

        if distances[closest] <= 1.0:
            # Tight pair: average pair, treat third as outlier
            pair_vals = [forecast[m] for m in closest]
            center = sum(pair_vals) / 2
            outlier_key = next(m for m in ('icon', 'gfs', 'ecmwf') if m not in closest)
            outlier = forecast[outlier_key]
        else:
            # All three spread out: average all, no outlier
            center = (icon + gfs + ecmwf) / 3
            outlier = None

        # Convert center from Celsius to Fahrenheit
        center_f = (center * 9/5) + 32

        # Find center bin (with gap fallback)
        center_bin = None
        for b in available_buckets:
            if b.contains(center_f):
                center_bin = b
                break
        if center_bin is None:
            # Gap fallback: nearest bin midpoint
            center_bin = min(available_buckets, key=lambda b: abs(b.midpoint() - center_f))

        idx = available_buckets.index(center_bin)
        above_1 = available_buckets[idx + 1] if idx + 1 < len(available_buckets) else None
        above_2 = available_buckets[idx + 2] if idx + 2 < len(available_buckets) else None
        below_1 = available_buckets[idx - 1] if idx > 0 else None

        # CASE A: outlier above center → tilt upward
        if outlier is not None and (outlier * 9/5 + 32) > center_f:
            plan = [center_bin, above_1, above_2]
        else:
            # CASE B/C: outlier below center or no outlier → center + above + below
            plan = [center_bin, above_1, below_1]

        plan = [b for b in plan if b is not None]
        if len(plan) < 2:
            return None

        return [b.label for b in plan]

    def _in_entry_window(self, market_ticker: str) -> bool:
        """
        Return True if market resolves 18–30 hours from now.
        Markets resolve at end-of-day (midnight UTC) of their target date.
        """
        import re
        from datetime import datetime, timezone, timedelta, date as date_class

        WIN_MIN_H, WIN_MAX_H = 18.0, 30.0
        m = re.search(r'-(\d{2})([A-Z]{3})(\d{2})-', market_ticker)
        if not m:
            return False

        day, mon_str, yr2 = int(m.group(1)), m.group(2), int(m.group(3))
        month_map = {
            'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
            'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12,
        }
        month = month_map.get(mon_str)
        if not month:
            return False

        year = 2000 + yr2
        target_date = date_class(year, month, day)
        resolve_time = datetime(year, month, day, tzinfo=timezone.utc) + timedelta(hours=24)
        hours_until = (resolve_time - datetime.now(timezone.utc)).total_seconds() / 3600
        return WIN_MIN_H <= hours_until <= WIN_MAX_H

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
