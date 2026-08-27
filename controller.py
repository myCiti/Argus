# controller.py
# State machine and door logic implementation for Project Argus

import machine
import time
import config
import neopixel

class DoorState:
    IDLE = "IDLE"
    OPENING = "OPENING"
    CLOSING = "CLOSING"
    REVERSING = "REVERSING"

class DoorController:
    """
    Non-blocking Door Controller implementing:
    - 500ms press debounce/trigger for Open/Close
    - 8-second standard run cycle
    - Safety sensor reversal (instant stop + 200ms reverse open)
    - Constant pressure closing support
    - Mutual exclusion hardware interlock
    """
    def __init__(self, pin_sensor, pin_btn_open, pin_btn_close, pin_out_open, pin_out_close,
                 pin_led_rgb=None, pin_led_ext=None):
        self.sensor = pin_sensor
        self.btn_open = pin_btn_open
        self.btn_close = pin_btn_close
        self.out_open = pin_out_open
        self.out_close = pin_out_close
        
        # NeoPixel RGB
        self.led_rgb = None
        if pin_led_rgb is not None:
            self.led_rgb = neopixel.NeoPixel(machine.Pin(pin_led_rgb), 1)

        # PWM LED external
        self.led_ext_pwm = None
        if pin_led_ext is not None:
            self.led_ext_pwm = machine.PWM(pin_led_ext)
            self.led_ext_pwm.freq(1000)

        # Fade parameters
        self.fade_value = 0
        self.fade_direction = 1

        # Ensure all outputs start LOW (inactive)
        self._set_outputs(0, 0)

        # Internal state
        self.state = DoorState.IDLE
        self.state_start_time = 0

        # Sensor blind window: sensor ignored until this timestamp (ticks_ms)
        self.sensor_ignore_until = 0

        # Button tracking
        self.open_press_start = None
        self.open_triggered = False
        self.close_press_start = None
        self.close_triggered = False

    def _get_time_ms(self):
        """Cross-platform/MicroPython ticks helper."""
        return time.ticks_ms()

    def _time_diff(self, t_now, t_start):
        """Calculates elapsed milliseconds safely handling wrap-around."""
        return time.ticks_diff(t_now, t_start)

    def _set_outputs(self, open_val, close_val):
        """
        Hardware interlock: guarantees Open and Close outputs are never 
        simultaneously active.
        """
        if open_val and close_val:
            # Interlock violation: both outputs are the same, turn them off
            self.out_open.value(0)
            self.out_close.value(0)

        self.out_open.value(open_val)
        self.out_close.value(close_val)
    
    def _sensor_effective(self, now):
        """True if sensor is active AND not within the post-trigger blind window."""
        if self._time_diff(now, self.sensor_ignore_until) < 0:
            return False  # inside the ignore window
        return self._is_active(self.sensor)

    def _is_active(self, pin):
        """Returns True if the pin is at its active logic level."""
        return pin.value() == config.INPUT_ACTIVE_LEVEL

    def _read_inputs(self, now):
        """Reads input pins and manages 500ms press detection."""
        # --- Read Open Button ---
        if self._is_active(self.btn_open):
            if self.open_press_start is None:
                self.open_press_start = now
        else:
            self.open_press_start = None
            self.open_triggered = False

        # --- Read Close Button ---
        if self._is_active(self.btn_close):
            if self.close_press_start is None:
                self.close_press_start = now
        else:
            self.close_press_start = None
            self.close_triggered = False
    
    # ---------------------------------------------------------
    # Fade synchronized for RGB + PWM
    # ---------------------------------------------------------
    def _update_fade(self):
        self.fade_value += self.fade_direction * config.FADE_STEP

        if self.fade_value >= config.FADE_MAX:
            self.fade_value = config.FADE_MAX
            self.fade_direction = -1

        elif self.fade_value <= config.FADE_MIN:
            self.fade_value = config.FADE_MIN
            self.fade_direction = 1

        # RGB NeoPixel
        if self.led_rgb:
            self.led_rgb[0] = (0, 0, self.fade_value)
            self.led_rgb.write()

        # PWM LED external
        if self.led_ext_pwm:
            duty = int(self.fade_value * 257)  # 0–255 → 0–65535
            self.led_ext_pwm.duty_u16(duty)

    # ---------------------------------------------------------
    
    def start_opening(self, now):
        """Transitions to OPENING state (Open is always safe and permitted)."""
        print("[Argus] Starting OPEN (8 seconds)...")
        self.state = DoorState.OPENING
        self.state_start_time = now
        self._set_outputs(1, 0)

    def start_closing(self, now):
        """Transitions to CLOSING state if safety sensor is clear."""
        if self._sensor_effective(now):
            return False

        print("[Argus] Starting CLOSE (8 seconds or constant pressure)...")
        self.state = DoorState.CLOSING
        self.state_start_time = now
        self._set_outputs(0, 1)
        return True

    def trigger_safety_reversal(self, now):
        """Emergency reverse; blind the sensor so the latched pulse
        doesn't freeze operation or cause an immediate re-trigger."""
        print("[Argus] SAFETY TRIGGERED! Reversing...")
        self.sensor_ignore_until = now + config.SENSOR_IGNORE_MS
        self.state = DoorState.REVERSING
        self.state_start_time = now
        self._set_outputs(1, 0)

    def stop_to_idle(self):
        """Stops all outputs and returns to IDLE."""
        self._set_outputs(0, 0)
        self.state = DoorState.IDLE
        print("[Argus] Door stopped. System IDLE.")

    def update(self):
        """
        Main non-blocking tick function. Must be called repeatedly in the main loop.
        """
        now = self._get_time_ms()
        self._read_inputs(now)
        
        # Fade update
        self._update_fade()

        # -------------------------------------------------------------
        # 1. Check Button Triggers for 500ms continuous press
        # -------------------------------------------------------------
        # Open button held for >= 500ms (Always responsive)
        if self.open_press_start is not None and not self.open_triggered:
            if self._time_diff(now, self.open_press_start) >= config.BUTTON_TRIGGER_MS:
                self.open_triggered = True
                if self.state in (DoorState.IDLE, DoorState.CLOSING, DoorState.REVERSING):
                    self.start_opening(now)

        # Close button held >= 500ms
        # Allowed from IDLE and OPENING, but gated by the effective sensor.
        if self.close_press_start is not None and not self.close_triggered:
            if self._time_diff(now, self.close_press_start) >= config.BUTTON_TRIGGER_MS:
                if self.state in (DoorState.IDLE, DoorState.OPENING):
                    if not self._sensor_effective(now):
                        self.close_triggered = True
                        self.start_closing(now)
        # -------------------------------------------------------------
        # 2. State Machine Progress and Safety Handling
        # -------------------------------------------------------------
        if self.state == DoorState.OPENING:
            elapsed = self._time_diff(now, self.state_start_time)
            if elapsed >= config.DOOR_CYCLE_MS:
                print("[Argus] Open cycle complete.")
                self.stop_to_idle()

        elif self.state == DoorState.CLOSING:
            # Priority 1: Check Safety Sensor (Instant Reversal)
            if self._sensor_effective(now):
                self.trigger_safety_reversal(now)
                return

            elapsed = self._time_diff(now, self.state_start_time)
            btn_close_active = self._is_active(self.btn_close)

            # Standard 8s elapsed and user not holding constant pressure
            if elapsed >= config.DOOR_CYCLE_MS and not btn_close_active:
                print("[Argus] Close cycle complete.")
                self.stop_to_idle()
            elif elapsed >= config.DOOR_CYCLE_MS and btn_close_active:
                # Constant pressure: continue closing as long as held
                print("[Argus] Constant pressure detected. Continuing to close.")
                self.sensor_ignore_until = now + 500


        elif self.state == DoorState.REVERSING:
            # Manual override: user takes control immediately during reversal.
            # Open always allowed; Close re-checked against the (blinded) sensor.
            if self.open_triggered:
                print("[Argus] Manual override during reversal: opening.")
                self.start_opening(now)
                return

            if self._time_diff(now, self.state_start_time) >= config.SAFETY_REVERSE_MS:
                print("[Argus] Safety reversal complete.")
                self.stop_to_idle()
                
        elif self.state == DoorState.IDLE:
            # Everything stopped, waiting for user trigger
            pass

if __name__ == "__main__":
    
    import time
    sensor = machine.Pin(config.PIN_SENSOR, machine.Pin.IN, machine.Pin.PULL_UP)
    # Inputs with internal pull-up (Active LOW: 0V = 0)
    sensor = machine.Pin(config.PIN_SENSOR, machine.Pin.IN, machine.Pin.PULL_UP)
    btn_open = machine.Pin(config.PIN_BTN_OPEN, machine.Pin.IN, machine.Pin.PULL_UP)
    btn_close = machine.Pin(config.PIN_BTN_CLOSE, machine.Pin.IN, machine.Pin.PULL_UP)

    # Outputs (Active HIGH: 3.3V = 1, initialized to 0 / LOW)
    out_open = machine.Pin(config.PIN_OUT_OPEN, machine.Pin.OUT, value=0)
    out_close = machine.Pin(config.PIN_OUT_CLOSE, machine.Pin.OUT, value=0)
    
    controller = DoorController(sensor, btn_open, btn_close, out_open, out_close)
    
    while True:
        print(f'{time.ticks_ms()} Sensor: {controller._sensor_effective(time.ticks_ms())}')
        time.sleep_ms(200)