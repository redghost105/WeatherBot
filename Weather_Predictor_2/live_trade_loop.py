import schedule
import time
import os
from datetime import datetime, date, timedelta
import config
from forecast_consensus import fetch_forecast
from market_scanner import scan_markets
from portfolio_builder import build_portfolio, passes_filters
from polymarket_client import PolymarketClient
from trade_journal import TradeJournal
from telegram_notifier import TelegramNotifier
from dotenv import load_dotenv

load_dotenv()

def in_window(target_date_utc, now_utc):
    """Check if current time is in 18-30h window before target_date."""
    resolve_time = target_date_utc + timedelta(hours=24)
    hours_until = (resolve_time - now_utc).total_seconds() / 3600
    return config.WIN_MIN_H <= hours_until <= config.WIN_MAX_H


def scan_cycle():
    """Scan, fetch forecasts, build portfolios, place REAL orders."""
    now = datetime.utcnow()
    target_date = date.today() + timedelta(days=1)

    print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] Scanning markets (LIVE MODE)...")

    client = PolymarketClient()
    if not client.is_live_mode():
        print("ERROR: Live mode not initialized. Set POLYMARKET_PRIVATE_KEY and POLYMARKET_SAFE_ADDRESS.")
        return

    journal = TradeJournal("live")
    notifier = TelegramNotifier()
    stake_per_bin = float(os.getenv("STAKE_PER_BIN", "2.0"))

    for city, city_config in config.CITIES.items():
        # Check entry window
        if not in_window(target_date, now):
            print(f"  {city}: Outside entry window")
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
            print(f"  {city}: Models disagree")
            continue

        # Scan markets (would use real API here)
        markets = scan_markets([], city, target_date)
        if not markets:
            print(f"  {city}: No markets found")
            continue

        # Build portfolio
        portfolio = build_portfolio(forecast, markets)
        if portfolio is None or not passes_filters(portfolio):
            print(f"  {city}: Invalid portfolio")
            continue

        # Place REAL orders
        bins = []
        stakes = []
        order_ids = []

        for bin_data in portfolio:
            price = bin_data["yes_price"]
            order_id = client.place_limit_order(
                token_id=bin_data["token_id"],
                price=price,
                amount_usdc=stake_per_bin
            )

            if order_id:
                success = journal.log_trade(
                    city=city,
                    target_date=target_date,
                    bin_low=bin_data["bin_low"],
                    bin_high=bin_data["bin_high"],
                    yes_price=price,
                    stake_usdc=stake_per_bin,
                    order_id=order_id
                )

                if success:
                    bins.append(bin_data)
                    stakes.append(stake_per_bin)
                    order_ids.append(order_id)
                    print(
                        f"  {city}: LIVE ORDER {int(bin_data['bin_low'])}-{int(bin_data['bin_high'])}°"
                        f" @ ${price:.2f} x ${stake_per_bin:.2f} (ID: {order_id[:8]}...)"
                    )
            else:
                print(f"  {city}: Order placement failed for {int(bin_data['bin_low'])}-{int(bin_data['bin_high'])}°")

        if bins:
            notifier.notify_trade_placed("live", city, target_date, bins, stakes)


def scheduled_scan():
    """Wrapper for schedule."""
    try:
        scan_cycle()
    except Exception as e:
        print(f"Scan error: {e}")


if __name__ == "__main__":
    print("=== LIVE TRADE LOOP ===")
    print(f"Entry window: {config.WIN_MIN_H}-{config.WIN_MAX_H} hours before resolution")
    print("REAL ORDERS will be placed. Scanning every 10 minutes...")

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
