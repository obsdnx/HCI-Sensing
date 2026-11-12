"""
IMU mouse control — tilt to move cursor, tap to click.
Roll/pitch computed on ESP32 (Madgwick), streamed at 460800 baud.

On startup: hold the board flat for ~0.5s to calibrate.
Tap → click then stop. Ctrl+C → stop without clicking.

Usage:
    python tools/mouse_control.py --port /dev/tty.usbserial-110
"""
import argparse
import math
import sys
import threading
import time
from collections import deque

try:
    import pyautogui
    import serial
except ImportError:
    sys.exit("pip install pyautogui pyserial")

pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0

DEAD_ZONE     = 3.0   # degrees
SENSITIVITY   = 0.9   # pixels per degree per tick
MAX_SPEED     = 20    # pixels per tick cap
CALIB_SAMPLES = 50

_latest   = deque(maxlen=1)
_tap_flag = threading.Event()


def _read_serial(port, baud):
    with serial.Serial(port, baud, timeout=1) as ser:
        while True:
            try:
                raw = ser.readline().decode("utf-8", errors="ignore").strip()
            except Exception:
                break
            if not raw or "," not in raw:
                continue
            parts = raw.split(",")
            if len(parts) < 10:
                continue
            try:
                roll  = float(parts[7])
                pitch = float(parts[8])
                tap   = int(parts[9])
            except ValueError:
                continue
            if tap:
                _tap_flag.set()
            _latest.append((roll, pitch))


def _apply_dead_zone(val):
    if abs(val) < DEAD_ZONE:
        return 0.0
    return math.copysign(abs(val) - DEAD_ZONE, val)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", required=True)
    p.add_argument("--baud", type=int, default=460800)
    args = p.parse_args()

    t = threading.Thread(target=_read_serial, args=(args.port, args.baud), daemon=True)
    t.start()

    # Calibration
    print("CALIBRATION: hold board flat and still...")
    buf = []
    while len(buf) < CALIB_SAMPLES:
        if _latest:
            buf.append(_latest[-1])
        time.sleep(0.01)

    roll_offset  = sum(r for r,_ in buf) / len(buf)
    pitch_offset = sum(p for _,p in buf) / len(buf)
    print(f"Done — offset: roll {roll_offset:+.1f}°  pitch {pitch_offset:+.1f}°")
    print("\nTilt to move  |  Tap to click and stop  |  Ctrl+C to stop\n")

    try:
        while True:
            if _tap_flag.is_set():
                _tap_flag.clear()
                pyautogui.click()
                print("click")
                break

            if _latest:
                roll, pitch = _latest[-1]
                dx =  _apply_dead_zone(roll  - roll_offset)  * SENSITIVITY
                dy = -_apply_dead_zone(pitch - pitch_offset) * SENSITIVITY
                dx = max(-MAX_SPEED, min(MAX_SPEED, dx))
                dy = max(-MAX_SPEED, min(MAX_SPEED, dy))
                if dx != 0 or dy != 0:
                    pyautogui.move(int(dx), int(dy))

            time.sleep(0.01)

    except KeyboardInterrupt:
        pass
    print("Stopped.")


if __name__ == "__main__":
    main()
