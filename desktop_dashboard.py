"""
Phase 11: Native Desktop Dashboard (PySimpleGUI)

Standalone desktop application for real-time monitoring.
No web server required - runs as native GUI application.
"""

import PySimpleGUI as sg
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any
import json

# Configure theme
sg.theme('DarkBlue3')
sg.set_options(font=('Helvetica', 10))


class DesktopDashboard:
    """Native desktop dashboard using PySimpleGUI."""

    def __init__(self):
        """Initialize dashboard."""
        self.running = True
        self.refresh_interval = 15  # seconds

        # Sample data (in production, fetch from real sources)
        self.portfolio = {
            "total_capital": "$10,000.00",
            "available": "$5,000.00",
            "daily_pnl": "+$245.50",
            "total_pnl": "+$2,345.60",
            "open_positions": 3,
            "win_rate": "62.5%",
            "sharpe": "1.45"
        }

        self.positions = [
            {"city": "NYC", "bucket": ">75°F", "size": "50", "entry": "$0.62", "current": "$0.68", "pnl": "+$300"},
            {"city": "Chicago", "bucket": ">65°F", "size": "75", "entry": "$0.54", "current": "$0.58", "pnl": "+$300"},
            {"city": "LA", "bucket": ">85°F", "size": "25", "entry": "$0.65", "current": "$0.72", "pnl": "+$175"}
        ]

        self.status = {
            "system": "✅ RUNNING",
            "breaker": "✅ INACTIVE",
            "kalshi": "✅ HEALTHY",
            "open_meteo": "✅ HEALTHY",
            "nws": "✅ HEALTHY"
        }

        self.recent_events = [
            {"time": "14:35:22", "type": "Edge Detected", "city": "NYC", "edge": "13.0%"},
            {"time": "14:22:15", "type": "Order Executed", "city": "Chicago", "edge": "4.0%"},
            {"time": "14:10:50", "type": "Trade Resolved", "city": "NYC", "edge": "WIN"},
        ]

    def create_window(self):
        """Create the GUI window."""

        # Portfolio Section
        portfolio_layout = [
            [sg.Text("💰 PORTFOLIO", font=('Helvetica', 14, 'bold'))],
            [sg.Column([
                [sg.Text("Total Capital:", font=('Helvetica', 10)), sg.Text(self.portfolio["total_capital"], key="-CAPITAL-", font=('Helvetica', 10, 'bold'))],
                [sg.Text("Available:", font=('Helvetica', 10)), sg.Text(self.portfolio["available"], key="-AVAILABLE-", font=('Helvetica', 10, 'bold'))],
            ]), sg.Column([
                [sg.Text("Daily PnL:", font=('Helvetica', 10)), sg.Text(self.portfolio["daily_pnl"], key="-DAILY-", font=('Helvetica', 10, 'bold'), text_color='#4CAF50')],
                [sg.Text("Total PnL:", font=('Helvetica', 10)), sg.Text(self.portfolio["total_pnl"], key="-TOTAL-", font=('Helvetica', 10, 'bold'), text_color='#4CAF50')],
            ])],
            [sg.HSeparator()],
        ]

        # Performance Section
        performance_layout = [
            [sg.Text("📊 PERFORMANCE", font=('Helvetica', 14, 'bold'))],
            [sg.Column([
                [sg.Text("Open Positions:", font=('Helvetica', 10)), sg.Text(self.portfolio["open_positions"], key="-OPEN-", font=('Helvetica', 10, 'bold'))],
                [sg.Text("Win Rate:", font=('Helvetica', 10)), sg.Text(self.portfolio["win_rate"], key="-WINRATE-", font=('Helvetica', 10, 'bold'))],
            ]), sg.Column([
                [sg.Text("Sharpe Ratio:", font=('Helvetica', 10)), sg.Text(self.portfolio["sharpe"], key="-SHARPE-", font=('Helvetica', 10, 'bold'))],
                [sg.Text("Max Drawdown:", font=('Helvetica', 10)), sg.Text("8.3%", key="-DRAWDOWN-", font=('Helvetica', 10, 'bold'))],
            ])],
            [sg.HSeparator()],
        ]

        # Status Section
        status_layout = [
            [sg.Text("🔌 SYSTEM STATUS", font=('Helvetica', 14, 'bold'))],
            [sg.Column([
                [sg.Text(f"Status: {self.status['system']}", key="-STATUS-", font=('Helvetica', 10))],
                [sg.Text(f"Circuit Breaker: {self.status['breaker']}", key="-BREAKER-", font=('Helvetica', 10))],
            ]), sg.Column([
                [sg.Text(f"Kalshi: {self.status['kalshi']}", key="-KALSHI-", font=('Helvetica', 10))],
                [sg.Text(f"Open-Meteo: {self.status['open_meteo']}", key="-METEO-", font=('Helvetica', 10))],
            ])],
            [sg.HSeparator()],
        ]

        # Positions Section
        positions_layout = [
            [sg.Text("📍 OPEN POSITIONS", font=('Helvetica', 14, 'bold'))],
            [sg.Listbox(
                values=[f"{p['city']} {p['bucket']:12} | Size: {p['size']:3} | Entry: {p['entry']} | Current: {p['current']} | PnL: {p['pnl']}"
                        for p in self.positions],
                size=(90, 4),
                key="-POSITIONS-",
                disabled=True,
                background_color='#2B2B2B',
                text_color='#FFFFFF'
            )],
            [sg.HSeparator()],
        ]

        # Recent Events Section
        events_layout = [
            [sg.Text("📝 RECENT EVENTS", font=('Helvetica', 14, 'bold'))],
            [sg.Listbox(
                values=[f"{e['time']} | {e['type']:20} | {e['city']:10} | Edge: {e['edge']:6}"
                        for e in self.recent_events],
                size=(90, 4),
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
            size=(1000, 900),
            finalize=True,
            resizable=True,
            element_padding=(5, 5)
        )

        return window

    def update_data(self, window):
        """Update all displayed data."""
        current_time = datetime.now(timezone.utc).strftime('%H:%M:%S UTC')
        window["-TIMESTAMP-"].update(f"Last Updated: {current_time}")

        # Update portfolio (in production, fetch real data)
        window["-CAPITAL-"].update(self.portfolio["total_capital"])
        window["-DAILY-"].update(self.portfolio["daily_pnl"])

        # Refresh complete
        window["-REFRESH-"].update("✓ REFRESHED")
        window.refresh()

    def run(self):
        """Run the dashboard."""
        window = self.create_window()

        print("🚀 WeatherBot Desktop Dashboard started")
        print("Press any button or close window to interact")

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
                window["-STATUS-"].update(f"Status: ⏸️  PAUSED")
                print("Trading paused")
            elif event == "-RESUME-":
                window["-STATUS-"].update(f"Status: ✅ RUNNING")
                print("Trading resumed")
            elif event == "-REFRESH-":
                self.update_data(window)

        window.close()
        print("Dashboard closed")


def main():
    """Main entry point."""
    try:
        dashboard = DesktopDashboard()
        dashboard.run()
    except ImportError:
        print("❌ PySimpleGUI not installed. Install with:")
        print("   pip3 install PySimpleGUI")
        print("\nThen run again: python3 desktop_dashboard.py")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
