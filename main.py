# main.py
import config
import time
from as7265x import AS7265X_Driver, SoilMeasurementSystem
from hs5645mg import MeasurementMovement
from database import MaterialDatabase

def run_job():
    print("\n--- Starting Measurement Cycle ---")
    
    # Initialize Hardware
    try:
        move = MeasurementMovement(config.SERVO_PIN)
        sensor = SoilMeasurementSystem(AS7265X_Driver())
        db = MaterialDatabase()
    except Exception as e:
        print(f"Hardware Error: {e}")
        return

    # STEP 1: Center
    print("\n[Step 1] Initial Centering...")
    move.return_to_center()

    # STEP 2: Move to Sample
    print("\n[Step 2] Moving to Sample Position (0°)...")
    move.move_to_soil()

    # STEP 3: Measure Dark
    print("\n[Step 3] Measuring Dark (LED OFF)...")
    sensor.take_dark()

    # STEP 4: Measure Sample
    print("\n[Step 4] Measuring Soil (LED ON)...")
    sensor.take_sample()

    # STEP 5: Move to White
    print("\n[Step 5] Moving to White Reference Position (180°)...")
    move.move_to_white()

    # STEP 6: Measure White
    print("\n[Step 6] Measuring White (LED ON)...")
    sensor.take_white()

    # STEP 7: Return to Center
    print("\n[Step 7] Returning to Safe Center Position (90°)...")
    move.return_to_center()
    move.shutdown()

    # STEP 8: Analyze Data
    print("\n[Step 8] Analyzing Data against Database...")
    if sensor.normalize():
        print("\n--- SPECTRAL REFLECTANCE DATA ---")
        print(f"{'CH':<3} | {'nm':<4} | {'Dark':<8} | {'White':<8} | {'Sample':<8} | {'Reflectance'}")
        print("-" * 62)
        for i, ch in enumerate(sensor.channels):
            wl = sensor.wavelengths[i]
            d = sensor.dark_ref[ch]
            w = sensor.white_ref[ch]
            s = sensor.sample_data[ch]
            r = sensor.normalized_data[ch]
            print(f"{ch:<3} | {wl:<4} | {d:<8.2f} | {w:<8.2f} | {s:<8.2f} | {r:.4f}")
            
        print("\n--- DATABASE MATCH RESULTS ---")
        if not db.data:
            print("No materials found in database.json.")
        else:
            matches = db.find_matches(sensor.normalized_data, top_n=5)
            for name, sim in matches:
                print(f"{name}: {sim:.2f}% Match")
    else:
        print("ERROR: Missing data. Could not calculate reflectance.")
        
    print("\nJob Complete.")

if __name__ == "__main__":
    run_job()