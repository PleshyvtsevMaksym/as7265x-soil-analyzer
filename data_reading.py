# data_reading.py
import sys
import select
from as7265x import create_default_driver
from measuring_types import SoilMeasurementSystem
import config

def print_results(system):
    print(f"\n{'Ch':<3} | {'nm':<4} | {'Dark':<10} | {'White':<10} | {'Sample':<10} | {'Reflectance'}")
    print("-" * 65)
    for i, ch in enumerate(system.channels):
        d = system.dark_ref[ch] if system.dark_ref else 0.0
        w = system.white_ref[ch] if system.white_ref else 0.0
        s = system.sample_data[ch] if system.sample_data else 0.0
        n = system.normalized_data[ch] if system.normalized_data else 0.0
        print(f"{ch:<3} | {system.wavelengths[i]:<4} | {d:<10.2f} | {w:<10.2f} | {s:<10.2f} | {n:.4f}")
    print("\n")

def run_data_reading(debug=False):
    print("Initializing sensor...")
    driver = create_default_driver(
        debug=debug, 
        i2c_bus=0, 
        scl_pin=config.I2C_SCL_PIN, 
        sda_pin=config.I2C_SDA_PIN, 
        freq=config.I2C_FREQ
    )
    system = SoilMeasurementSystem(driver, config.EXT_LED_PIN)
    
    print("System ready.")
    print("Available Commands: 'dark', 'white', 'sample', 'normalize', 'print'")

    # Set up non-blocking serial read loop
    poll_obj = select.poll()
    poll_obj.register(sys.stdin, select.POLLIN)

    while True:
        poll_res = poll_obj.poll(config.CMD_POLL_DELAY_MS)
        if poll_res:
            # Read and process the command
            cmd = sys.stdin.readline().strip().lower()
            
            if cmd == 'dark':
                print(">>> Taking DARK reference...")
                system.take_dark()
                print(">>> DONE.")
            elif cmd == 'white':
                print(">>> Taking WHITE reference...")
                system.take_white()
                print(">>> DONE.")
            elif cmd == 'sample':
                print(">>> Taking SAMPLE measurement...")
                system.take_sample()
                print(">>> DONE.")
            elif cmd == 'normalize':
                print(">>> Calculating normalized reflectance...")
                if system.normalize():
                    print(">>> DONE. Use 'print' to view.")
                else:
                    print(">>> ERROR: Missing data. Take dark, white, and sample first.")
            elif cmd == 'print':
                print_results(system)
            elif cmd != '':
                print(f"Unknown command: '{cmd}'. Use: dark, white, sample, normalize, print")