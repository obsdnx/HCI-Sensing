"""
Generic IMU driver skeleton.
Swap the register map for your specific chip (MPU-6050, BNO055, LSM6DS3, ICM-42688…).

Default: MPU-6050 / MPU-6500 register map (0x68 / 0x69).
"""

_DEFAULT_ADDR = 0x68

# MPU-6050 registers
_REG_PWR_MGMT_1 = 0x6B
_REG_ACCEL_XOUT_H = 0x3B
_REG_GYRO_XOUT_H  = 0x43
_REG_WHO_AM_I     = 0x75

_ACCEL_SCALE = 16384.0  # ±2g range → LSB/g
_GYRO_SCALE  = 131.0    # ±250°/s range → LSB/(°/s)


def _signed(val):
    return val - 65536 if val > 32767 else val


class IMU:
    def __init__(self, i2c, addr=_DEFAULT_ADDR):
        self._i2c = i2c
        self._addr = addr

    def init(self):
        # Wake the chip (clears sleep bit)
        self._write(_REG_PWR_MGMT_1, 0x00)
        who = self._read_byte(_REG_WHO_AM_I)
        print(f"IMU WHO_AM_I: {hex(who)}")

    def read(self):
        raw = self._i2c.readfrom_mem(self._addr, _REG_ACCEL_XOUT_H, 14)

        ax = _signed(raw[0] << 8 | raw[1]) / _ACCEL_SCALE
        ay = _signed(raw[2] << 8 | raw[3]) / _ACCEL_SCALE
        az = _signed(raw[4] << 8 | raw[5]) / _ACCEL_SCALE
        # raw[6:7] = temperature (skip for now)
        gx = _signed(raw[8]  << 8 | raw[9])  / _GYRO_SCALE
        gy = _signed(raw[10] << 8 | raw[11]) / _GYRO_SCALE
        gz = _signed(raw[12] << 8 | raw[13]) / _GYRO_SCALE

        return {"ax": ax, "ay": ay, "az": az,
                "gx": gx, "gy": gy, "gz": gz}

    def _write(self, reg, val):
        self._i2c.writeto_mem(self._addr, reg, bytes([val]))

    def _read_byte(self, reg):
        return self._i2c.readfrom_mem(self._addr, reg, 1)[0]
