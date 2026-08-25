# controller.py
# State machine and door logic implementation for Project Argus

try:
    import time
except ImportError:
    import utime as time

import config

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
    def __init__(self, pin_sensor, pin_btn_open, pin_btn_close, pin_out_open, pin_out_close):
        self.sensor = pin_sensor
        self.btn_open = pin_btn_open
        self.btn_close = pin_btn_close
        self.out_open = pin_out_open
        self.out_close = pin_out_close

        # Ensure all outputs start LOW (inactive)
        self._set_outputs(0, 0)

        # Internal state
        self.state = DoorState.IDLE
        self.state_start_time = 0

        # Button tracking
        self.open_press_start = None
        self.open_triggered = False
        self.close_press_start = None
        self.close_triggered = False

    def _get_time_ms(self):
        """Cross-platform/MicroPython ticks helper."""
        if hasattr(time, "ticks_ms"):
            return time.ticks_ms()
        return int(time.time() * 1000)

    def _time_diff(self, t_now, t_start):
        """Calculates elapsed milliseconds safely handling wrap-around."""
        if hasattr(time, "ticks_diff"):
            return time.ticks_diff(t_now, t_start)
        return t_now - t_start

    def _set_outputs(self, open_val, close_val):
        """
        Hardware interlock: guarantees Open and Close outputs are never 
        simultaneously active.
        """
        if open_val and close_val:
            # Dangerous condition: force both OFF
            self.out_open.value(0)
            self.out_close.value(0)
            return

        # Turn OFF active channel before activating the other (break-before-make)
        if open_val:
            self.out_close.value(0)
            self.out_open.value(1)
        elif close_val:
            self.out_open.value(0)
            self.out_close.value(1)
        else:
            self.out_open.value(0)
            self.out_close.value(0)

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

    def start_opening(self, now):
        """Transitions to OPENING state (Open is always safe and permitted)."""
        print("[Argus] Starting OPEN (8 seconds)...")
        self.state = DoorState.OPENING
        self.state_start_time = now
        self._set_outputs(1, 0)

    def start_closing(self, now):
        """Transitions to CLOSING state if safety sensor is clear."""
        if self._is_active(self.sensor):
            return False

        print("[Argus] Starting CLOSE (8 seconds or constant pressure)...")
        self.state = DoorState.CLOSING
        self.state_start_time = now
        self._set_outputs(0, 1)
        return True

    def trigger_safety_reversal(self, now):
        """Emergency stop closing and reverse open for 200ms."""
        print("[Argus] SAFETY TRIGGERED! Obstruction detected while closing. Reversing for 200ms...")
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

        # -------------------------------------------------------------
        # 1. Check Button Triggers for 500ms continuous press
        # -------------------------------------------------------------
        # Open button held for >= 500ms (Always responsive)
        if self.open_press_start is not None and not self.open_triggered:
            if self._time_diff(now, self.open_press_start) >= config.BUTTON_TRIGGER_MS:
                self.open_triggered = True
                if self.state in (DoorState.IDLE, DoorState.CLOSING, DoorState.REVERSING):
                    self.start_opening(now)

        # Close button held for >= 500ms
        if self.close_press_start is not None and not self.close_triggered:
            if self._time_diff(now, self.close_press_start) >= config.BUTTON_TRIGGER_MS:
                if self.state in (DoorState.IDLE, DoorState.OPENING):
                    if not self._is_active(self.sensor):
                        self.close_triggered = True
                        self.start_closing(now)
                    # Note: If sensor is active (e.g. 1s pulse), we don't set close_triggered yet.
                    # As soon as the sensor pulse ends, closing will start immediately!

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
            if self._is_active(self.sensor):
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
                pass

        elif self.state == DoorState.REVERSING:
            elapsed = self._time_diff(now, self.state_start_time)
            if elapsed >= config.SAFETY_REVERSE_MS:
                print("[Argus] Safety reversal complete.")
                self.stop_to_idle()

        elif self.state == DoorState.IDLE:
            # Everything stopped, waiting for user trigger
            pass
