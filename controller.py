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

class DoorController:
    """
    Non-blocking Door Controller implementing:
    - Debounce/trigger for Open/Close buttons
    - Standard run cycle for opening/closing
    - Overcurrent obstacle sensor validation (configurable ms)
    - Hardware interlock protection
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
            self.led_ext_pwm = machine.PWM(machine.Pin(pin_led_ext))
            self.led_ext_pwm.freq(1000)

        # Fade parameters
        self.fade_value = 0
        self.fade_direction = 1

        # Ensure all outputs start LOW (inactive)
        self._set_outputs(0, 0)

        # Internal state
        self.state = DoorState.IDLE
        self.state_start_time = 0

        # Overcurrent sensor tracking
        self.sensor_debounce_start = None

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
            self.out_open.value(0)
            self.out_close.value(0)
            return

        self.out_open.value(open_val)
        self.out_close.value(close_val)

    def _is_active(self, pin):
        """Returns True if the pin is at its active logic level."""
        return pin.value() == config.INPUT_ACTIVE_LEVEL

    def _read_inputs(self, now):
        """Reads input pins and manages press detection."""
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
    
    def _update_fade(self):
        self.fade_value += self.fade_direction * config.FADE_STEP

        if self.fade_value >= config.FADE_MAX:
            self.fade_value = config.FADE_MAX
            self.fade_direction = -1

        elif self.fade_value <= config.FADE_MIN:
            self.fade_value = config.FADE_MIN
            self.fade_direction = 1

        # Modificăm culoarea pixelului 0 la fiecare iterație direct din buclă
        if self.led_rgb:
            self.led_rgb[0] = (0, 0, self.fade_value)
            self.led_rgb.write()

        # PWM LED external
        if self.led_ext_pwm:
            duty = int(self.fade_value * 257)  # 0–255 → 0–65535
            self.led_ext_pwm.duty_u16(duty)

    def start_opening(self, now):
        """Transitions to OPENING state."""
        print("[Argus] Starting OPEN...")
        self.state = DoorState.OPENING
        self.state_start_time = now
        self._set_outputs(1, 0)

    def start_closing(self, now):
        """Transitions to CLOSING state."""
        print("[Argus] Starting CLOSE...")
        self.state = DoorState.CLOSING
        self.state_start_time = now
        self._set_outputs(0, 1)

    def stop_to_idle(self):
        """Stops all outputs and returns to IDLE."""
        self._set_outputs(0, 0)
        self.state = DoorState.IDLE
        print("[Argus] Door stopped. System IDLE.")

    def update(self):
        """Main non-blocking tick function."""
        now = self._get_time_ms()
        self._read_inputs(now)
        
        # ELIMINAT VERIFICAREA COCOROATĂ: Rulăm direct fade-ul sincronizat mecanic cu sleep-ul de 10ms din main
        self._update_fade()

        # -------------------------------------------------------------
        # 1. Check Button Triggers
        # -------------------------------------------------------------
        # Open button held
        if self.open_press_start is not None and not self.open_triggered:
            if self._time_diff(now, self.open_press_start) >= config.BUTTON_TRIGGER_MS:
                self.open_triggered = True
                if self.state in (DoorState.IDLE, DoorState.CLOSING):
                    self.start_opening(now)

        # Close button held
        if self.close_press_start is not None and not self.close_triggered:
            if self._time_diff(now, self.close_press_start) >= config.BUTTON_TRIGGER_MS:
                if self.state in (DoorState.IDLE, DoorState.OPENING):
                    self.close_triggered = True
                    self.start_closing(now)

        # -------------------------------------------------------------
        # 2. Obstacle Overcurrent Sensor Logic (GP29)
        # -------------------------------------------------------------
        if self.state in (DoorState.OPENING, DoorState.CLOSING):
            if self.sensor.value() == 0:
                if self.sensor_debounce_start is None:
                    self.sensor_debounce_start = now
                elif self._time_diff(now, self.sensor_debounce_start) >= config.SENSOR_DEBOUNCE_MS:
                    print(f"[Argus] Obstacle detected! (Stable 0V for {config.SENSOR_DEBOUNCE_MS}ms). Hard Stop.")
                    self.stop_to_idle()
                    self.sensor_debounce_start = None
                    return
            else:
                self.sensor_debounce_start = None
        else:
            self.sensor_debounce_start = None

        # -------------------------------------------------------------
        # 3. State Machine Progress
        # -------------------------------------------------------------
        if self.state == DoorState.OPENING:
            elapsed = self._time_diff(now, self.state_start_time)
            if elapsed >= config.DOOR_CYCLE_MS:
                print("[Argus] Open cycle complete.")
                self.stop_to_idle()

        elif self.state == DoorState.CLOSING:
            elapsed = self._time_diff(now, self.state_start_time)
            btn_close_active = self._is_active(self.btn_close)

            if elapsed >= config.DOOR_CYCLE_MS and not btn_close_active:
                print("[Argus] Close cycle complete.")
                self.stop_to_idle()
