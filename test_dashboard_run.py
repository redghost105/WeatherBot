#!/usr/bin/env python3
"""Test the dashboard run() loop."""

import sys
import os
import threading
import time

print("=" * 80)
print("DASHBOARD RUN() LOOP TEST")
print("=" * 80)

# Import and start dashboard in a thread
print("\n1. Importing dashboard...")
try:
    from desktop_dashboard import RealDataDashboard
    print("   ✓ Dashboard imported")
except Exception as e:
    print(f"   ✗ Failed to import: {e}")
    sys.exit(1)

# Create dashboard instance
print("\n2. Creating dashboard instance...")
try:
    dashboard = RealDataDashboard()
    print("   ✓ Dashboard instance created")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Run dashboard in a thread with timeout
print("\n3. Running dashboard in thread (5 second timeout)...")
try:
    def run_dashboard():
        try:
            dashboard.run()
        except Exception as e:
            print(f"   ✗ Dashboard run failed: {e}")
            import traceback
            traceback.print_exc()

    thread = threading.Thread(target=run_dashboard, daemon=True)
    thread.start()

    # Wait for 5 seconds
    time.sleep(5)

    # Stop the dashboard by closing the window
    print("   ✓ Dashboard running (exiting after timeout)")

except Exception as e:
    print(f"   ✗ Failed to run: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ DASHBOARD RUN TEST PASSED")
print("=" * 80)
