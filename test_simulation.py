# test_simulation.py
# Automated unit tests and simulation for DoorController logic

import unittest
from controller import DoorController, DoorState
import config

class MockPin:
    def __init__(self, initial_value=0):
        self._val = initial_value

    def value(self, val=None):
        if val is not None:
            self._val = val
        return self._val

class SimulatedDoorController(DoorController):
    def __init__(self, pin_sensor, pin_btn_open, pin_btn_close, pin_out_open, pin_out_close):
        self.simulated_time_ms = 0
        super().__init__(pin_sensor, pin_btn_open, pin_btn_close, pin_out_open, pin_out_close)

    def _get_time_ms(self):
        return self.simulated_time_ms

    def _time_diff(self, t_now, t_start):
        return t_now - t_start

    def advance_time(self, ms, step_ms=10):
        """Simulates time passing in discrete steps while calling update()."""
        end_time = self.simulated_time_ms + ms
        while self.simulated_time_ms < end_time:
            self.update()
            self.simulated_time_ms += step_ms
        self.update()

class TestDoorController(unittest.TestCase):
    def setUp(self):
        # Pull-up inputs: default inactive state is 1 (3.3V)
        self.sensor = MockPin(1)
        self.btn_open = MockPin(1)
        self.btn_close = MockPin(1)
        # Outputs: default inactive state is 0 (LOW)
        self.out_open = MockPin(0)
        self.out_close = MockPin(0)

        self.door = SimulatedDoorController(
            self.sensor, self.btn_open, self.btn_close, self.out_open, self.out_close
        )

    def test_initial_state(self):
        self.assertEqual(self.door.state, DoorState.IDLE)
        self.assertEqual(self.out_open.value(), 0)
        self.assertEqual(self.out_close.value(), 0)

    def test_short_press_ignored(self):
        """A press shorter than 500ms should NOT trigger door movement."""
        self.btn_open.value(0)  # Pressed (0V)
        self.door.advance_time(400)
        self.btn_open.value(1)  # Released (3.3V)
        self.door.advance_time(100)

        self.assertEqual(self.door.state, DoorState.IDLE)
        self.assertEqual(self.out_open.value(), 0)

    def test_open_cycle(self):
        """Holding Open for 500ms triggers 8 seconds of Open output."""
        # Hold for 500ms (Active LOW = 0)
        self.btn_open.value(0)
        self.door.advance_time(500)
        self.btn_open.value(1)  # Released

        # Should now be OPENING
        self.assertEqual(self.door.state, DoorState.OPENING)
        self.assertEqual(self.out_open.value(), 1)
        self.assertEqual(self.out_close.value(), 0)

        # Advance 7500ms (total 8000ms after trigger)
        self.door.advance_time(7900)
        self.assertEqual(self.door.state, DoorState.OPENING)
        self.assertEqual(self.out_open.value(), 1)

        # Complete the 8s cycle
        self.door.advance_time(200)
        self.assertEqual(self.door.state, DoorState.IDLE)
        self.assertEqual(self.out_open.value(), 0)

    def test_close_cycle(self):
        """Holding Close for 500ms triggers 8 seconds of Close output."""
        self.btn_close.value(0)  # Pressed (0V)
        self.door.advance_time(500)
        self.btn_close.value(1)  # Released

        self.assertEqual(self.door.state, DoorState.CLOSING)
        self.assertEqual(self.out_close.value(), 1)
        self.assertEqual(self.out_open.value(), 0)

        # After 8s, should return to IDLE
        self.door.advance_time(8100)
        self.assertEqual(self.door.state, DoorState.IDLE)
        self.assertEqual(self.out_close.value(), 0)

    def test_safety_sensor_reversal(self):
        """Tripping sensor while closing must immediately stop Close and reverse Open for 200ms."""
        # Start closing
        self.btn_close.value(0)
        self.door.advance_time(500)
        self.btn_close.value(1)
        self.assertEqual(self.door.state, DoorState.CLOSING)

        # Advance 2 seconds into closing
        self.door.advance_time(2000)

        # Trigger obstacle sensor (Active LOW = 0)
        self.sensor.value(0)
        self.door.advance_time(10)  # Next loop tick

        # Must immediately cut Close and turn on Open for reversal
        self.assertEqual(self.door.state, DoorState.REVERSING)
        self.assertEqual(self.out_close.value(), 0)
        self.assertEqual(self.out_open.value(), 1)

        # Clear sensor (Inactive = 1)
        self.sensor.value(1)

        # During the 200ms reverse window
        self.door.advance_time(150)
        self.assertEqual(self.door.state, DoorState.REVERSING)
        self.assertEqual(self.out_open.value(), 1)

        # After 200ms reversal completes
        self.door.advance_time(100)
        self.assertEqual(self.door.state, DoorState.IDLE)
        self.assertEqual(self.out_open.value(), 0)
        self.assertEqual(self.out_close.value(), 0)

    def test_constant_pressure_closing(self):
        """Holding Close continuously keeps closing beyond standard 8 seconds until released."""
        self.btn_close.value(0)  # Pressed (0V)
        self.door.advance_time(500)  # Triggers CLOSING

        # Keep holding for 12 seconds total
        self.door.advance_time(11500)
        self.assertEqual(self.door.state, DoorState.CLOSING)
        self.assertEqual(self.out_close.value(), 1)

        # Release button (Released = 1)
        self.btn_close.value(1)
        self.door.advance_time(50)

        # Should now stop and enter IDLE
        self.assertEqual(self.door.state, DoorState.IDLE)
        self.assertEqual(self.out_close.value(), 0)

    def test_sensor_prevents_closing_from_idle(self):
        """If sensor is blocked (0V) before starting close, door should not close."""
        self.sensor.value(0)  # Blocked
        self.btn_close.value(0)  # Pressed
        self.door.advance_time(600)

        self.assertEqual(self.door.state, DoorState.IDLE)
        self.assertEqual(self.out_close.value(), 0)

    def test_one_second_sensor_pulse_during_closing(self):
        """A 1-second sensor pulse reverses for 200ms without freezing subsequent Open commands."""
        # 1. Start closing
        self.btn_close.value(0)
        self.door.advance_time(500)
        self.btn_close.value(1)
        self.assertEqual(self.door.state, DoorState.CLOSING)

        # 2. Sensor emits 1000ms pulse (at t = 1000ms into closing)
        self.door.advance_time(1000)
        self.sensor.value(0)  # Pulse starts
        self.door.advance_time(10)
        self.assertEqual(self.door.state, DoorState.REVERSING)
        self.assertEqual(self.out_open.value(), 1)

        # 3. 200ms reverse completes -> enters IDLE, while sensor is STILL in its 1000ms pulse (790ms remaining)
        self.door.advance_time(200)
        self.assertEqual(self.door.state, DoorState.IDLE)
        self.assertEqual(self.out_open.value(), 0)

        # 4. User presses OPEN while sensor pulse is STILL active (500ms press)
        self.btn_open.value(0)
        self.door.advance_time(500)
        self.btn_open.value(1)

        # Door MUST open immediately without freezing or waiting for sensor to clear
        self.assertEqual(self.door.state, DoorState.OPENING)
        self.assertEqual(self.out_open.value(), 1)

        # Clear sensor pulse
        self.sensor.value(1)

    def test_holding_close_through_transient_sensor_pulse(self):
        """If user holds Close while sensor is active for 1s, closing starts seamlessly once sensor clears."""
        # Sensor is currently emitting 1s pulse (0V)
        self.sensor.value(0)

        # User starts holding Close button
        self.btn_close.value(0)
        self.door.advance_time(600)

        # Door must not close yet
        self.assertEqual(self.door.state, DoorState.IDLE)
        self.assertEqual(self.out_close.value(), 0)

        # Sensor 1s pulse ends (sensor goes back to 1 / clear)
        self.sensor.value(1)
        self.door.advance_time(20)

        # Door MUST immediately start CLOSING without requiring user to release and re-press Close!
        self.assertEqual(self.door.state, DoorState.CLOSING)
        self.assertEqual(self.out_close.value(), 1)

if __name__ == "__main__":
    unittest.main()
