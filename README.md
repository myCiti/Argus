# Project Argus - Door Controller for Raspberry Pi Pico

MicroPython door controller firmware for Raspberry Pi Pico / RP2040.

## Hardware Pinout

All inputs are configured with internal pull-ups (Active LOW: 0V / GND = `0`, Idle = `1`).

### Inputs
| Function | GPIO Pin | Physical Pin (Pico) | Logic Level |
| :--- | :--- | :--- | :--- |
| **Sensor** | `GP29` | Pin 35 (or dedicated ADC3/GP29 pin on Pico Mini) | Active LOW (0V / GND) |
| **Open Button** | `GP28` | Pin 34 | Active LOW (0V / GND) |
| **Close Button** | `GP27` | Pin 32 | Active LOW (0V / GND) |

### Outputs
| Function | GPIO Pin | Physical Pin (Pico) | Active Level |
| :--- | :--- | :--- | :--- |
| **Open Output** | `GP7` | Pin 10 | Active HIGH (3.3V = ON) |
| **Close Output** | `GP8` | Pin 11 | Active HIGH (3.3V = ON) |
| **Heartbeat LED** | `GP25` / `"LED"` | Onboard LED | Blinks every 1s |

---

## Operating Logic & Features

1. **500ms Press Debounce / Trigger**:
   - Pressing and holding **Open** for at least 500ms triggers the Open output for 8 seconds.
   - Pressing and holding **Close** for at least 500ms triggers the Close output for 8 seconds.
   - Brief clicks/noise under 500ms are ignored.

2. **Safety Reversal (Anti-Pinch / Obstruction)**:
   - If the **Sensor** triggers (`GP29 == 1`) while closing, closing halts immediately and **Open** output activates for 200ms to back away from the obstruction.
   - Closing cannot be initiated while the sensor is blocked.

3. **Constant Pressure Closing**:
   - If the user keeps holding the **Close** button, the door continues to close as long as the button remains pressed (even beyond 8 seconds). Releasing it stops the door.

4. **Hardware Interlock**:
   - Open and Close outputs are mutually exclusive with break-before-make switching to prevent motor/relay shorts.

---

## How to Deploy to Pico

1. Connect your Raspberry Pi Pico via USB.
2. Using Thonny, `mpremote`, or VS Code Pico Extension:
   - Copy [`config.py`](file:///home/chavtha/Projects/Argus/config.py), [`controller.py`](file:///home/chavtha/Projects/Argus/controller.py), and [`main.py`](file:///home/chavtha/Projects/Argus/main.py) to the root of the Pico filesystem.
3. Reset or power-cycle the Pico. `main.py` will start automatically.
