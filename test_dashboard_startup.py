#!/usr/bin/env python3
"""Test dashboard startup with detailed diagnostics."""

import sys
import os
import time

print("=" * 80)
print("DASHBOARD STARTUP DIAGNOSTIC TEST")
print("=" * 80)

# Check environment
print("\n1. Environment Variables:")
print(f"   DISPLAY: {os.getenv('DISPLAY', 'NOT SET')}")
print(f"   WAYLAND_DISPLAY: {os.getenv('WAYLAND_DISPLAY', 'NOT SET')}")
print(f"   XAUTHORITY: {os.getenv('XAUTHORITY', 'NOT SET')}")

# Check imports
print("\n2. Checking imports...")
try:
    from dotenv import load_dotenv
    print("   ✓ python-dotenv")
except ImportError as e:
    print(f"   ✗ python-dotenv: {e}")
    sys.exit(1)

try:
    from kalshi_api_client import KalshiAPIClient
    print("   ✓ KalshiAPIClient")
except ImportError as e:
    print(f"   ✗ KalshiAPIClient: {e}")
    sys.exit(1)

try:
    import PySimpleGUI as sg
    print("   ✓ PySimpleGUI")
except ImportError as e:
    print(f"   ✗ PySimpleGUI: {e}")
    sys.exit(1)

# Load environment
load_dotenv()

# Initialize API client
print("\n3. Initializing Kalshi API client...")
try:
    api_key_id = os.getenv('KALSHI_API_KEY_ID')
    private_key_path = os.getenv('KALSHI_PRIVATE_KEY_PATH')

    with open(private_key_path, 'r') as f:
        private_key_pem = f.read()

    client = KalshiAPIClient(api_key_id, private_key_pem)
    print("   ✓ API client initialized")
except Exception as e:
    print(f"   ✗ Failed to init API: {e}")
    sys.exit(1)

# Try to create GUI
print("\n4. Creating GUI window...")
try:
    sg.theme('DarkBlue3')
    sg.set_options(font=('Helvetica', 10))

    print("   - Theme set")
    print("   - Creating window...")

    layout = [
        [sg.Text('WeatherBot Dashboard Loading...', size=(40, 1))],
        [sg.Button('Test Button')]
    ]

    window = sg.Window('WeatherBot Dashboard Test', layout, finalize=True)
    print("   - Window created")

    # Try to show the window
    print("   - Attempting to show window...")
    event, values = window.read(timeout=2000)

    print(f"   ✓ Window displayed successfully! (event: {event})")
    window.close()

except Exception as e:
    print(f"   ✗ GUI creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ ALL TESTS PASSED - Dashboard should work")
print("=" * 80)
