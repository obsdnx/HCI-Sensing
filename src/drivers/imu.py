"""
LSM6DS3 IMU driver (I2C).
Accel: ±2g, Gyro: ±245°/s (defaults, change CTRL registers to adjust range).
I2C address: 0x6A (SDO=GND) or 0x6B (SDO=VCC).
"""

_DEFAULT_ADDR = 0x6A

# Registers
_WHO_AM_I  = 0x0F  # should return 0x69
_CTRL1_XL  = 0x10  # accel config
_CTRL2_G   = 0x11  # gyro config
_CTRL3_C   = 0x12  # general: set IF_INC for auto-increment reads
_OUTX_L_G  = 0x22  # gyro output, 6 bytes (XYZ, little-endian)
_OUTX_L_XL = 0x28  # accel output, 6 bytes (XYZ, little-endian)

# Sensitivity at default ranges
_ACCEL_SCALE = 1.0 / 16393.0   # ±2g  → 0.061 mg/LSB
_GYRO_SCALE  = 8.75 / 1000.0   # ±245°/s → 8.75 mdps/LSB


def _signed(val):
    return val - 65536 if val > 32767 else val


class IMU:
    def __init__(self, i2c, addr=_DEFAULT_ADDR):
        self._i2c = i2c
        self._addr = addr

    def init(self):
        who = self._read_byte(_WHO_AM_I)
        print(f"LSM6DS3 WHO_AM_I: {hex(who)}")  # expect 0x69

        # Enable auto-increment for multi-byte reads
        self._write(_CTRL3_C, 0x04)

        # Accel: 104 Hz ODR, ±2g (0x40)
        self._write(_CTRL1_XL, 0x40)

        # Gyro: 104 Hz ODR, ±245°/s (0x40)
        self._write(_CTRL2_G, 0x40)

    def read(self):
        raw_g  = self._i2c.readfrom_mem(self._addr, _OUTX_L_G,  6)
        raw_xl = self._i2c.readfrom_mem(self._addr, _OUTX_L_XL, 6)

        gx = _signed(raw_g[1]  << 8 | raw_g[0])  * _GYRO_SCALE
        gy = _signed(raw_g[3]  << 8 | raw_g[2])  * _GYRO_SCALE
        gz = _signed(raw_g[5]  << 8 | raw_g[4])  * _GYRO_SCALE

        ax = _signed(raw_xl[1] << 8 | raw_xl[0]) * _ACCEL_SCALE
        ay = _signed(raw_xl[3] << 8 | raw_xl[2]) * _ACCEL_SCALE
        az = _signed(raw_xl[5] << 8 | raw_xl[4]) * _ACCEL_SCALE

        return {"ax": ax, "ay": ay, "az": az,
                "gx": gx, "gy": gy, "gz": gz}

    def _write(self, reg, val):
        self._i2c.writeto_mem(self._addr, reg, bytes([val]))

    def _read_byte(self, reg):
        return self._i2c.readfrom_mem(self._addr, reg, 1)[0]
