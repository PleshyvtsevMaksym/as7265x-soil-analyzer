import gc
import time
from AS7265x_driver import create_default_driver


class BasicReading:
    def __init__(self, debug=True, use_bulb=False, delay_ms=2000):
        self.debug = debug
        self.use_bulb = use_bulb
        self.delay_ms = delay_ms
        self.driver = None

    def setup(self):
        if self.debug:
            print("Initializing BasicReading...")
        self.driver = create_default_driver(debug=self.debug)
        if self.debug:
            print("BasicReading ready")

    def run_once(self):
        if self.driver is None:
            self.setup()

        data = self.driver.read_once(with_bulb=self.use_bulb)
        formatted = self.driver.format_spectrum(data)

        print("------ SPECTRUM ------")
        print(formatted)
        print()

    def run_loop(self):
        if self.driver is None:
            self.setup()

        while True:
            try:
                self.run_once()
                time.sleep_ms(self.delay_ms)
            except Exception as e:
                print("Reading error:", e)
                gc.collect()
                print("Free memory:", gc.mem_free())
                time.sleep(1)


def run_basic_reading(debug=True, use_bulb=False, delay_ms=2000):
    app = BasicReading(
        debug=debug,
        use_bulb=use_bulb,
        delay_ms=delay_ms
    )
    app.run_loop()