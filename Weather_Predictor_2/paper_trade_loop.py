import schedule
import time
from datetime import datetime, date, timedelta
import config
from forecast_consensus import fetch_forecast
from market_scanner import scan_markets
from portfolio_builder import build_portfolio, passes_filters
from trade_journal import TradeJournal
from telegram_notifier import TelegramNotifier

# Mock Polymarket API data for testing (in production, use real API)
MOCK_MARKETS = []

def in_window(target_date_utc, now_utc):
    """Check if current time is in 18-30h window before target_date."""
    resolve_time = target_date_utc + timedelta(hours=24)
    hours_until = (resolve_time - now_utc).total_seconds() / 3600
    return config.WIN_MIN_H <= hours_until <= config.WIN_MAX_H


def scan_cycle():
    """Scan all cities, fetch forecasts, build portfolios, log trades."""
    now = datetime.utcnow()
    target_date = date.today() + timedelta(days=1)

    print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] Scanning markets...")

    journal = TradeJournal("paper")
    notifier = TelegramNotifier()

    for city, city_config in config.CITIES.items():
        # Check entry window
        if not in_window(target_date, now):
            print(f"  {city}: Outside entry window (18-30h)")
            continue

        # Fetch forecast
        try:
            forecast = fetch_forecast(
                city_config["lat"],
                city_config["lon"],
                target_date
            )
        except Exception as e:
            print(f"  {city}: Forecast error - {e}")
            continue

        if not forecast["agree"]:
            print(f"  {city}: Models disagree (spread {forecast['spread']:.1f}°C)")
            continue

        # Scan markets
        markets = scan_markets(MOCK_MARKETS, city, target_date)
        if not markets:
            print(f"  {city}: No markets found")
            continue

        # Build portfolio
        portfolio = build_portfolio(forecast, markets)
        if portfolio is None:
            print(f"  {city}: No portfolio (agree={forecast['agree']})")
            continue

        # Check filters
        if not passes_filters(portfolio):
            print(f"  {city}: Filters failed")
            continue

        # Log trades
        bins = []
        stakes = []
        stake_per_bin = float(os.getenv("STAKE_PER_BIN", "2.0"))

        for bin_data in portfolio:
            success = journal.log_trade(
                city=city,
                target_date=target_date,
                bin_low=bin_data["bin_low"],
                bin_high=bin_data["bin_high"],
                yes_price=bin_data["yes_price"],
                stake_usdc=stake_per_bin,
                order_id=None
            )

            if success:
                bins.append(bin_data)
                stakes.append(stake_per_bin)
                print(
                    f"  {city}: BET {int(bin_data['bin_low'])}-{int(bin_data['bin_high'])}°"
                    f" @ ${bin_data['yes_price']:.2f} x ${stake_per_bin:.2f}"
                )

        if bins:
            notifier.notify_trade_placed("paper", city, target_date, bins, stakes)


def scheduled_scan():
    """Wrapper for schedule."""
    try:
        scan_cycle()
    except Exception as e:
        print(f"Scan error: {e}")


if __name__ == "__main__":
    import os

    print("=== PAPER TRADE LOOP ===")
    print(f"Entry window: {config.WIN_MIN_H}-{config.WIN_MAX_H} hours before resolution")
    print("Scanning every 10 minutes...")

    schedule.every(10).minutes.do(scheduled_scan)

    # Run initial scan immediately
    scheduled_scan()

    # Then schedule
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nExiting...")
