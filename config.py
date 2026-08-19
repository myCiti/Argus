# config.py
# Pin mapping and timing configuration for Project Argus door controller

# --- GPIO Pin Mapping ---
# Inputs (Active LOW / 0V = 0, Pull-Up by default)
PIN_SENSOR = 29
PIN_BTN_OPEN = 28
PIN_BTN_CLOSE = 27

# Input Active Level (0 = Active LOW / 0V, 1 = Active HIGH)
INPUT_ACTIVE_LEVEL = 0

# Outputs (Active HIGH / 3.3V = 1)
PIN_OUT_OPEN = 7
PIN_OUT_CLOSE = 8

# Onboard LED (Optional heartbeat indicator, GP25 on standard Pico or "LED" on Pico W / RP2040-Zero)
PIN_LED = 25

# --- Timing Parameters (in milliseconds) ---
BUTTON_TRIGGER_MS = 500       # Time button must be held to trigger action (500 ms)
DOOR_CYCLE_MS = 8000          # Standard travel time for opening/closing (8 seconds)
SAFETY_REVERSE_MS = 200       # Duration of reverse open pulse when sensor is tripped (200 ms)
SAFETY_DEADTIME_MS = 50       # Deadtime pause before changing motor directions
POLL_INTERVAL_MS = 10         # Main loop polling interval (10 ms)
