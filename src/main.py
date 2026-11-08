"""
HCI-Sensing — ESP32 entry point.
Set MODE in config.py: 'serial' | 'wifi' | 'ble' | 'sd'
"""
import time
from machine import I2C, Pin
import config
from drivers.imu import IMU
from filters.madgwick import MadgwickAHRS

if config.MODE == 'wifi':
    from utils.wifi_stream import WiFiStream
    out = WiFiStream(config.WIFI_SSID, config.WIFI_PASSWORD,
                     config.HOST_IP, config.UDP_PORT)
elif config.MODE == 'ble':
    from utils.ble_hid import BleHID
    out = BleHID()
elif config.MODE == 'sd':
    from utils.sd_logger import SDLogger
    out = SDLogger()
else:
    from utils.serial_out import SerialOut
    out = SerialOut()

def main():
    i2c = I2C(config.I2C_BUS, sda=Pin(config.SDA_PIN),
              scl=Pin(config.SCL_PIN), freq=400_000)
    print(f"I2C devices: {[hex(d) for d in i2c.scan()]}")

    imu = IMU(i2c)
    imu.init()

    ahrs = MadgwickAHRS(beta=0.1, sample_period=1.0 / config.SAMPLE_RATE_HZ)
    interval = 1.0 / config.SAMPLE_RATE_HZ

    print("START")
    while True:
        sample = imu.read()
        ahrs.update(sample['gx'], sample['gy'], sample['gz'],
                    sample['ax'], sample['ay'], sample['az'])
        sample['roll'], sample['pitch'], sample['yaw'] = ahrs.euler()
        out.send(sample)
        time.sleep(interval)

main()
