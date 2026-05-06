# measuring_types.py
import time
from machine import Pin

class SoilMeasurementSystem:
    def __init__(self, driver, led_pin):
        self.driver = driver
        # Initialize external LED on GPIO
        self.led = Pin(led_pin, Pin.OUT)
        self.led.value(0) # Ensure it starts OFF
        
        # Memory to store state
        self.dark_ref = None
        self.white_ref = None
        self.sample_data = None
        self.normalized_data = None
        
        # 18 spectral channels mapped to AS7265x
        self.channels = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'R', 'S', 'T', 'U', 'V', 'W']
        self.wavelengths = [410, 435, 460, 485, 510, 535, 560, 585, 610, 645, 680, 705, 730, 760, 810, 860, 900, 940]

    def take_dark(self):
        """Measurement 1: Dark Reference (LED OFF)"""
        self.led.value(0)
        time.sleep_ms(500) # Allow sensor/environment to settle
        self.dark_ref = self.driver.read_once()
        return self.dark_ref

    def take_white(self):
        """Measurement 2: White Reference (LED ON)"""
        self.led.value(1)
        time.sleep_ms(500) 
        self.white_ref = self.driver.read_once()
        self.led.value(0) # Turn off immediately after reading
        return self.white_ref

    def take_sample(self):
        """Measurement 3: Soil Sample (LED ON)"""
        self.led.value(1)
        time.sleep_ms(500)
        self.sample_data = self.driver.read_once()
        self.led.value(0)
        return self.sample_data

    def normalize(self):
        """Calculate Reflectance: R[i] = (S[i] - D[i]) / (W[i] - D[i])"""
        if not self.dark_ref or not self.white_ref or not self.sample_data:
            return False
            
        self.normalized_data = {}
        for ch in self.channels:
            s = self.sample_data[ch]
            d = self.dark_ref[ch]
            w = self.white_ref[ch]
            
            denom = w - d
            # Prevent division by zero if white target isn't reflecting more than dark
            if denom == 0:
                self.normalized_data[ch] = 0.0
            else:
                self.normalized_data[ch] = (s - d) / denom
                
        return True