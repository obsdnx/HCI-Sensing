"""
HCI-Sensing — Raspberry Pi Pico entry point
Reads IMU data over I2C and streams it via USB serial.
"""
import time
from machine import I2C, Pin
from drivers.imu import IMU
from utils.serial_out import SerialOut

# I2C pins — adjust if your wiring differs
I2C_BUS = 0
SDA_PIN = 4
SCL_PIN = 5
SAMPLE_RATE_HZ = 100

def main():
    i2c = I2C(I2C_BUS, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=400_000)

    # Scan so you can confirm the IMU address on first boot
    devices = i2c.scan()
    print(f"I2C devices found: {[hex(d) for d in devices]}")

    imu = IMU(i2c)
    imu.init()

    out = SerialOut()
    interval = 1.0 / SAMPLE_RATE_HZ

    print("START")
    while True:
        sample = imu.read()
        out.send(sample)
        time.sleep(interval)

main()
