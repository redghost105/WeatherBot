#!/usr/bin/env python3
"""Minimal PySimpleGUI test to identify the exact failure point."""

import sys
import os

print("=" * 80)
print("MINIMAL PYSIMPLEGUI TEST")
print("=" * 80)

# Step 1: Environment
print("\n1. Environment:")
print(f"   DISPLAY: {os.getenv('DISPLAY', 'NOT SET')}")
print(f"   WAYLAND_DISPLAY: {os.getenv('WAYLAND_DISPLAY', 'NOT SET')}")

# Step 2: Import
print("\n2. Importing PySimpleGUI...")
try:
    import PySimpleGUI as sg
    print("   ✓ PySimpleGUI imported")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

# Step 3: Set theme
print("\n3. Setting theme...")
try:
    sg.theme('DarkBlue3')
    print("   ✓ Theme set")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

# Step 4: Set options (without icon)
print("\n4. Setting options...")
try:
    sg.set_options(font=('Helvetica', 10))
    print("   ✓ Options set")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

# Step 5: Create simple layout
print("\n5. Creating simple layout...")
try:
    layout = [
        [sg.Text('Test Window', size=(20, 1))],
        [sg.Button('OK'), sg.Button('Cancel')]
    ]
    print("   ✓ Layout created")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

# Step 6: Create window WITHOUT icon
print("\n6. Creating window (no icon)...")
try:
    window = sg.Window(
        "Test Window",
        layout,
        size=(400, 200),
        finalize=True
    )
    print("   ✓ Window created")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 7: Show window
print("\n7. Reading window (timeout 2 sec)...")
try:
    event, values = window.read(timeout=2000)
    print(f"   ✓ Window read successful (event: {event})")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 8: Close
print("\n8. Closing window...")
try:
    window.close()
    print("   ✓ Window closed")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ MINIMAL TEST PASSED")
print("=" * 80)
