"""
Phase 11: Performance Reports & Summaries

Generate daily and weekly performance reports.

Outputs:
- Telegram summaries
- HTML reports
- PDF reports (future)
- CSV data exports
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


class PerformanceReporter:
    """Generate comprehensive performance reports."""

    def __init__(self, reports_dir: str = "reports"):
        """Initialize reporter."""
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)
        logger.info(f"Performance reporter initialized: {self.reports_dir}")

    def generate_daily_summary(
        self,
        trades_count: int,
        pnl_cents: int,
        win_rate: float,
        sharpe: float,
        max_drawdown: float,
        capital_cents: int,
        date: Optional[datetime] = None
    ) -> Dict:
        """Generate daily performance summary."""
        if date is None:
            date = datetime.now(timezone.utc).date()

        summary = {
            "date": str(date),
            "trades": trades_count,
            "pnl_dollars": round(pnl_cents / 100, 2),
            "win_rate": round(win_rate, 2),
            "sharpe": round(sharpe, 2),
            "max_drawdown": round(max_drawdown, 2),
            "capital": round(capital_cents / 100, 2),
            "return_pct": round((pnl_cents / capital_cents) * 100, 2) if capital_cents > 0 else 0
        }

        # Save to JSON
        report_file = self.reports_dir / f"daily_{date}.json"
        with open(report_file, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Daily summary saved: {report_file}")
        return summary

    def generate_weekly_summary(
        self,
        daily_summaries: List[Dict]
    ) -> Dict:
        """Generate weekly summary from daily data."""
        if not daily_summaries:
            logger.warning("No daily summaries provided for weekly report")
            return {}

        total_trades = sum(d.get("trades", 0) for d in daily_summaries)
        total_pnl = sum(d.get("pnl_dollars", 0) for d in daily_summaries)
        avg_win_rate = sum(d.get("win_rate", 0) for d in daily_summaries) / len(daily_summaries)
        avg_sharpe = sum(d.get("sharpe", 0) for d in daily_summaries) / len(daily_summaries)
        max_dd = max(d.get("max_drawdown", 0) for d in daily_summaries)

        week_start = daily_summaries[0].get("date", "unknown")
        week_end = daily_summaries[-1].get("date", "unknown")

        summary = {
            "period": f"{week_start} to {week_end}",
            "days": len(daily_summaries),
            "total_trades": total_trades,
            "total_pnl": round(total_pnl, 2),
            "avg_daily_pnl": round(total_pnl / len(daily_summaries), 2),
            "avg_win_rate": round(avg_win_rate, 2),
            "avg_sharpe": round(avg_sharpe, 2),
            "max_drawdown": round(max_dd, 2),
            "trades_per_day": round(total_trades / len(daily_summaries), 1)
        }

        # Save to JSON
        report_file = self.reports_dir / f"weekly_{week_start}_to_{week_end}.json"
        with open(report_file, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Weekly summary saved: {report_file}")
        return summary

    def format_telegram_daily(self, summary: Dict) -> str:
        """Format daily summary for Telegram."""
        return f"""
<b>📊 Daily Summary</b>

<b>Date:</b> {summary.get('date', 'N/A')}

<b>Trading:</b>
  • Trades: {summary.get('trades', 0)}
  • Win Rate: {summary.get('win_rate', 0):.1f}%
  • PnL: ${summary.get('pnl_dollars', 0):+.2f}
  • Return: {summary.get('return_pct', 0):.2f}%

<b>Risk:</b>
  • Sharpe: {summary.get('sharpe', 0):.2f}
  • Max DD: {summary.get('max_drawdown', 0):.2f}%

<b>Capital:</b> ${summary.get('capital', 0):.2f}
"""

    def format_telegram_weekly(self, summary: Dict) -> str:
        """Format weekly summary for Telegram."""
        return f"""
<b>📈 Weekly Summary</b>

<b>Period:</b> {summary.get('period', 'N/A')}

<b>Trading:</b>
  • Total Trades: {summary.get('total_trades', 0)}
  • Avg Daily Trades: {summary.get('trades_per_day', 0):.1f}
  • Avg Win Rate: {summary.get('avg_win_rate', 0):.1f}%

<b>Performance:</b>
  • Total PnL: ${summary.get('total_pnl', 0):+.2f}
  • Avg Daily PnL: ${summary.get('avg_daily_pnl', 0):+.2f}
  • Avg Sharpe: {summary.get('avg_sharpe', 0):.2f}

<b>Risk:</b>
  • Max Drawdown: {summary.get('max_drawdown', 0):.2f}%
"""

    def format_html_report(self, summary: Dict, report_type: str = "daily") -> str:
        """Format summary as HTML report."""
        date = summary.get("date", "N/A")
        title = f"Daily Report - {date}" if report_type == "daily" else f"Weekly Report - {summary.get('period', 'N/A')}"

        pnl_value = summary.get("pnl_dollars", 0)
        pnl_color = "#4CAF50" if pnl_value >= 0 else "#f44336"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #1e3c72; border-bottom: 2px solid #2a5298; padding-bottom: 10px; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0; }}
        .metric-card {{ background: #f9f9f9; padding: 15px; border-radius: 6px; border-left: 3px solid #2a5298; }}
        .metric-label {{ color: #666; font-size: 0.9em; margin-bottom: 5px; }}
        .metric-value {{ font-size: 1.5em; font-weight: bold; color: #1e3c72; }}
        .metric-value.positive {{ color: #4CAF50; }}
        .metric-value.negative {{ color: #f44336; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #999; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>

        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Trades</div>
                <div class="metric-value">{summary.get('trades', 0)}</div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Win Rate</div>
                <div class="metric-value">{summary.get('win_rate', 0):.1f}%</div>
            </div>

            <div class="metric-card">
                <div class="metric-label">PnL</div>
                <div class="metric-value {'positive' if pnl_value >= 0 else 'negative'}">
                    ${pnl_value:+.2f}
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Return</div>
                <div class="metric-value">
                    {summary.get('return_pct', 0):.2f}%
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Sharpe Ratio</div>
                <div class="metric-value">{summary.get('sharpe', 0):.2f}</div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Max Drawdown</div>
                <div class="metric-value">{summary.get('max_drawdown', 0):.2f}%</div>
            </div>
        </div>

        <div class="footer">
            Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
        </div>
    </div>
</body>
</html>
"""
        return html

    def save_html_report(self, summary: Dict, filename: Optional[str] = None) -> Path:
        """Save HTML report to file."""
        if filename is None:
            date = summary.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
            filename = f"report_{date}.html"

        filepath = self.reports_dir / filename

        html = self.format_html_report(summary)
        with open(filepath, 'w') as f:
            f.write(html)

        logger.info(f"HTML report saved: {filepath}")
        return filepath

    def save_csv_export(
        self,
        trades: List[Dict],
        filename: Optional[str] = None
    ) -> Path:
        """Save trades to CSV for Excel analysis."""
        if not trades:
            logger.warning("No trades to export")
            return None

        if filename is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            filename = f"trades_{date}.csv"

        filepath = self.reports_dir / filename

        try:
            import csv
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=trades[0].keys())
                writer.writeheader()
                writer.writerows(trades)

            logger.info(f"CSV export saved: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save CSV export: {e}")
            return None


# Global reporter instance
_reporter_instance = None


def get_reporter() -> PerformanceReporter:
    """Get or create global reporter instance."""
    global _reporter_instance
    if _reporter_instance is None:
        _reporter_instance = PerformanceReporter()
    return _reporter_instance


def generate_daily_summary(
    trades_count: int,
    pnl_cents: int,
    win_rate: float,
    sharpe: float,
    max_drawdown: float,
    capital_cents: int
) -> Dict:
    """Generate and save daily performance summary."""
    reporter = get_reporter()
    return reporter.generate_daily_summary(
        trades_count, pnl_cents, win_rate, sharpe, max_drawdown, capital_cents
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    reporter = get_reporter()

    # Test daily summary
    summary = reporter.generate_daily_summary(
        trades_count=12,
        pnl_cents=45620,
        win_rate=65.5,
        sharpe=1.45,
        max_drawdown=8.3,
        capital_cents=1000000
    )

    print("Daily Summary:")
    print(reporter.format_telegram_daily(summary))

    # Save HTML report
    filepath = reporter.save_html_report(summary)
    print(f"\nHTML report saved: {filepath}")

    print("\n✓ Performance reporting system initialized")
