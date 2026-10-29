# HCI-Sensing

IMU sensing unit — ESP32 + LSM6DS3, Imperial coursework project.

## Hardware

| Part | Notes |
|------|-------|
| ESP32 | MicroPython firmware |
| IMU | LSM6DS3 breakout (DollaTek), I2C addr `0x6A` |

## Wiring (I2C)

| LSM6DS3 pin | ESP32 pin |
|-------------|-----------|
| 3V3 | 3V3 |
| GND | GND |
| SCL | GPIO 22 |
| SDA | GPIO 21 |

Only 4 wires needed. Leave CD and SAO unconnected.

## Project layout

```
src/
  main.py              # ESP32 entry point — runs on-device
  drivers/
    imu.py             # LSM6DS3 I2C driver
  utils/
    serial_out.py      # Streams CSV over USB serial
tools/
  capture.py           # Host: record serial stream → CSV
  plot.py              # Host: plot a captured CSV
data/                  # Captured sessions (gitignored)
```

## Quickstart

### 1 — Flash MicroPython onto the ESP32

```bash
pip install esptool

# Erase first
esptool.py --port /dev/tty.SLAB_USBtoUART erase_flash

# Flash — download .bin from https://micropython.org/download/ESP32_GENERIC/
esptool.py --chip esp32 --port /dev/tty.SLAB_USBtoUART write_flash -z 0x1000 ESP32_GENERIC-*.bin
```

Find your port: `ls /dev/tty.*` after plugging in.

### 2 — Copy firmware to the ESP32

```bash
pip install mpremote
mpremote connect auto mkdir drivers
mpremote connect auto mkdir utils
mpremote connect auto cp src/main.py :main.py
mpremote connect auto cp src/drivers/imu.py :drivers/imu.py
mpremote connect auto cp src/utils/serial_out.py :utils/serial_out.py
```

### 3 — Verify IMU is detected

```bash
mpremote connect auto exec "from machine import I2C, Pin; i2c = I2C(0, sda=Pin(21), scl=Pin(22)); print([hex(d) for d in i2c.scan()])"
```

Should print `['0x6a']`.

### 4 — Capture data

```bash
pip install -r requirements.txt
python tools/capture.py --port /dev/tty.SLAB_USBtoUART --out data/test.csv
```

### 5 — Plot

```bash
python tools/plot.py data/test.csv
```
