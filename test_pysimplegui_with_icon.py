#!/usr/bin/env python3
"""Test PySimpleGUI with icon file (like the real dashboard)."""

import sys
import os

print("=" * 80)
print("PYSIMPLEGUI WITH ICON TEST")
print("=" * 80)

# Step 1: Import and setup
print("\n1. Setup...")
try:
    import PySimpleGUI as sg
    sg.theme('DarkBlue3')
    sg.set_options(font=('Helvetica', 10))
    print("   ✓ PySimpleGUI ready")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

# Step 2: Check icon file
icon_path = '/home/carter/claude_programs/Polymarket/weatherbot-icon.svg'
print(f"\n2. Icon file check...")
if os.path.exists(icon_path):
    print(f"   ✓ Icon exists: {icon_path}")
else:
    print(f"   ✗ Icon NOT found: {icon_path}")
    sys.exit(1)

# Step 3: Create window WITH icon
print("\n3. Creating window WITH icon...")
try:
    layout = [
        [sg.Text('Test with Icon', size=(20, 1))],
        [sg.Button('OK'), sg.Button('Cancel')]
    ]

    window = sg.Window(
        "Test with Icon",
        layout,
        icon=icon_path,
        size=(400, 200),
        finalize=True
    )
    print("   ✓ Window created with icon")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 4: Read window
print("\n4. Reading window (timeout 2 sec)...")
try:
    event, values = window.read(timeout=2000)
    print(f"   ✓ Window read successful (event: {event})")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 5: Close
print("\n5. Closing window...")
try:
    window.close()
    print("   ✓ Window closed")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ ICON TEST PASSED")
print("=" * 80)
