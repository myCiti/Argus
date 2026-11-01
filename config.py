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

# --- Timing Parameters (in milliseconds) ---
BUTTON_TRIGGER_MS = 200       # Time button must be held to trigger action
DOOR_CYCLE_MS = 16000         # Standard travel time for opening/closing (16 seconds)
POLL_INTERVAL_MS = 10         # Main loop polling interval (10 ms) pentru verificări rapide
HEARTBEAT_MS = 500            # Heartbeat LED toggle interval (500 ms)

# --- Overcurrent Sensor Parameters ---
SENSOR_DEBOUNCE_MS = 100      # Timpul de filtrare (100 ms) - Salvează pisica și ignoră șocul motorului

# Onboard RGB LED (WS2812 / NeoPixel)
PIN_LED_RGB = 16
PIN_LED_EXT = 6 # External LED (PWM)

# Fade parameters
FADE_STEP = 3 # how fast brightness changes
FADE_MIN = 0
FADE_MAX = 255
