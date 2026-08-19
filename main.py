# main.py
# Main entry point for Project Argus on Raspberry Pi Pico (RP2040)

import machine
try:
    import time
except ImportError:
    import utime as time

import config
from controller import DoorController

def init_hardware():
    """Initializes and returns all GPIO pins with proper pull-downs and initial states."""
    print("------------------------------------------")
    print("Initializing Project Argus Door Controller")
    print("------------------------------------------")

    # Inputs with internal pull-up (Active LOW: 0V = 0)
    sensor = machine.Pin(config.PIN_SENSOR, machine.Pin.IN, machine.Pin.PULL_UP)
    btn_open = machine.Pin(config.PIN_BTN_OPEN, machine.Pin.IN, machine.Pin.PULL_UP)
    btn_close = machine.Pin(config.PIN_BTN_CLOSE, machine.Pin.IN, machine.Pin.PULL_UP)

    # Outputs (Active HIGH: 3.3V = 1, initialized to 0 / LOW)
    out_open = machine.Pin(config.PIN_OUT_OPEN, machine.Pin.OUT, value=0)
    out_close = machine.Pin(config.PIN_OUT_CLOSE, machine.Pin.OUT, value=0)

    # Optional status LED
    led = None
    try:
        led = machine.Pin(config.PIN_LED, machine.Pin.OUT, value=0)
    except Exception:
        pass

    print(f"Inputs  : Sensor=GP{config.PIN_SENSOR}, Open=GP{config.PIN_BTN_OPEN}, Close=GP{config.PIN_BTN_CLOSE}")
    print(f"Outputs : Open=GP{config.PIN_OUT_OPEN}, Close=GP{config.PIN_OUT_CLOSE}")
    print("Ready. Waiting for input...")
    
    return sensor, btn_open, btn_close, out_open, out_close, led

def main():
    sensor, btn_open, btn_close, out_open, out_close, led = init_hardware()
    controller = DoorController(sensor, btn_open, btn_close, out_open, out_close)

    last_heartbeat = time.ticks_ms() if hasattr(time, "ticks_ms") else int(time.time() * 1000)
    led_state = 0

    try:
        while True:
            # Update state machine
            controller.update()

            # Heartbeat LED toggle every 1000ms
            now = time.ticks_ms() if hasattr(time, "ticks_ms") else int(time.time() * 1000)
            diff = time.ticks_diff(now, last_heartbeat) if hasattr(time, "ticks_diff") else (now - last_heartbeat)
            if led is not None and diff >= 1000:
                led_state = 1 - led_state
                led.value(led_state)
                last_heartbeat = now

            # Non-blocking poll interval
            if hasattr(time, "sleep_ms"):
                time.sleep_ms(config.POLL_INTERVAL_MS)
            else:
                time.sleep(config.POLL_INTERVAL_MS / 1000.0)

    except KeyboardInterrupt:
        print("\nStopping controller...")
    finally:
        # Failsafe: Ensure outputs are explicitly shut off
        out_open.value(0)
        out_close.value(0)
        if led is not None:
            led.value(0)
        print("Outputs shut down safely. Argus terminated.")

if __name__ == "__main__":
    main()
