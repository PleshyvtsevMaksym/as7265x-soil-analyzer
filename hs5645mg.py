# hs5645mg.py
import time
import config
from machine import Pin, PWM

class HS5645MG:
    def __init__(self, pin_num, freq=50, min_us=600, max_us=2400, max_angle=180):
        """
        Universal hardware driver for standard and continuous rotation RC servos.
        """
        self.pwm = PWM(Pin(pin_num), freq=freq)
        self.min_ns = min_us * 1000
        self.max_ns = max_us * 1000
        self.max_angle = max_angle
        
        # Keep track of where we are
        self.current_us = 1500 
        self.set_us(self.current_us) # Start in the middle

    def set_us(self, us):
        """Core Capability: Send an exact raw microsecond pulse width."""
        # Constrain to safe limits
        us = max(self.min_ns // 1000, min(us, self.max_ns // 1000))
        self.current_us = us
        self.pwm.duty_ns(us * 1000)

    def set_angle(self, angle):
        """Capability: Move to a specific angle (Standard 180-degree servos)."""
        angle = max(0, min(angle, self.max_angle))
        pulse_ns = self.min_ns + int((self.max_ns - self.min_ns) * (angle / self.max_angle))
        self.set_us(pulse_ns // 1000)

    def set_speed(self, speed):
        """Capability: Set rotation speed (For modified 360-degree continuous servos).
           speed: -1.0 (reverse) to 1.0 (forward). 0.0 is stop."""
        speed = max(-1.0, min(speed, 1.0))
        center_ns = (self.max_ns + self.min_ns) // 2
        range_ns = (self.max_ns - self.min_ns) // 2
        
        pulse_ns = center_ns + int(speed * range_ns)
        self.set_us(pulse_ns // 1000)

    def get_state(self):
        """Capability: Read the currently commanded pulse width in microseconds."""
        return self.current_us

    def release(self):
        """Capability: Cut the PWM signal so the motor loses torque/goes limp."""
        self.pwm.deinit()


# ==========================================
# Merged from measuring_movement.py
# ==========================================
class MeasurementMovement:
    def __init__(self, pin_num=config.SERVO_PIN):
        # Instantiate the "Engine" so we have access to all its capabilities
        self.motor = HS5645MG(pin_num=pin_num)

    def move_to_soil(self):
        """Rotates the arm to the soil sample position."""
        print("Moving to SOIL target...")
        target_angle = config.SERVO_CENTER_ANGLE - config.SERVO_SWING_DEGREES
        self.motor.set_angle(target_angle)
        time.sleep(config.MECHANICAL_SETTLE_TIME)

    def move_to_light(self):
        """Rotates the arm to the white light reference position."""
        print("Moving to WHITE target...")
        self.motor.set_angle(config.SERVO_CENTER_ANGLE)
        time.sleep(config.MECHANICAL_SETTLE_TIME)

    def print_diagnostics(self):
        """Checks the current PWM pulse width being sent to the servo."""
        current_us = self.motor.get_state()
        print(f"[Diagnostics] Servo is currently receiving {current_us} microseconds.")

    def shutdown(self):
        """Releases the servo to save power when not actively moving."""
        print("Releasing servo torque...")
        self.motor.release()