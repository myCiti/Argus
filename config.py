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
BUTTON_TRIGGER_MS = 200       # Time button must be held to trigger action (500 ms)
DOOR_CYCLE_MS = 8000          # Standard travel time for opening/closing (8 seconds)
SAFETY_REVERSE_MS = 200       # Duration of reverse open pulse when sensor is tripped (200 ms)
POLL_INTERVAL_MS = 10         # Main loop polling interval (10 ms)
SENSOR_IGNORE_MS = 8000       # Ignore sensor for this long after it triggers
HEARTBEAT_MS = 500           # Heartbeat LED toggle interval (1 second)

# Onboard RGB LED (WS2812 / NeoPixel)
PIN_LED_RGB = 16
PIN_LED_EXT = 6 # External LED (PWM)

# Fade parameters
FADE_STEP = 3 # how fast brightness changes
FADE_MIN = 0
FADE_MAX = 255

