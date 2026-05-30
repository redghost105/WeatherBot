#!/usr/bin/env python3
"""Test running the actual dashboard initialization."""

import sys
import os
from datetime import datetime, timezone

print("=" * 80)
print("DASHBOARD DIRECT TEST")
print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
print("=" * 80)

# Set up minimal logging to see what's happening
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

print("\n1. Checking environment...")
print(f"   DISPLAY: {os.getenv('DISPLAY', 'NOT SET')}")
print(f"   WAYLAND_DISPLAY: {os.getenv('WAYLAND_DISPLAY', 'NOT SET')}")

print("\n2. Importing desktop_dashboard...")
try:
    from desktop_dashboard import RealDataDashboard
    print("   ✓ desktop_dashboard imported")
except Exception as e:
    print(f"   ✗ Failed to import: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n3. Creating RealDataDashboard instance...")
try:
    print("   - This will call __init__ which:")
    print("     • initializes Kalshi API client")
    print("     • refreshes all data")
    print("     • may fetch weather data")
    dashboard = RealDataDashboard()
    print("   ✓ RealDataDashboard instance created")
except Exception as e:
    print(f"   ✗ Failed to create instance: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n4. Creating window...")
try:
    print("   - Calling dashboard.create_window()")
    window = dashboard.create_window()
    print("   ✓ Window created successfully")
except Exception as e:
    print(f"   ✗ Failed to create window: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n5. Testing window read (timeout 2 sec)...")
try:
    event, values = window.read(timeout=2000)
    print(f"   ✓ Window read successful (event: {event})")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n6. Closing window...")
try:
    window.close()
    print("   ✓ Window closed")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ DASHBOARD DIRECT TEST PASSED")
print("=" * 80)
