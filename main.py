# main.py
import config
from as7265x import AS7265X_Driver, SoilMeasurementSystem
from hs5645mg import MeasurementMovement

def run_job():
    print("Starting Job...")
    sensor = SoilMeasurementSystem(AS7265X_Driver())
    
    # FIX: Pass the pin number to the movement controller here
    move = MeasurementMovement(config.SERVO_PIN)

    # 1. Rotate 60 degrees left to Soil target
    move.move_to_soil()
    
    # 2. Take Dark and Soil measurements
    print("Measuring Dark...")
    sensor.take_dark()
    print("Measuring Soil...")
    sensor.take_sample()

    # 3. Rotate 60 degrees right to Light (White) target
    move.move_to_light()
    
    # 4. Take Light measurement
    print("Measuring White...")
    sensor.take_white()

    # 5. Normalize and print all data
    if sensor.normalize():
        print("\n--- FINAL RESULTS ---")
        print(f"{'CH':<3} | {'nm':<4} | {'Dark':<10} | {'White':<10} | {'Sample':<10} | {'Reflectance'}")
        print("-" * 65)
        
        for i, ch in enumerate(sensor.channels):
            wl = sensor.wavelengths[i]
            d = sensor.dark_ref[ch]
            w = sensor.white_ref[ch]
            s = sensor.sample_data[ch]
            r = sensor.normalized_data[ch]
            print(f"{ch:<3} | {wl:<4} | {d:<10.2f} | {w:<10.2f} | {s:<10.2f} | {r:.4f}")
    else:
        print("ERROR: Missing data. Could not calculate reflectance.")
    
    move.shutdown()
    print("\nJob Complete.")

if __name__ == "__main__":
    run_job()