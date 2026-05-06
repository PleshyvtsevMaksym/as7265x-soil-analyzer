from machine import Pin, I2C
import time
import struct


class AS7265X:
    ADDRESS = 0x49

    STATUS_REG = 0x00
    WRITE_REG = 0x01
    READ_REG = 0x02

    TX_VALID = 0x02
    RX_VALID = 0x01

    HW_VERSION_HIGH = 0x00
    HW_VERSION_LOW = 0x01

    FW_VERSION_HIGH = 0x02
    FW_VERSION_LOW = 0x03

    CONFIG = 0x04
    INTEGRATION_TIME = 0x05
    DEVICE_TEMP = 0x06
    LED_CONFIG = 0x07

    R_G_A = 0x08
    S_H_B = 0x0A
    T_I_C = 0x0C
    U_J_D = 0x0E
    V_K_E = 0x10
    W_L_F = 0x12

    R_G_A_CAL = 0x14
    S_H_B_CAL = 0x18
    T_I_C_CAL = 0x1C
    U_J_D_CAL = 0x20
    V_K_E_CAL = 0x24
    W_L_F_CAL = 0x28

    DEV_SELECT_CONTROL = 0x4F

    COEF_DATA_0 = 0x50
    COEF_DATA_1 = 0x51
    COEF_DATA_2 = 0x52
    COEF_DATA_3 = 0x53
    COEF_DATA_READ = 0x54
    COEF_DATA_WRITE = 0x55

    POLLING_DELAY_MS = 5

    DEV_NIR = 0x00
    DEV_VISIBLE = 0x01
    DEV_UV = 0x02

    LED_WHITE = 0x00
    LED_IR = 0x01
    LED_UV = 0x02

    LED_CURRENT_LIMIT_12_5MA = 0b00
    LED_CURRENT_LIMIT_25MA = 0b01
    LED_CURRENT_LIMIT_50MA = 0b10
    LED_CURRENT_LIMIT_100MA = 0b11

    INDICATOR_CURRENT_LIMIT_1MA = 0b00
    INDICATOR_CURRENT_LIMIT_2MA = 0b01
    INDICATOR_CURRENT_LIMIT_4MA = 0b10
    INDICATOR_CURRENT_LIMIT_8MA = 0b11

    GAIN_1X = 0b00
    GAIN_3_7X = 0b01
    GAIN_16X = 0b10
    GAIN_64X = 0b11

    MEASUREMENT_MODE_4CHAN = 0b00
    MEASUREMENT_MODE_4CHAN_2 = 0b01
    MEASUREMENT_MODE_6CHAN_CONTINUOUS = 0b10
    MEASUREMENT_MODE_6CHAN_ONE_SHOT = 0b11

    def __init__(self, i2c, address=ADDRESS, debug=False):
        self.i2c = i2c
        self.address = address
        self.debug = debug
        self.max_wait_time_ms = 1071

    def _sleep_ms(self, ms):
        time.sleep_ms(ms)

    def _ticks_ms(self):
        return time.ticks_ms()

    def _ticks_diff(self, a, b):
        return time.ticks_diff(a, b)

    def read_register(self, addr):
        try:
            self.i2c.writeto(self.address, bytes([addr]))
            data = self.i2c.readfrom(self.address, 1)
            if len(data) == 1:
                return data[0]
            return 0
        except OSError:
            return 0

    def write_register(self, addr, val):
        try:
            self.i2c.writeto(self.address, bytes([addr, val & 0xFF]))
            return True
        except OSError:
            return False

    def virtual_read_register(self, virtual_addr):
        status = self.read_register(self.STATUS_REG)

        if (status & self.RX_VALID) != 0:
            _ = self.read_register(self.READ_REG)

        start_time = self._ticks_ms()
        while True:
            if self._ticks_diff(self._ticks_ms(), start_time) > self.max_wait_time_ms:
                return 0

            status = self.read_register(self.STATUS_REG)
            if (status & self.TX_VALID) == 0:
                break

            self._sleep_ms(self.POLLING_DELAY_MS)

        self.write_register(self.WRITE_REG, virtual_addr & 0x7F)

        start_time = self._ticks_ms()
        while True:
            if self._ticks_diff(self._ticks_ms(), start_time) > self.max_wait_time_ms:
                return 0

            status = self.read_register(self.STATUS_REG)
            if (status & self.RX_VALID) != 0:
                break

            self._sleep_ms(self.POLLING_DELAY_MS)

        return self.read_register(self.READ_REG)

    def virtual_write_register(self, virtual_addr, data_to_write):
        start_time = self._ticks_ms()

        while True:
            if self._ticks_diff(self._ticks_ms(), start_time) > self.max_wait_time_ms:
                return

            status = self.read_register(self.STATUS_REG)
            if (status & self.TX_VALID) == 0:
                break

            self._sleep_ms(self.POLLING_DELAY_MS)

        self.write_register(self.WRITE_REG, (virtual_addr | 0x80) & 0xFF)

        start_time = self._ticks_ms()
        while True:
            if self._ticks_diff(self._ticks_ms(), start_time) > self.max_wait_time_ms:
                return

            status = self.read_register(self.STATUS_REG)
            if (status & self.TX_VALID) == 0:
                break

            self._sleep_ms(self.POLLING_DELAY_MS)

        self.write_register(self.WRITE_REG, data_to_write & 0xFF)

    def is_connected(self):
        for _ in range(100):
            try:
                self.i2c.writeto(self.address, b"")
                return True
            except OSError:
                self._sleep_ms(10)
        return False

    def begin(self):
        if not self.is_connected():
            raise OSError("AS7265X not detected on I2C")

        time.sleep_ms(200)

        value = self.virtual_read_register(self.DEV_SELECT_CONTROL)
        if (value & 0b00110000) == 0:
            raise OSError("AS7265X slave devices not detected")

        self.set_bulb_current(self.LED_CURRENT_LIMIT_12_5MA, self.LED_WHITE)
        self.set_bulb_current(self.LED_CURRENT_LIMIT_12_5MA, self.LED_IR)
        self.set_bulb_current(self.LED_CURRENT_LIMIT_12_5MA, self.LED_UV)

        self.disable_bulb(self.LED_WHITE)
        self.disable_bulb(self.LED_IR)
        self.disable_bulb(self.LED_UV)

        self.set_indicator_current(self.INDICATOR_CURRENT_LIMIT_8MA)
        self.enable_indicator()

        self.set_integration_cycles(100)
        self.set_gain(self.GAIN_1X)
        self.set_measurement_mode(self.MEASUREMENT_MODE_6CHAN_CONTINUOUS)
        self.disable_interrupt()

        time.sleep_ms(300)
        return True

    def get_device_type(self):
        return self.virtual_read_register(self.HW_VERSION_HIGH)

    def get_hardware_version(self):
        return self.virtual_read_register(self.HW_VERSION_LOW)

    def get_major_firmware_version(self):
        self.virtual_write_register(self.FW_VERSION_HIGH, 0x01)
        self.virtual_write_register(self.FW_VERSION_LOW, 0x01)
        return self.virtual_read_register(self.FW_VERSION_LOW)

    def get_patch_firmware_version(self):
        self.virtual_write_register(self.FW_VERSION_HIGH, 0x02)
        self.virtual_write_register(self.FW_VERSION_LOW, 0x02)
        return self.virtual_read_register(self.FW_VERSION_LOW)

    def get_build_firmware_version(self):
        self.virtual_write_register(self.FW_VERSION_HIGH, 0x03)
        self.virtual_write_register(self.FW_VERSION_LOW, 0x03)
        return self.virtual_read_register(self.FW_VERSION_LOW)

    def take_measurements(self):
        self.set_measurement_mode(self.MEASUREMENT_MODE_6CHAN_CONTINUOUS)
        time.sleep_ms(250)

        start_time = self._ticks_ms()
        timeout_ms = max(self.max_wait_time_ms, 1500)

        while self.data_available() is False:
            if self._ticks_diff(self._ticks_ms(), start_time) > timeout_ms:
                raise OSError("AS7265X measurement timeout")
            self._sleep_ms(self.POLLING_DELAY_MS)

    def take_measurements_with_bulb(self):
        self.enable_bulb(self.LED_WHITE)
        self.enable_bulb(self.LED_IR)
        self.enable_bulb(self.LED_UV)
        time.sleep_ms(200)

        try:
            self.take_measurements()
        finally:
            self.disable_bulb(self.LED_WHITE)
            self.disable_bulb(self.LED_IR)
            self.disable_bulb(self.LED_UV)

    def select_device(self, device):
        self.virtual_write_register(self.DEV_SELECT_CONTROL, device & 0x03)

    def get_channel(self, channel_register, device):
        self.select_device(device)
        color_data = self.virtual_read_register(channel_register) << 8
        color_data |= self.virtual_read_register(channel_register + 1)
        return color_data

    def get_calibrated_value(self, cal_address, device):
        self.select_device(device)

        b0 = self.virtual_read_register(cal_address + 0)
        b1 = self.virtual_read_register(cal_address + 1)
        b2 = self.virtual_read_register(cal_address + 2)
        b3 = self.virtual_read_register(cal_address + 3)

        return struct.unpack(">f", bytes([b0, b1, b2, b3]))[0]

    def get_A(self):
        return self.get_channel(self.R_G_A, self.DEV_UV)

    def get_B(self):
        return self.get_channel(self.S_H_B, self.DEV_UV)

    def get_C(self):
        return self.get_channel(self.T_I_C, self.DEV_UV)

    def get_D(self):
        return self.get_channel(self.U_J_D, self.DEV_UV)

    def get_E(self):
        return self.get_channel(self.V_K_E, self.DEV_UV)

    def get_F(self):
        return self.get_channel(self.W_L_F, self.DEV_UV)

    def get_G(self):
        return self.get_channel(self.R_G_A, self.DEV_VISIBLE)

    def get_H(self):
        return self.get_channel(self.S_H_B, self.DEV_VISIBLE)

    def get_I(self):
        return self.get_channel(self.T_I_C, self.DEV_VISIBLE)

    def get_J(self):
        return self.get_channel(self.U_J_D, self.DEV_VISIBLE)

    def get_K(self):
        return self.get_channel(self.V_K_E, self.DEV_VISIBLE)

    def get_L(self):
        return self.get_channel(self.W_L_F, self.DEV_VISIBLE)

    def get_R(self):
        return self.get_channel(self.R_G_A, self.DEV_NIR)

    def get_S(self):
        return self.get_channel(self.S_H_B, self.DEV_NIR)

    def get_T(self):
        return self.get_channel(self.T_I_C, self.DEV_NIR)

    def get_U(self):
        return self.get_channel(self.U_J_D, self.DEV_NIR)

    def get_V(self):
        return self.get_channel(self.V_K_E, self.DEV_NIR)

    def get_W(self):
        return self.get_channel(self.W_L_F, self.DEV_NIR)

    def get_calibrated_A(self):
        return self.get_calibrated_value(self.R_G_A_CAL, self.DEV_UV)

    def get_calibrated_B(self):
        return self.get_calibrated_value(self.S_H_B_CAL, self.DEV_UV)

    def get_calibrated_C(self):
        return self.get_calibrated_value(self.T_I_C_CAL, self.DEV_UV)

    def get_calibrated_D(self):
        return self.get_calibrated_value(self.U_J_D_CAL, self.DEV_UV)

    def get_calibrated_E(self):
        return self.get_calibrated_value(self.V_K_E_CAL, self.DEV_UV)

    def get_calibrated_F(self):
        return self.get_calibrated_value(self.W_L_F_CAL, self.DEV_UV)

    def get_calibrated_G(self):
        return self.get_calibrated_value(self.R_G_A_CAL, self.DEV_VISIBLE)

    def get_calibrated_H(self):
        return self.get_calibrated_value(self.S_H_B_CAL, self.DEV_VISIBLE)

    def get_calibrated_I(self):
        return self.get_calibrated_value(self.T_I_C_CAL, self.DEV_VISIBLE)

    def get_calibrated_J(self):
        return self.get_calibrated_value(self.U_J_D_CAL, self.DEV_VISIBLE)

    def get_calibrated_K(self):
        return self.get_calibrated_value(self.V_K_E_CAL, self.DEV_VISIBLE)

    def get_calibrated_L(self):
        return self.get_calibrated_value(self.W_L_F_CAL, self.DEV_VISIBLE)

    def get_calibrated_R(self):
        return self.get_calibrated_value(self.R_G_A_CAL, self.DEV_NIR)

    def get_calibrated_S(self):
        return self.get_calibrated_value(self.S_H_B_CAL, self.DEV_NIR)

    def get_calibrated_T(self):
        return self.get_calibrated_value(self.T_I_C_CAL, self.DEV_NIR)

    def get_calibrated_U(self):
        return self.get_calibrated_value(self.U_J_D_CAL, self.DEV_NIR)

    def get_calibrated_V(self):
        return self.get_calibrated_value(self.V_K_E_CAL, self.DEV_NIR)

    def get_calibrated_W(self):
        return self.get_calibrated_value(self.W_L_F_CAL, self.DEV_NIR)

    def set_measurement_mode(self, mode):
        if mode > 0b11:
            mode = 0b11

        value = self.virtual_read_register(self.CONFIG)
        value &= 0b11110011
        value |= (mode << 2)
        self.virtual_write_register(self.CONFIG, value)

    def set_gain(self, gain):
        if gain > 0b11:
            gain = 0b11

        value = self.virtual_read_register(self.CONFIG)
        value &= 0b11001111
        value |= (gain << 4)
        self.virtual_write_register(self.CONFIG, value)

    def set_integration_cycles(self, cycle_value):
        cycle_value &= 0xFF
        self.max_wait_time_ms = int(cycle_value * 2.8 * 1.5) + 1
        self.virtual_write_register(self.INTEGRATION_TIME, cycle_value)

    def enable_interrupt(self):
        value = self.virtual_read_register(self.CONFIG)
        value |= (1 << 6)
        self.virtual_write_register(self.CONFIG, value)

    def disable_interrupt(self):
        value = self.virtual_read_register(self.CONFIG)
        value &= ~(1 << 6)
        self.virtual_write_register(self.CONFIG, value)

    def data_available(self):
        value = self.virtual_read_register(self.CONFIG)
        return (value & (1 << 1)) != 0

    def enable_bulb(self, device):
        self.select_device(device)
        value = self.virtual_read_register(self.LED_CONFIG)
        value |= (1 << 3)
        self.virtual_write_register(self.LED_CONFIG, value)

    def disable_bulb(self, device):
        self.select_device(device)
        value = self.virtual_read_register(self.LED_CONFIG)
        value &= ~(1 << 3)
        self.virtual_write_register(self.LED_CONFIG, value)

    def set_bulb_current(self, current, device):
        self.select_device(device)

        if current > 0b11:
            current = 0b11

        value = self.virtual_read_register(self.LED_CONFIG)
        value &= 0b11001111
        value |= (current << 4)
        self.virtual_write_register(self.LED_CONFIG, value)

    def enable_indicator(self):
        self.select_device(self.DEV_NIR)
        value = self.virtual_read_register(self.LED_CONFIG)
        value |= (1 << 0)
        self.virtual_write_register(self.LED_CONFIG, value)

    def disable_indicator(self):
        self.select_device(self.DEV_NIR)
        value = self.virtual_read_register(self.LED_CONFIG)
        value &= ~(1 << 0)
        self.virtual_write_register(self.LED_CONFIG, value)

    def set_indicator_current(self, current):
        self.select_device(self.DEV_NIR)

        if current > 0b11:
            current = 0b11

        value = self.virtual_read_register(self.LED_CONFIG)
        value &= 0b11111001
        value |= (current << 1)
        self.virtual_write_register(self.LED_CONFIG, value)

    def get_temperature(self, device_number=0):
        self.select_device(device_number)
        return self.virtual_read_register(self.DEVICE_TEMP)

    def get_temperature_average(self):
        average = 0.0
        for x in range(3):
            average += self.get_temperature(x)
        return average / 3.0

    def soft_reset(self):
        value = self.virtual_read_register(self.CONFIG)
        value |= (1 << 7)
        self.virtual_write_register(self.CONFIG, value)
        self._sleep_ms(1000)

    def read_raw_channels(self):
        return {
            "A": self.get_A(),
            "B": self.get_B(),
            "C": self.get_C(),
            "D": self.get_D(),
            "E": self.get_E(),
            "F": self.get_F(),
            "G": self.get_G(),
            "H": self.get_H(),
            "I": self.get_I(),
            "J": self.get_J(),
            "K": self.get_K(),
            "L": self.get_L(),
            "R": self.get_R(),
            "S": self.get_S(),
            "T": self.get_T(),
            "U": self.get_U(),
            "V": self.get_V(),
            "W": self.get_W(),
        }

    def read_calibrated_channels(self):
        return {
            "A": self.get_calibrated_A(),
            "B": self.get_calibrated_B(),
            "C": self.get_calibrated_C(),
            "D": self.get_calibrated_D(),
            "E": self.get_calibrated_E(),
            "F": self.get_calibrated_F(),
            "G": self.get_calibrated_G(),
            "H": self.get_calibrated_H(),
            "I": self.get_calibrated_I(),
            "J": self.get_calibrated_J(),
            "K": self.get_calibrated_K(),
            "L": self.get_calibrated_L(),
            "R": self.get_calibrated_R(),
            "S": self.get_calibrated_S(),
            "T": self.get_calibrated_T(),
            "U": self.get_calibrated_U(),
            "V": self.get_calibrated_V(),
            "W": self.get_calibrated_W(),
        }

    def info(self):
        return {
            "device_type": self.get_device_type(),
            "hardware_version": self.get_hardware_version(),
            "firmware_major": self.get_major_firmware_version(),
            "firmware_patch": self.get_patch_firmware_version(),
            "firmware_build": self.get_build_firmware_version(),
            "temperature_average": self.get_temperature_average(),
        }


class AS7265X_Driver:
    def __init__(self, i2c_bus=0, scl_pin=22, sda_pin=21, freq=100000, debug=False):
        self.i2c_bus = i2c_bus
        self.scl_pin = scl_pin
        self.sda_pin = sda_pin
        self.freq = freq
        self.debug = debug
        self.i2c = None
        self.sensor = None

    def init_i2c(self):
        self.i2c = I2C(
            self.i2c_bus,
            scl=Pin(self.scl_pin),
            sda=Pin(self.sda_pin),
            freq=self.freq
        )
        devices = self.i2c.scan()
        if self.debug:
            print("I2C scan:", devices)
        if AS7265X.ADDRESS not in devices:
            raise OSError("AS7265X not found on I2C")
        return self.i2c

    def init_sensor(self):
        if self.i2c is None:
            self.init_i2c()
        self.sensor = AS7265X(self.i2c, debug=self.debug)
        self.sensor.begin()
        return self.sensor

    def init(self):
        self.init_i2c()
        self.init_sensor()
        return self.sensor

    def get_sensor(self):
        if self.sensor is None:
            self.init()
        return self.sensor

    def read_once(self, with_bulb=False):
        sensor = self.get_sensor()

        try:
            if with_bulb:
                sensor.take_measurements_with_bulb()
            else:
                sensor.take_measurements()

            return sensor.read_calibrated_channels()

        except Exception:
            if self.debug:
                print("Read failed, trying soft reset...")

            sensor.soft_reset()
            time.sleep_ms(1000)
            sensor.begin()

            if with_bulb:
                sensor.take_measurements_with_bulb()
            else:
                sensor.take_measurements()

            return sensor.read_calibrated_channels()

    def read_raw_once(self, with_bulb=False):
        sensor = self.get_sensor()

        if with_bulb:
            sensor.take_measurements_with_bulb()
        else:
            sensor.take_measurements()

        return sensor.read_raw_channels()

    def format_spectrum(self, data):
        return (
            "UV:\n"
            "A: {:.2f}  B: {:.2f}  C: {:.2f}  D: {:.2f}  E: {:.2f}  F: {:.2f}\n"
            "VISIBLE:\n"
            "G: {:.2f}  H: {:.2f}  I: {:.2f}  J: {:.2f}  K: {:.2f}  L: {:.2f}\n"
            "NIR:\n"
            "R: {:.2f}  S: {:.2f}  T: {:.2f}  U: {:.2f}  V: {:.2f}  W: {:.2f}"
        ).format(
            data["A"], data["B"], data["C"], data["D"], data["E"], data["F"],
            data["G"], data["H"], data["I"], data["J"], data["K"], data["L"],
            data["R"], data["S"], data["T"], data["U"], data["V"], data["W"]
        )


def create_default_driver(debug=False, i2c_bus=0, scl_pin=22, sda_pin=21, freq=100000):
    driver = AS7265X_Driver(
        i2c_bus=i2c_bus,
        scl_pin=scl_pin,
        sda_pin=sda_pin,
        freq=freq,
        debug=debug
    )
    driver.init()
    return driver