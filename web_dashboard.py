"""
Phase 11: Lightweight Web Dashboard

FastAPI-based dashboard for real-time monitoring.

Features:
- Portfolio summary (capital, PnL, exposure)
- Open positions by city
- Recent predictions and trades
- System status and health metrics
- Auto-refresh every 10-30 seconds
- Responsive design (works on mobile too)
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


# Data models
class Position(BaseModel):
    city: str
    bucket: str
    ticker: str
    size: int
    entry_price: float
    current_price: float
    pnl_cents: int


class Trade(BaseModel):
    id: str
    city: str
    bucket: str
    size: int
    entry_time: str
    exit_time: Optional[str]
    pnl_cents: int
    status: str  # OPEN, RESOLVED_WIN, RESOLVED_LOSS


class SystemStatus(BaseModel):
    status: str  # RUNNING, PAUSED, ERROR
    circuit_breaker_active: bool
    api_health: Dict[str, bool]
    uptime_hours: float
    last_update: str


class PortfolioSummary(BaseModel):
    total_capital_cents: int
    available_balance_cents: int
    used_margin_cents: int
    daily_pnl_cents: int
    weekly_pnl_cents: int
    monthly_pnl_cents: int
    total_pnl_cents: int
    open_positions: int
    win_rate: float
    sharpe_ratio: float


class DashboardData(BaseModel):
    portfolio: PortfolioSummary
    positions: List[Position]
    recent_trades: List[Trade]
    system_status: SystemStatus
    predictions: List[Dict[str, Any]]


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="WeatherBot Dashboard",
        description="Real-time monitoring dashboard",
        version="1.0.0"
    )

    # Store runtime data (in production, use proper state management)
    app.state.portfolio = {
        "total_capital_cents": 1000000,
        "available_balance_cents": 500000,
        "used_margin_cents": 500000,
        "daily_pnl_cents": 12450,
        "weekly_pnl_cents": 45670,
        "monthly_pnl_cents": 89340,
        "total_pnl_cents": 234560,
        "open_positions": 3,
        "win_rate": 62.5,
        "sharpe_ratio": 1.45
    }

    app.state.positions = [
        {
            "city": "NYC",
            "bucket": ">75°F",
            "ticker": "KXHIGHNY-26MAY21-T75",
            "size": 50,
            "entry_price": 0.62,
            "current_price": 0.68,
            "pnl_cents": 300
        },
        {
            "city": "Chicago",
            "bucket": ">65°F",
            "ticker": "KXHIGHCHI-26MAY21-T65",
            "size": 75,
            "entry_price": 0.54,
            "current_price": 0.58,
            "pnl_cents": 300
        },
        {
            "city": "LA",
            "bucket": ">85°F",
            "ticker": "KXHIGHLA-26MAY21-T85",
            "size": 25,
            "entry_price": 0.65,
            "current_price": 0.72,
            "pnl_cents": 175
        }
    ]

    app.state.system_status = {
        "status": "RUNNING",
        "circuit_breaker_active": False,
        "api_health": {
            "kalshi": True,
            "open_meteo": True,
            "nws": True
        },
        "uptime_hours": 48.5,
        "last_update": datetime.now(timezone.utc).isoformat()
    }

    # Routes
    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        """Serve the main dashboard HTML."""
        return get_dashboard_html()

    @app.get("/api/data", response_model=DashboardData)
    async def get_dashboard_data():
        """Get all dashboard data as JSON."""
        try:
            return DashboardData(
                portfolio=PortfolioSummary(**app.state.portfolio),
                positions=[Position(**p) for p in app.state.positions],
                recent_trades=[
                    Trade(
                        id="TRADE001",
                        city="NYC",
                        bucket=">75°F",
                        size=50,
                        entry_time=datetime.now(timezone.utc).isoformat(),
                        exit_time=None,
                        pnl_cents=300,
                        status="OPEN"
                    )
                ],
                system_status=SystemStatus(**app.state.system_status),
                predictions=[
                    {
                        "city": "NYC",
                        "bucket": ">75°F",
                        "confidence": 82.5,
                        "edge": 13.0,
                        "model_prob": 0.68,
                        "market_price": 0.55,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                ]
            )
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/portfolio")
    async def get_portfolio():
        """Get portfolio summary."""
        return app.state.portfolio

    @app.get("/api/positions")
    async def get_positions():
        """Get open positions."""
        return app.state.positions

    @app.get("/api/status")
    async def get_status():
        """Get system status."""
        return app.state.system_status

    @app.post("/api/pause")
    async def pause_trading():
        """Pause trading."""
        app.state.system_status["status"] = "PAUSED"
        return {"status": "PAUSED"}

    @app.post("/api/resume")
    async def resume_trading():
        """Resume trading."""
        app.state.system_status["status"] = "RUNNING"
        return {"status": "RUNNING"}

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

    return app


def get_dashboard_html() -> str:
    """Return the dashboard HTML."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WeatherBot Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        header {
            color: white;
            margin-bottom: 30px;
            text-align: center;
        }

        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .status-bar {
            display: flex;
            gap: 20px;
            justify-content: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }

        .status-item {
            background: white;
            padding: 12px 20px;
            border-radius: 8px;
            font-weight: 500;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .status-item.running {
            border-left: 4px solid #4CAF50;
        }

        .status-item.warning {
            border-left: 4px solid #ff9800;
        }

        .status-item.error {
            border-left: 4px solid #f44336;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        .card h2 {
            font-size: 1.3em;
            margin-bottom: 15px;
            color: #1e3c72;
            border-bottom: 2px solid #2a5298;
            padding-bottom: 10px;
        }

        .metric {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }

        .metric:last-child {
            border-bottom: none;
        }

        .metric-label {
            color: #666;
            font-weight: 500;
        }

        .metric-value {
            font-weight: 600;
            color: #1e3c72;
        }

        .metric-value.positive {
            color: #4CAF50;
        }

        .metric-value.negative {
            color: #f44336;
        }

        .position-item {
            background: #f9f9f9;
            padding: 12px;
            border-left: 3px solid #2a5298;
            margin-bottom: 10px;
            border-radius: 4px;
        }

        .position-header {
            display: flex;
            justify-content: space-between;
            font-weight: 600;
            margin-bottom: 8px;
        }

        .position-detail {
            font-size: 0.9em;
            color: #666;
            display: flex;
            justify-content: space-between;
        }

        .controls {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }

        button {
            flex: 1;
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }

        .btn-pause {
            background: #ff9800;
            color: white;
        }

        .btn-pause:hover {
            background: #f57c00;
        }

        .btn-resume {
            background: #4CAF50;
            color: white;
        }

        .btn-resume:hover {
            background: #45a049;
        }

        .loading {
            text-align: center;
            padding: 20px;
            color: white;
        }

        @media (max-width: 768px) {
            h1 {
                font-size: 1.8em;
            }

            .grid {
                grid-template-columns: 1fr;
            }

            .status-bar {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 WeatherBot Dashboard</h1>
            <p>Real-time Trading Monitoring</p>
        </header>

        <div id="content" class="loading">
            <p>Loading dashboard...</p>
        </div>
    </div>

    <script>
        async function loadDashboard() {
            try {
                const response = await fetch('/api/data');
                if (!response.ok) throw new Error('Failed to load data');
                const data = await response.json();
                renderDashboard(data);
            } catch (error) {
                document.getElementById('content').innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
            }
        }

        function renderDashboard(data) {
            const portfolio = data.portfolio;
            const positions = data.positions;
            const status = data.system_status;

            let html = `
                <div class="status-bar">
                    <div class="status-item ${status.status === 'RUNNING' ? 'running' : 'warning'}">
                        ${status.status === 'RUNNING' ? '✅' : '⏸️'} Status: ${status.status}
                    </div>
                    <div class="status-item ${status.circuit_breaker_active ? 'error' : 'running'}">
                        ${status.circuit_breaker_active ? '🛑' : '✅'} Circuit Breaker: ${status.circuit_breaker_active ? 'ACTIVE' : 'INACTIVE'}
                    </div>
                </div>

                <div class="grid">
                    <div class="card">
                        <h2>💰 Portfolio</h2>
                        <div class="metric">
                            <span class="metric-label">Total Capital</span>
                            <span class="metric-value">$${(portfolio.total_capital_cents/100).toFixed(2)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Available Balance</span>
                            <span class="metric-value">$${(portfolio.available_balance_cents/100).toFixed(2)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Daily PnL</span>
                            <span class="metric-value ${portfolio.daily_pnl_cents >= 0 ? 'positive' : 'negative'}">
                                $${(portfolio.daily_pnl_cents/100).toFixed(2)}
                            </span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Total PnL</span>
                            <span class="metric-value ${portfolio.total_pnl_cents >= 0 ? 'positive' : 'negative'}">
                                $${(portfolio.total_pnl_cents/100).toFixed(2)}
                            </span>
                        </div>
                    </div>

                    <div class="card">
                        <h2>📊 Performance</h2>
                        <div class="metric">
                            <span class="metric-label">Win Rate</span>
                            <span class="metric-value">${portfolio.win_rate.toFixed(1)}%</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Sharpe Ratio</span>
                            <span class="metric-value">${portfolio.sharpe_ratio.toFixed(2)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Open Positions</span>
                            <span class="metric-value">${portfolio.open_positions}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Uptime</span>
                            <span class="metric-value">${status.uptime_hours.toFixed(1)}h</span>
                        </div>
                    </div>

                    <div class="card">
                        <h2>📍 Open Positions</h2>
            `;

            positions.forEach(pos => {
                const pnl = (pos.pnl_cents / 100).toFixed(2);
                html += `
                    <div class="position-item">
                        <div class="position-header">
                            <span>${pos.city} ${pos.bucket}</span>
                            <span style="color: ${pos.pnl_cents >= 0 ? '#4CAF50' : '#f44336'}">$${pnl}</span>
                        </div>
                        <div class="position-detail">
                            <span>Size: ${pos.size} contracts</span>
                            <span>Entry: ${(pos.entry_price*100).toFixed(0)}¢</span>
                        </div>
                    </div>
                `;
            });

            html += `
                        <div class="controls">
                            <button class="btn-pause" onclick="pauseTrading()">⏸️ Pause</button>
                            <button class="btn-resume" onclick="resumeTrading()">▶️ Resume</button>
                        </div>
                    </div>
                </div>
            `;

            document.getElementById('content').innerHTML = html;
        }

        async function pauseTrading() {
            await fetch('/api/pause', {method: 'POST'});
            loadDashboard();
        }

        async function resumeTrading() {
            await fetch('/api/resume', {method: 'POST'});
            loadDashboard();
        }

        // Load dashboard immediately and refresh every 15 seconds
        loadDashboard();
        setInterval(loadDashboard, 15000);
    </script>
</body>
</html>
    """


if __name__ == "__main__":
    import uvicorn

    app = create_app()
    print("🚀 Starting WeatherBot Dashboard on http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
