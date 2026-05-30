#!/usr/bin/env python3
"""Quick tests of core modules."""

import sys
from datetime import date, timedelta

def test_config():
    """Verify city config."""
    from config import CITIES, WIN_MIN_H, WIN_MAX_H
    print("✓ Config loaded")
    print(f"  Cities: {len(CITIES)}")
    print(f"  Entry window: {WIN_MIN_H}-{WIN_MAX_H} hours")
    assert len(CITIES) == 11
    assert WIN_MIN_H == 18.0
    assert WIN_MAX_H == 30.0


def test_forecast():
    """Test forecast fetch."""
    from forecast_consensus import fetch_forecast
    tomorrow = date.today() + timedelta(days=1)

    result = fetch_forecast(40.7772, -73.8726, tomorrow)
    print("✓ Forecast consensus")
    print(f"  ICON: {result['icon']:.1f}°C" if result['icon'] else "  ICON: None")
    print(f"  GFS: {result['gfs']:.1f}°C" if result['gfs'] else "  GFS: None")
    print(f"  ECMWF: {result['ecmwf']:.1f}°C" if result['ecmwf'] else "  ECMWF: None")
    print(f"  Spread: {result['spread']:.1f}°C" if result['spread'] else "  Spread: None")
    print(f"  Agree: {result['agree']}")


def test_portfolio():
    """Test portfolio builder."""
    from portfolio_builder import build_portfolio, passes_filters

    forecast = {
        "icon": 20.5, "gfs": 20.8, "ecmwf": 19.9,
        "spread": 0.9, "agree": True
    }

    bins = [
        {"bin_low": 18, "bin_high": 19, "yes_price": 0.30, "token_id": "t1"},
        {"bin_low": 19, "bin_high": 20, "yes_price": 0.25, "token_id": "t2"},
        {"bin_low": 20, "bin_high": 21, "yes_price": 0.20, "token_id": "t3"},
        {"bin_low": 21, "bin_high": 22, "yes_price": 0.15, "token_id": "t4"},
    ]

    portfolio = build_portfolio(forecast, bins)
    print("✓ Portfolio builder")
    print(f"  Built: {len(portfolio) if portfolio else 0} bins")
    if portfolio:
        for b in portfolio:
            print(f"    {int(b['bin_low'])}-{int(b['bin_high'])}°C @ ${b['yes_price']:.2f}")
    print(f"  Passes filters: {passes_filters(portfolio) if portfolio else False}")


def test_market_scanner():
    """Test market scanner."""
    from market_scanner import scan_markets

    markets = [
        {
            "id": "m1", "tokenId": "t1",
            "question": "Will NYC high be 56-57°F on May 1?",
            "yes_price": 0.30
        },
        {
            "id": "m2", "tokenId": "t2",
            "question": "Will NYC high be 57-58°F on May 1?",
            "yes_price": 0.25
        },
    ]

    target = date(2026, 5, 1)
    results = scan_markets(markets, "NYC", target)
    print("✓ Market scanner")
    print(f"  Found: {len(results)} markets")
    for r in results:
        print(f"    {int(r['bin_low'])}-{int(r['bin_high'])}°{r['unit']} @ ${r['yes_price']:.2f}")


def test_trade_journal():
    """Test trade journal."""
    from trade_journal import TradeJournal
    import os

    # Use temp file
    journal = TradeJournal("test")
    tomorrow = date.today() + timedelta(days=1)

    success = journal.log_trade("NYC", tomorrow, 56, 57, 0.30, 2.0)
    print("✓ Trade journal")
    print(f"  Log success: {success}")

    # Clean up
    if os.path.exists("test_trades.csv"):
        os.remove("test_trades.csv")


def test_polymarket_client():
    """Test client init."""
    from polymarket_client import PolymarketClient

    client = PolymarketClient()
    print("✓ Polymarket client")
    print(f"  Live mode: {client.is_live_mode()}")
    print(f"  (Set POLYMARKET_PRIVATE_KEY to enable live trades)")


def test_telegram():
    """Test telegram notifier."""
    from telegram_notifier import TelegramNotifier

    notifier = TelegramNotifier()
    print("✓ Telegram notifier")
    print(f"  Enabled: {notifier.enabled}")
    print(f"  (Set TELEGRAM_BOT_TOKEN to enable alerts)")


if __name__ == "__main__":
    print("=== CORE MODULE TESTS ===\n")

    try:
        test_config()
        print()
        test_forecast()
        print()
        test_portfolio()
        print()
        test_market_scanner()
        print()
        test_trade_journal()
        print()
        test_polymarket_client()
        print()
        test_telegram()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
