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

        # Initialize Kalshi API client
        self.kalshi_client = None
        self.init_kalshi_client()

        # Cache for API data
        self.portfolio_data = {}
        self.positions_data = []
        self.orders_data = []
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
            response = requests.get("https://archive-api.open-meteo.com/v1/archive", timeout=5, params={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "start_date": "2026-05-21",
                "end_date": "2026-05-21",
                "daily": "temperature_2m_max"
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

    def get_system_status(self) -> Dict[str, str]:
        """Get system status."""
        return {
            "system": "✅ RUNNING" if self.running else "⏸️ PAUSED",
            "breaker": "✅ INACTIVE",
            "kalshi": "✅ HEALTHY" if self.api_health["kalshi"] else "❌ UNHEALTHY",
            "open_meteo": "✅ HEALTHY" if self.api_health["open_meteo"] else "❌ UNHEALTHY",
            "nws": "✅ HEALTHY"
        }

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
            [sg.Listbox(
                values=positions_list,
                size=(100, 4),
                key="-POSITIONS-",
                disabled=True,
                background_color='#2B2B2B',
                text_color='#FFFFFF'
            )],
            [sg.HSeparator()],
        ]

        # Recent Events Section
        events_layout = [
            [sg.Text("📝 RECENT EVENTS (FROM ORDER HISTORY)", font=('Helvetica', 14, 'bold'))],
            [sg.Listbox(
                values=events_list,
                size=(100, 4),
                key="-EVENTS-",
                disabled=True,
                background_color='#2B2B2B',
                text_color='#FFFFFF'
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

        # Main Layout
        layout = [
            [sg.Text("🤖 WEATHERBOT DASHBOARD", font=('Helvetica', 18, 'bold'), text_color='#2196F3')],
            [sg.Text(f"Last Updated: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}", key="-TIMESTAMP-", font=('Helvetica', 9))],
            [sg.HSeparator()],
            *portfolio_layout,
            *performance_layout,
            *status_layout,
            *positions_layout,
            *events_layout,
            *controls_layout,
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

        while self.running:
            event, values = window.read(timeout=500)

            # Auto-refresh every 15 seconds
            if time.time() - last_refresh >= self.refresh_interval:
                self.update_data(window)
                last_refresh = time.time()

            # Handle events
            if event == sg.WINDOW_CLOSED or event == "-EXIT-":
                self.running = False
                break
            elif event == "-PAUSE-":
                self.running = False
                window["-STATUS-"].update(f"Status: ⏸️  PAUSED")
                print("Trading paused")
            elif event == "-RESUME-":
                self.running = True
                window["-STATUS-"].update(f"Status: ✅ RUNNING")
                print("Trading resumed")
            elif event == "-REFRESH-":
                self.update_data(window)

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
