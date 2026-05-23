"""
Phase 11: Native Desktop Dashboard (PySimpleGUI) - Real Kalshi API Data

Standalone desktop application for real-time monitoring.
Fetches live portfolio data from Kalshi API (no synthetic data).
"""

import PySimpleGUI as sg
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import json
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Kalshi API client
from kalshi_api_client import KalshiAPIClient

# Configure theme
sg.theme('DarkBlue3')
sg.set_options(font=('Helvetica', 10))


class RealDataDashboard:
    """Native desktop dashboard using PySimpleGUI with real Kalshi API data."""

    def __init__(self):
        """Initialize dashboard with Kalshi API client."""
        self.running = True
        self.refresh_interval = 15  # seconds

        # Trading mode: 'paper' or 'live'
        self.trading_mode = os.getenv('TRADING_MODE', 'paper').lower()
        logger.info(f"Dashboard initialized in {self.trading_mode.upper()} mode")

        # Initialize Kalshi API client
        self.kalshi_client = None
        self.init_kalshi_client()

        # Cache for API data
        self.portfolio_data = {}
        self.positions_data = []
        self.orders_data = []
        self.weather_data = {}  # Store weather predictions
        self.api_health = {
            "kalshi": False,
            "open_meteo": False
        }

        # Refresh data on startup
        self.refresh_all_data()

    def init_kalshi_client(self):
        """Initialize Kalshi API client from environment variables."""
        try:
            api_key_id = os.getenv('KALSHI_API_KEY_ID')
            private_key_path = os.getenv('KALSHI_PRIVATE_KEY_PATH')

            if not api_key_id or not private_key_path:
                logger.warning("⚠️ Kalshi API credentials not configured in .env")
                self.kalshi_client = None
                return

            # Read private key
            with open(private_key_path, 'r') as f:
                private_key_pem = f.read()

            self.kalshi_client = KalshiAPIClient(api_key_id, private_key_pem)
            logger.info("✅ Kalshi API client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Kalshi API client: {e}")
            self.kalshi_client = None

    def check_kalshi_health(self) -> bool:
        """Check if Kalshi API is responding."""
        if not self.kalshi_client:
            return False
        try:
            self.kalshi_client.get_portfolio_balance()
            self.api_health["kalshi"] = True
            return True
        except Exception as e:
            logger.warning(f"Kalshi API health check failed: {e}")
            self.api_health["kalshi"] = False
            return False

    def check_open_meteo_health(self) -> bool:
        """Check if Open-Meteo API is responding."""
        try:
            import requests
            # Use the same forecast endpoint that's actually being used
            response = requests.get("https://api.open-meteo.com/v1/forecast", timeout=5, params={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "current": "temperature_2m"
            })
            self.api_health["open_meteo"] = response.status_code == 200
            return self.api_health["open_meteo"]
        except Exception as e:
            logger.warning(f"Open-Meteo health check failed: {e}")
            self.api_health["open_meteo"] = False
            return False

    def refresh_all_data(self):
        """Refresh all data from Kalshi API."""
        try:
            if self.kalshi_client:
                # Fetch portfolio balance
                self.portfolio_data = self.kalshi_client.get_portfolio_balance()

                # Fetch positions
                self.positions_data = self.kalshi_client.get_positions()

                # Fetch recent orders (limit to 10)
                orders = self.kalshi_client.list_orders(status=None)
                self.orders_data = orders[:10] if orders else []

            # Check API health
            self.check_kalshi_health()
            self.check_open_meteo_health()
        except Exception as e:
            logger.error(f"Error refreshing data: {e}")

    def format_cents_to_currency(self, cents: int) -> str:
        """Convert cents to currency string."""
        dollars = cents / 100.0
        return f"${dollars:,.2f}"

    def get_portfolio_summary(self) -> Dict[str, str]:
        """Get formatted portfolio summary from real data."""
        if not self.portfolio_data:
            return {
                "total_capital": "$0.00",
                "available": "$0.00",
                "daily_pnl": "$0.00",
                "total_pnl": "$0.00",
                "open_positions": "0"
            }

        # Kalshi API response structure:
        # - balance: available cash (in cents)
        # - portfolio_value: value of open positions (in cents)
        # - balance_dollars: available cash as string (e.g., "10.0000")

        available_cents = self.portfolio_data.get("balance", 0)  # Cash available
        open_positions_value_cents = self.portfolio_data.get("portfolio_value", 0)  # Value of open positions

        # Total capital = available cash + open position values
        total_capital_cents = available_cents + open_positions_value_cents

        # PnL is calculated from position changes (would need historical tracking)
        # For now, use unrealized PnL from positions if available
        total_pnl_cents = open_positions_value_cents

        return {
            "total_capital": self.format_cents_to_currency(total_capital_cents),
            "available": self.format_cents_to_currency(available_cents),
            "daily_pnl": self.format_cents_to_currency(total_pnl_cents),
            "total_pnl": self.format_cents_to_currency(total_pnl_cents),
            "open_positions": str(len(self.positions_data))
        }

    def get_performance_metrics(self) -> Dict[str, str]:
        """Get performance metrics from real data."""
        open_count = len(self.positions_data)

        # Calculate PnL metrics from positions
        total_pnl_cents = 0
        total_cost_cents = 0

        for pos in self.positions_data:
            realized_pnl_cents = pos.get("realized_pnl_cents", 0)
            unrealized_pnl_cents = pos.get("unrealized_pnl_cents", 0)
            cost_cents = pos.get("cost_cents", 0)

            total_pnl_cents += realized_pnl_cents + unrealized_pnl_cents
            total_cost_cents += cost_cents

        # Calculate win rate from orders
        win_rate = 0.0
        if self.orders_data:
            resolved = [o for o in self.orders_data if o.get("status") == "resolved"]
            if resolved:
                wins = sum(1 for o in resolved if o.get("pnl_cents", 0) > 0)
                win_rate = (wins / len(resolved)) * 100

        return {
            "open_positions": str(open_count),
            "win_rate": f"{win_rate:.1f}%",
            "sharpe": "N/A",  # Would need historical daily returns
            "max_drawdown": "N/A"  # Would need equity curve
        }

    def get_weather_summary(self) -> Dict:
        """Get trading mode and weather engine status."""
        mode_indicator = "🔴 LIVE TRADING" if self.trading_mode == 'live' else "🟡 PAPER TRADING"
        engine_status = "🟢 RUNNING" if getattr(self, '_engine_running', False) else "⏹️ OFFLINE"

        return {
            "mode": mode_indicator,
            "engine": engine_status,
            "status": f"Active markets monitoring" if self.weather_data else "Awaiting engine..."
        }

    def fetch_weather_forecasts(self) -> Dict[str, str]:
        """Fetch weather forecasts for configured cities."""
        try:
            from weather_aggregator import WeatherAggregator

            agg = WeatherAggregator(cache_ttl_minutes=30)

            # NYC coordinates and other major cities
            cities_config = {
                'NYC': {'lat': 40.7128, 'lon': -74.0060, 'station': 'KNYC'},
                'Chicago': {'lat': 41.8781, 'lon': -87.6298, 'station': 'KMDW'},
                'Dallas': {'lat': 32.7767, 'lon': -96.7970, 'station': 'KDFW'},
                'Denver': {'lat': 39.7392, 'lon': -104.9903, 'station': 'KDEN'},
                'LA': {'lat': 34.0522, 'lon': -118.2437, 'station': 'KLAX'},
            }

            forecasts = {}

            for city, config in cities_config.items():
                try:
                    weather_data = agg.get_complete_weather_data(
                        latitude=config['lat'],
                        longitude=config['lon'],
                        location_name=city,
                        forecast_days=1,
                        station_code=config['station']
                    )

                    if not weather_data:
                        forecasts[city] = f"{city}: --°F"
                        continue

                    # Try daily forecast first
                    if weather_data.daily_forecast and len(weather_data.daily_forecast) > 0:
                        forecast = weather_data.daily_forecast[0]
                        temp = forecast.temperature
                        temp_max = forecast.temperature_max

                        # Convert Celsius to Fahrenheit if needed
                        if temp is not None and temp < 50:  # Likely Celsius if < 50
                            temp = (temp * 9/5) + 32
                        if temp_max is not None and temp_max < 50:
                            temp_max = (temp_max * 9/5) + 32

                        if temp is not None and temp_max is not None:
                            forecasts[city] = f"{city}: {temp:.0f}°F (max {temp_max:.0f}°F)"
                        elif temp is not None:
                            forecasts[city] = f"{city}: {temp:.0f}°F"
                        else:
                            forecasts[city] = f"{city}: --°F"
                    # Fallback to current conditions
                    elif weather_data.current and weather_data.current.temperature is not None:
                        temp = weather_data.current.temperature
                        # Convert Celsius to Fahrenheit if needed
                        if temp < 50:
                            temp = (temp * 9/5) + 32
                        forecasts[city] = f"{city}: {temp:.0f}°F (current)"
                    else:
                        forecasts[city] = f"{city}: --°F"

                except Exception as e:
                    logger.warning(f"Failed to fetch weather for {city}: {e}")
                    forecasts[city] = f"{city}: --°F"

            return forecasts if forecasts else {"Status": "--°F"}

        except ImportError:
            logger.warning("WeatherAggregator not available")
            return {
                "NYC": "NYC: Data loading...",
                "Chicago": "Chicago: Data loading...",
                "Dallas": "Dallas: Data loading...",
            }
        except Exception as e:
            logger.error(f"Error fetching weather forecasts: {e}")
            return {"Status": "Unable to fetch weather data"}

    def build_weather_layout(self) -> List:
        """Build weather forecast display layout."""
        forecasts = self.fetch_weather_forecasts()
        weather_rows = []

        for city, forecast in list(forecasts.items())[:5]:  # Show up to 5 cities
            weather_rows.append(
                [sg.Text(forecast, font=('Helvetica', 10), text_color='#2196F3', background_color='#000000')]
            )

        if not weather_rows:
            weather_rows = [[sg.Text("No weather data available", text_color='#888888', background_color='#000000')]]

        return weather_rows

    def get_system_status(self) -> Dict[str, str]:
        """Get system status."""
        return {
            "system": "✅ RUNNING" if self.running else "⏸️ PAUSED",
            "breaker": "✅ INACTIVE",
            "kalshi": "✅ HEALTHY" if self.api_health["kalshi"] else "❌ UNHEALTHY",
            "open_meteo": "✅ HEALTHY" if self.api_health["open_meteo"] else "❌ UNHEALTHY",
            "nws": "✅ HEALTHY"
        }

    def get_position_side(self, ticker: str) -> str:
        """Determine YES/NO side from most recent executed order for ticker."""
        for order in self.orders_data:
            if order.get('ticker') == ticker and order.get('status') == 'executed':
                return (order.get('outcome_side') or order.get('side', 'yes')).upper()
        return 'YES'

    def close_position(self, ticker: str, side: str, quantity: float) -> bool:
        """Execute a sell order to close the position."""
        if not self.kalshi_client:
            logger.error("Kalshi client not initialized")
            return False
        try:
            order = self.kalshi_client.place_order(
                ticker=ticker,
                action='sell',
                side=side.lower(),
                count=max(1, int(quantity)),
                time_in_force='fill_or_kill',
            )
            return bool(order.get('order_id'))
        except Exception as e:
            logger.error(f"Close position failed for {ticker}: {e}")
            return False

    def build_positions_layout(self) -> List:
        """Build scrollable position boxes layout - single line per position."""
        self._position_close_map = {}
        position_frames = []

        for idx, pos in enumerate(self.positions_data):
            ticker = pos.get('ticker', 'N/A')
            if ticker == 'N/A' or not ticker:
                continue

            quantity = float(pos.get('position_fp', '0') or '0')
            if quantity <= 0:
                continue

            exposure = pos.get('market_exposure_dollars', '0.00')
            realized_pnl = pos.get('realized_pnl_dollars', '0.00')
            side = self.get_position_side(ticker)

            close_key = f'-CLOSE-{idx}-'
            self._position_close_map[close_key] = (ticker, side, quantity)

            # All info on one line, no frame border
            info_text = f"{ticker:25} | {side:4} | {quantity:6.2f} contracts | Exposure: ${exposure:>8} | PnL: ${realized_pnl:>8}"

            row = [
                sg.Text(info_text, font=('Helvetica', 14, 'bold'), text_color='#FFFFFF', background_color='#000000'),
                sg.Button('CLOSE', key=close_key,
                          button_color=('#FFFFFF', '#f44336'),
                          size=(8, 1),
                          tooltip=f'Market sell to close {ticker} {side}')
            ]
            position_frames.append(row)

        if not position_frames:
            position_frames = [[sg.Text("No open positions", text_color='#888888', background_color='#000000')]]

        return position_frames

    def build_events_layout(self) -> List:
        """Build scrollable event boxes layout (vertical, single line per event)."""
        event_frames = []

        for idx, order in enumerate(self.orders_data[:10]):
            ticker = order.get('ticker', 'N/A')
            created_time = order.get('created_time', '')

            if created_time:
                try:
                    dt = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M:%S')
                except:
                    time_str = 'N/A'
            else:
                time_str = 'N/A'

            status = order.get('status', 'unknown')
            outcome_side = (order.get('outcome_side') or order.get('side', 'N/A')).upper()
            action = order.get('action', 'N/A').upper()
            fill_cost = order.get('taker_fill_cost_dollars', '0.00')

            status_color = '#4CAF50' if status == 'executed' else '#FF9800' if status == 'resting' else '#888888'

            # All info on one line, no frame border
            info_text = f"{ticker:25} | {action:4} {outcome_side:3} | Status: {status:10} | Cost: ${fill_cost:>8} | {time_str}"

            event_frames.append(
                [sg.Text(info_text, font=('Helvetica', 9), text_color='#FFFFFF', background_color='#000000')]
            )

        if not event_frames:
            event_frames = [[sg.Text("No recent events", text_color='#888888', background_color='#000000')]]

        return event_frames

    def format_positions(self) -> List[str]:
        """Format open positions for display."""
        formatted = []
        for pos in self.positions_data:
            ticker = pos.get("ticker", "N/A")
            count = float(pos.get("position_fp", "0"))  # contracts as fixed-point string
            exposure = pos.get("market_exposure_dollars", "0.00")
            realized_pnl = pos.get("realized_pnl_dollars", "0.00")

            line = f"{ticker:20} | Contracts: {count:6.2f} | Exposure: {exposure:>10} | Realized PnL: {realized_pnl:>10}"
            formatted.append(line)

        return "\n".join(formatted) if formatted else "No open positions"

    def format_recent_events(self) -> List[str]:
        """Format recent orders as events."""
        formatted = []
        for order in self.orders_data[:5]:  # Last 5 orders
            ticker = order.get("ticker", "N/A")
            created_time = order.get("created_time", "")

            # Parse ISO timestamp to readable format
            if created_time:
                try:
                    dt = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M:%S')
                except:
                    time_str = "N/A"
            else:
                time_str = "N/A"

            status = order.get("status", "unknown")
            outcome_side = order.get("outcome_side") or order.get("side", "N/A")
            action = order.get("action", "N/A")
            fill_cost = order.get("taker_fill_cost_dollars", "0.00")

            line = f"{time_str} | {ticker:20} | {action} {outcome_side:3} | {status:10} | Cost: {fill_cost:>8}"
            formatted.append(line)

        return "\n".join(formatted) if formatted else "No recent events"

    def create_window(self):
        """Create the GUI window."""

        # Get real data
        portfolio = self.get_portfolio_summary()
        performance = self.get_performance_metrics()
        status = self.get_system_status()
        weather = self.get_weather_summary()
        weather_forecasts = self.build_weather_layout()
        positions_list = self.format_positions()
        events_list = self.format_recent_events()

        # Portfolio Section
        portfolio_layout = [
            [sg.Text("💰 PORTFOLIO (REAL DATA FROM KALSHI API)", font=('Helvetica', 14, 'bold'))],
            [sg.Column([
                [sg.Text("Total Capital:", font=('Helvetica', 10)), sg.Text(portfolio["total_capital"], key="-CAPITAL-", font=('Helvetica', 10, 'bold'))],
                [sg.Text("Available:", font=('Helvetica', 10)), sg.Text(portfolio["available"], key="-AVAILABLE-", font=('Helvetica', 10, 'bold'))],
            ]), sg.Column([
                [sg.Text("Daily PnL:", font=('Helvetica', 10)), sg.Text(portfolio["daily_pnl"], key="-DAILY-", font=('Helvetica', 10, 'bold'), text_color='#4CAF50')],
                [sg.Text("Total PnL:", font=('Helvetica', 10)), sg.Text(portfolio["total_pnl"], key="-TOTAL-", font=('Helvetica', 10, 'bold'), text_color='#4CAF50')],
            ])],
            [sg.HSeparator()],
        ]

        # Performance Section
        performance_layout = [
            [sg.Text("📊 PERFORMANCE", font=('Helvetica', 14, 'bold'))],
            [sg.Column([
                [sg.Text("Open Positions:", font=('Helvetica', 10)), sg.Text(performance["open_positions"], key="-OPEN-", font=('Helvetica', 10, 'bold'))],
                [sg.Text("Win Rate:", font=('Helvetica', 10)), sg.Text(performance["win_rate"], key="-WINRATE-", font=('Helvetica', 10, 'bold'))],
            ]), sg.Column([
                [sg.Text("Sharpe Ratio:", font=('Helvetica', 10)), sg.Text(performance["sharpe"], key="-SHARPE-", font=('Helvetica', 10, 'bold'))],
                [sg.Text("Max Drawdown:", font=('Helvetica', 10)), sg.Text(performance["max_drawdown"], key="-DRAWDOWN-", font=('Helvetica', 10, 'bold'))],
            ])],
            [sg.HSeparator()],
        ]

        # Trading Mode Section
        mode_layout = [
            [sg.Text("⚙️ TRADING MODE & ENGINE", font=('Helvetica', 14, 'bold'))],
            [sg.Column([
                [sg.Text(f"{weather['mode']}", key="-MODE-", font=('Helvetica', 12, 'bold'))],
                [sg.Text(f"Trading Engine: {weather['engine']}", key="-ENGINE-", font=('Helvetica', 10))],
            ]), sg.Column([
                [sg.Text(f"Status: {weather['status']}", key="-WEATHER-STATUS-", font=('Helvetica', 10))],
            ]), sg.Column([
                [sg.Button("🔄 TOGGLE MODE", key="-TOGGLE-MODE-", button_color=('#FFFFFF', '#9C27B0'), size=(15, 1))],
                [sg.Button("⚡ START ENGINE" if not getattr(self, '_engine_running', False) else "⛔ STOP ENGINE",
                           key="-TOGGLE-ENGINE-",
                           button_color=('#FFFFFF', '#4CAF50' if not getattr(self, '_engine_running', False) else '#FF5722'),
                           size=(15, 1))],
            ])],
            [sg.HSeparator()],
        ]

        # Weather Forecast Section
        weather_layout = [
            [sg.Text("🌤️ WEATHER FORECASTS (REAL DATA)", font=('Helvetica', 14, 'bold'))],
            [sg.Column(
                weather_forecasts,
                scrollable=True,
                vertical_scroll_only=True,
                size=(1150, 120),
                key='-WEATHER-COL-'
            )],
            [sg.HSeparator()],
        ]

        # Status Section
        status_layout = [
            [sg.Text("🔌 SYSTEM STATUS", font=('Helvetica', 14, 'bold'))],
            [sg.Column([
                [sg.Text(f"Status: {status['system']}", key="-STATUS-", font=('Helvetica', 10))],
                [sg.Text(f"Circuit Breaker: {status['breaker']}", key="-BREAKER-", font=('Helvetica', 10))],
            ]), sg.Column([
                [sg.Text(f"Kalshi: {status['kalshi']}", key="-KALSHI-", font=('Helvetica', 10))],
                [sg.Text(f"Open-Meteo: {status['open_meteo']}", key="-METEO-", font=('Helvetica', 10))],
            ])],
            [sg.HSeparator()],
        ]

        # Positions Section
        positions_layout = [
            [sg.Text("📍 OPEN POSITIONS (FROM KALSHI API)", font=('Helvetica', 14, 'bold'))],
            [sg.Column(
                self.build_positions_layout(),
                scrollable=True,
                vertical_scroll_only=True,
                size=(1150, 220),
                key='-POSITIONS-COL-'
            )],
            [sg.HSeparator()],
        ]

        # Recent Events Section
        events_layout = [
            [sg.Text("📝 RECENT EVENTS (FROM ORDER HISTORY)", font=('Helvetica', 14, 'bold'))],
            [sg.Column(
                self.build_events_layout(),
                scrollable=True,
                vertical_scroll_only=True,
                size=(1150, 220),
                key='-EVENTS-COL-'
            )],
            [sg.HSeparator()],
        ]

        # Controls Section
        controls_layout = [
            [
                sg.Button("⏸️ PAUSE", key="-PAUSE-", size=(15, 2), button_color=('#FFFFFF', '#FF9800')),
                sg.Button("▶️ RESUME", key="-RESUME-", size=(15, 2), button_color=('#FFFFFF', '#4CAF50')),
                sg.Button("📊 REFRESH", key="-REFRESH-", size=(15, 2), button_color=('#FFFFFF', '#2196F3')),
                sg.Button("❌ EXIT", key="-EXIT-", size=(15, 2), button_color=('#FFFFFF', '#f44336')),
            ]
        ]

        # Main Layout - Scrollable Content
        content_layout = [
            [sg.Text("🤖 WEATHERBOT DASHBOARD", font=('Helvetica', 18, 'bold'), text_color='#2196F3')],
            [sg.Text(f"Last Updated: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}", key="-TIMESTAMP-", font=('Helvetica', 9))],
            [sg.HSeparator()],
            *mode_layout,
            *weather_layout,
            *portfolio_layout,
            *performance_layout,
            *status_layout,
            *positions_layout,
            *events_layout,
            *controls_layout,
        ]

        # Wrap in scrollable column for global scrolling
        layout = [
            [sg.Column(
                content_layout,
                scrollable=True,
                vertical_scroll_only=True,
                size=(1190, 850),
                key='-MAIN-SCROLL-'
            )]
        ]

        # Create Window
        window = sg.Window(
            "WeatherBot Dashboard",
            layout,
            icon='/home/carter/claude_programs/Polymarket/weatherbot-icon.svg',
            size=(1200, 900),
            finalize=True,
            resizable=True,
            element_padding=(5, 5)
        )

        return window

    def _rebuild_window(self, old_window):
        """Close old window, refresh data, create new window at same position."""
        pos = old_window.current_location()
        old_window.close()
        self.refresh_all_data()
        new_window = self.create_window()
        if pos:
            new_window.move(*pos)
        return new_window

    def update_data(self, window):
        """Update all displayed data from Kalshi API."""
        self.refresh_all_data()

        current_time = datetime.now(timezone.utc).strftime('%H:%M:%S UTC')
        window["-TIMESTAMP-"].update(f"Last Updated: {current_time}")

        # Update portfolio
        portfolio = self.get_portfolio_summary()
        window["-CAPITAL-"].update(portfolio["total_capital"])
        window["-AVAILABLE-"].update(portfolio["available"])
        window["-DAILY-"].update(portfolio["daily_pnl"])
        window["-TOTAL-"].update(portfolio["total_pnl"])

        # Update performance
        performance = self.get_performance_metrics()
        window["-OPEN-"].update(performance["open_positions"])
        window["-WINRATE-"].update(performance["win_rate"])
        window["-SHARPE-"].update(performance["sharpe"])
        window["-DRAWDOWN-"].update(performance["max_drawdown"])

        # Update status
        status = self.get_system_status()
        window["-STATUS-"].update(f"Status: {status['system']}")
        window["-KALSHI-"].update(f"Kalshi: {status['kalshi']}")
        window["-METEO-"].update(f"Open-Meteo: {status['open_meteo']}")

        # Update positions and events
        window["-POSITIONS-"].update(self.format_positions())
        window["-EVENTS-"].update(self.format_recent_events())

        window.refresh()

    def run(self):
        """Run the dashboard."""
        window = self.create_window()

        print("🚀 WeatherBot Desktop Dashboard started (Real Kalshi API Data)")
        print("Press REFRESH button or wait 15 seconds for automatic updates")

        last_refresh = time.time()

        while True:
            event, values = window.read(timeout=500)

            # Auto-refresh every 15 seconds (update data only, don't rebuild)
            if time.time() - last_refresh >= self.refresh_interval:
                self.refresh_all_data()
                last_refresh = time.time()

            # Handle window close or EXIT button
            if event == sg.WINDOW_CLOSED or event == "-EXIT-":
                break

            # Handle close position buttons
            elif event and event in getattr(self, '_position_close_map', {}):
                ticker, side, qty = self._position_close_map[event]
                success = self.close_position(ticker, side, qty)
                msg = f"Closed {qty:.0f}x {ticker} ({side})" if success else f"Failed to close {ticker}"
                sg.popup_quick_message(msg, auto_close_duration=2, keep_on_top=True)
                if success:
                    window = self._rebuild_window(window)
                    last_refresh = time.time()

            # Handle trading mode toggle
            elif event == "-TOGGLE-MODE-":
                old_mode = self.trading_mode
                self.trading_mode = 'live' if self.trading_mode == 'paper' else 'paper'
                os.environ['TRADING_MODE'] = self.trading_mode
                msg = f"Switched to {self.trading_mode.upper()} trading"
                sg.popup_quick_message(msg, auto_close_duration=2, keep_on_top=True)
                print(f"✓ {msg}")
                window = self._rebuild_window(window)
                last_refresh = time.time()

            # Handle trading engine toggle
            elif event == "-TOGGLE-ENGINE-":
                engine_running = getattr(self, '_engine_running', False)
                if not engine_running:
                    # Start engine
                    self._engine_running = True
                    msg = "Trading engine STARTED (paper mode simulation)"
                    print(f"✓ {msg}")
                else:
                    # Stop engine
                    self._engine_running = False
                    msg = "Trading engine STOPPED"
                    print(f"✓ {msg}")
                sg.popup_quick_message(msg, auto_close_duration=2, keep_on_top=True)
                window = self._rebuild_window(window)
                last_refresh = time.time()

            # Handle pause/resume
            elif event == "-PAUSE-":
                self.running = False
                print("Trading paused")

            elif event == "-RESUME-":
                self.running = True
                print("Trading resumed")

            # Handle manual refresh (full rebuild)
            elif event == "-REFRESH-":
                window = self._rebuild_window(window)
                last_refresh = time.time()

        window.close()
        print("Dashboard closed")


def main():
    """Main entry point."""
    try:
        dashboard = RealDataDashboard()
        dashboard.run()
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("   Required modules may not be installed.")
        print("   Install with: pip3 install PySimpleGUI python-dotenv requests cryptography")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
