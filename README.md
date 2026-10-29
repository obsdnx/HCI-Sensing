# HCI-Sensing

IMU sensing unit — Raspberry Pi Pico + IMU sensor, Imperial coursework project.

## Hardware

| Part | Notes |
|------|-------|
| Raspberry Pi Pico | RP2040, MicroPython firmware |
| IMU | Default: MPU-6050 (I2C addr `0x68`). Swap driver for BNO055/LSM6DS3/ICM-42688 etc. |
| Wiring | SDA → GP4, SCL → GP5 (3.3 V logic, no level shifter needed) |

## Project layout

```
src/
  main.py              # Pico entry point — runs on-device
  drivers/
    imu.py             # IMU register driver (MPU-6050 default)
  utils/
    serial_out.py      # Streams CSV over USB serial
lib/                   # Third-party .mpy libs (drop here, copy to Pico)
tools/
  capture.py           # Host: record serial stream → CSV
  plot.py              # Host: plot a captured CSV
data/                  # Captured sessions (gitignored)
```

## Quickstart

### 1 — Flash MicroPython onto the Pico

Download the latest `.uf2` from https://micropython.org/download/RPI_PICO/ and drag it onto the Pico in BOOTSEL mode.

### 2 — Copy firmware to the Pico

Use `mpremote` or Thonny to copy:

```bash
pip install mpremote
mpremote connect auto cp src/main.py :main.py
mpremote connect auto cp src/drivers/imu.py :drivers/imu.py
mpremote connect auto cp src/utils/serial_out.py :utils/serial_out.py
```

Or use Thonny's file manager.

### 3 — Capture data on the host

```bash
pip install -r requirements.txt
python tools/capture.py --port /dev/tty.usbmodem1101 --out data/test.csv
```

Find your port: `ls /dev/tty.usbmodem*` (macOS) or `ls /dev/ttyACM*` (Linux).

### 4 — Plot a session

```bash
python tools/plot.py data/test.csv
```

## Swapping the IMU chip

Edit `src/drivers/imu.py`:
- Change `_DEFAULT_ADDR` to your chip's I2C address
- Update the register constants and `_ACCEL_SCALE` / `_GYRO_SCALE` for your chip's datasheet
- The `IMU.read()` return dict keys (`ax/ay/az/gx/gy/gz`) stay the same so nothing else breaks
