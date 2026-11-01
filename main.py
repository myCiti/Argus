# main.py
# Main entry point for Project Argus on Waveshare RP2040-Zero

import machine
import time
import config
from controller import DoorController

def init_hardware():
    """Initializes and returns all GPIO pins with proper pull-ups and initial states."""
    print("------------------------------------------")
    print("Initializing Project Argus Door Controller")
    print("------------------------------------------")

    sensor = machine.Pin(config.PIN_SENSOR, machine.Pin.IN, machine.Pin.PULL_UP)
    btn_open = machine.Pin(config.PIN_BTN_OPEN, machine.Pin.IN, machine.Pin.PULL_UP)
    btn_close = machine.Pin(config.PIN_BTN_CLOSE, machine.Pin.IN, machine.Pin.PULL_UP)

    out_open = machine.Pin(config.PIN_OUT_OPEN, machine.Pin.OUT, value=0)
    out_close = machine.Pin(config.PIN_OUT_CLOSE, machine.Pin.OUT, value=0)
    
    led_ext_pin_id = config.PIN_LED_EXT

    print(f"Inputs  : Overcurrent Sensor=GP{config.PIN_SENSOR}, Open=GP{config.PIN_BTN_OPEN}, Close=GP{config.PIN_BTN_CLOSE}")
    print(f"Outputs : Open=GP{config.PIN_OUT_OPEN}, Close=GP{config.PIN_OUT_CLOSE}")
    print("Ready. Waiting for input...")
    
    return sensor, btn_open, btn_close, out_open, out_close, led_ext_pin_id

def main():
    sensor, btn_open, btn_close, out_open, out_close, led_ext_pin_id = init_hardware()
    
    controller = DoorController(
        sensor, btn_open, btn_close, out_open, out_close,
        pin_led_rgb=config.PIN_LED_RGB,
        pin_led_ext=led_ext_pin_id)

    try:
        while True:
            controller.update()
            time.sleep_ms(config.POLL_INTERVAL_MS)

    except KeyboardInterrupt:
        print("\nStopping controller...")
    finally:
        out_open.value(0)
        out_close.value(0)
        print("Outputs shut down safely. Argus terminated.")

if __name__ == "__main__":
    main()
