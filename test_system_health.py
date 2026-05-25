#!/usr/bin/env python3
"""Comprehensive system health check - Dashboard + Trading System."""

import os
import sys
from datetime import datetime, timezone

print("=" * 100)
print("SYSTEM HEALTH CHECK - DASHBOARD + TRADING SYSTEM")
print(f"Time: {datetime.now(timezone.utc).isoformat()}")
print("=" * 100)

# Test 1: Dashboard imports and initialization
print("\n1. DASHBOARD COMPONENT")
print("-" * 100)
try:
    from desktop_dashboard import RealDataDashboard
    print("   ✓ dashboard_dashboard.py imports successfully")

    dashboard = RealDataDashboard()
    print("   ✓ RealDataDashboard instance created")

    window = dashboard.create_window()
    print("   ✓ Window created successfully")

    event, values = window.read(timeout=1000)
    print(f"   ✓ Window read successful (event: {event})")

    window.close()
    print("   ✓ Window closed cleanly")

    print("   ✅ DASHBOARD: OPERATIONAL")
except Exception as e:
    print(f"   ❌ DASHBOARD FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Trading Engine imports and initialization
print("\n2. TRADING ENGINE COMPONENT")
print("-" * 100)
try:
    from trading_engine import TradingEngine
    print("   ✓ trading_engine.py imports successfully")

    engine = TradingEngine()
    print("   ✓ TradingEngine instance created")
    print(f"   ✓ Risk Manager configured: global={engine.risk_manager.global_exposure_pct*100:.1f}%, per_city={engine.risk_manager.per_city_exposure_pct*100:.1f}%, single_trade={engine.risk_manager.single_trade_size_pct*100:.1f}%")
    print(f"   ✓ Signal thresholds: min_edge={engine.signal_generator.min_edge_threshold*100:.0f}%, min_confidence={engine.signal_generator.min_confidence:.0f}%")

    print("   ✅ TRADING ENGINE: OPERATIONAL")
except Exception as e:
    print(f"   ❌ TRADING ENGINE FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Market discovery
print("\n3. MARKET DISCOVERY")
print("-" * 100)
try:
    markets = engine.scan_markets()
    print(f"   ✓ Market scan completed: {len(markets)} total markets found")

    # Group by city
    by_city = {}
    for m in markets:
        ticker = m.get('ticker', '')
        if 'NY' in ticker:
            city = 'NYC'
        elif 'CHI' in ticker:
            city = 'Chicago'
        elif 'DFW' in ticker:
            city = 'Dallas'
        elif 'DEN' in ticker:
            city = 'Denver'
        elif 'LAX' in ticker:
            city = 'LA'
        else:
            city = 'Other'
        by_city[city] = by_city.get(city, 0) + 1

    for city in sorted(by_city.keys()):
        print(f"     • {city}: {by_city[city]} markets")

    print("   ✅ MARKET DISCOVERY: OPERATIONAL")
except Exception as e:
    print(f"   ❌ MARKET DISCOVERY FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Signal generation (if markets available)
print("\n4. SIGNAL GENERATION")
print("-" * 100)
try:
    signals = engine.generate_signals(markets)
    print(f"   ✓ Signal generation completed: {len(signals)} signals generated from {len(markets)} markets")

    if signals:
        by_city = {}
        for s in signals:
            ticker = s.market_ticker
            if 'NY' in ticker:
                city = 'NYC'
            elif 'CHI' in ticker:
                city = 'Chicago'
            elif 'DFW' in ticker:
                city = 'Dallas'
            elif 'DEN' in ticker:
                city = 'Denver'
            elif 'LAX' in ticker:
                city = 'LA'
            else:
                city = 'Other'
            by_city[city] = by_city.get(city, 0) + 1

        for city in sorted(by_city.keys()):
            print(f"     • {city}: {by_city[city]} signals")

        # Show best signal
        best = max(signals, key=lambda s: s.edge_pct)
        print(f"   • Best signal: {best.market_ticker} edge={best.edge_pct:.1f}% confidence={best.confidence:.0f}%")
    else:
        print("   • No signals generated (this is normal if no markets are in 18-30h window)")

    print("   ✅ SIGNAL GENERATION: OPERATIONAL")
except Exception as e:
    print(f"   ❌ SIGNAL GENERATION FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Summary
print("\n" + "=" * 100)
print("SYSTEM HEALTH: ✅ ALL SYSTEMS OPERATIONAL")
print("=" * 100)
print("""
Components verified:
  ✅ Dashboard UI (PySimpleGUI window creation and event loop)
  ✅ Trading Engine (core logic and risk management)
  ✅ Market Discovery (Kalshi API weather market scanning)
  ✅ Signal Generation (weather prediction and edge calculation)

Ready for production trading (paper mode).
""")
