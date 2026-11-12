"""
IMU mouse control — tilt to move cursor, tap to click.

On startup: hold the board flat and still for 2 seconds to calibrate.
Tilt left/right  → cursor moves left/right
Tilt forward/back → cursor moves up/down
Sharp tap (fast flick) → left click
Ctrl+C → stop

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

DEAD_ZONE     = 3.0    # degrees — ignore tiny tilts
SENSITIVITY   = 0.9    # pixels per degree per tick
MAX_SPEED     = 20     # pixels per tick cap
TAP_THRESH    = 2.8    # g magnitude for tap (higher = less sensitive)
TAP_COOLDOWN  = 0.8    # seconds between clicks
CALIB_SAMPLES = 50     # samples collected during calibration (~0.5s at 100Hz)

# ── Madgwick ──────────────────────────────────────────────────────────────────

class Madgwick:
    def __init__(self, beta=0.03, dt=0.01):
        self.beta = beta
        self.dt   = dt
        self.q    = [1.0, 0.0, 0.0, 0.0]

    def update(self, gx, gy, gz, ax, ay, az):
        gx, gy, gz = math.radians(gx), math.radians(gy), math.radians(gz)
        q0,q1,q2,q3 = self.q
        norm = math.sqrt(ax*ax+ay*ay+az*az)
        if norm < 1e-10: return
        ax/=norm; ay/=norm; az/=norm
        s0 = 4*q0*q2*q2+2*q2*ax+4*q0*q1*q1-2*q1*ay
        s1 = 4*q1*q3*q3-2*q3*ax+4*q0*q0*q1-2*q0*ay-4*q1+8*q1**3+8*q1*q2*q2+4*q1*az
        s2 = 4*q0*q0*q2+2*q0*ax+4*q2*q3*q3-2*q3*ay-4*q2+8*q2*q1*q1+8*q2**3+4*q2*az
        s3 = 4*q1*q1*q3-2*q1*ax+4*q2*q2*q3-2*q2*ay
        ns = math.sqrt(s0*s0+s1*s1+s2*s2+s3*s3)
        if ns > 0: s0/=ns; s1/=ns; s2/=ns; s3/=ns
        qd = [
            0.5*(-q1*gx-q2*gy-q3*gz)-self.beta*s0,
            0.5*( q0*gx+q2*gz-q3*gy)-self.beta*s1,
            0.5*( q0*gy-q1*gz+q3*gx)-self.beta*s2,
            0.5*( q0*gz+q1*gy-q2*gx)-self.beta*s3,
        ]
        q = [self.q[i]+qd[i]*self.dt for i in range(4)]
        n = math.sqrt(sum(x*x for x in q))
        self.q = [x/n for x in q]

    def euler(self):
        q0,q1,q2,q3 = self.q
        roll  = math.degrees(math.atan2(2*(q0*q1+q2*q3), 1-2*(q1*q1+q2*q2)))
        pitch = math.degrees(math.asin(max(-1.0, min(1.0, 2*(q0*q2-q3*q1)))))
        return roll, pitch

# ── Shared state ──────────────────────────────────────────────────────────────

_latest   = deque(maxlen=1)
_tap_flag = threading.Event()


def _read_serial(port, baud):
    last_tap = 0.0
    prev_mag = 1.0
    with serial.Serial(port, baud, timeout=1) as ser:
        while True:
            try:
                raw = ser.readline().decode("utf-8", errors="ignore").strip()
            except Exception:
                break
            if not raw or "," not in raw:
                continue
            parts = raw.split(",")
            if len(parts) < 7:
                continue
            try:
                vals = [float(parts[i]) for i in range(1, 7)]
            except ValueError:
                continue

            ax, ay, az = vals[0], vals[1], vals[2]
            mag = math.sqrt(ax*ax + ay*ay + az*az)

            # tap = spike from near-1g up past threshold then back
            now = time.time()
            if prev_mag < 1.5 and mag > TAP_THRESH and (now - last_tap) > TAP_COOLDOWN:
                last_tap = now
                _tap_flag.set()
            prev_mag = mag

            _latest.append(vals)


def _apply_dead_zone(val):
    if abs(val) < DEAD_ZONE:
        return 0.0
    return math.copysign(abs(val) - DEAD_ZONE, val)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", required=True)
    p.add_argument("--baud", type=int, default=115200)
    args = p.parse_args()

    # ── Start serial thread ───────────────────────────────────────────────────
    t = threading.Thread(target=_read_serial, args=(args.port, args.baud), daemon=True)
    t.start()

    # ── Calibration ───────────────────────────────────────────────────────────
    print("CALIBRATION: hold the board flat and still...")
    filt = Madgwick(beta=0.1, dt=0.01)   # high beta to converge fast during calib

    calib_buf = []
    while len(calib_buf) < CALIB_SAMPLES:
        if _latest:
            ax, ay, az, gx, gy, gz = _latest[-1]
            filt.update(gx, gy, gz, ax, ay, az)
            if len(calib_buf) > 5:    # skip first 5 to let filter settle
                calib_buf.append(filt.euler())
        time.sleep(0.01)

    roll_offset  = sum(r for r,_ in calib_buf) / len(calib_buf)
    pitch_offset = sum(p for _,p in calib_buf) / len(calib_buf)
    print(f"Calibrated — offset: roll {roll_offset:+.1f}°  pitch {pitch_offset:+.1f}°")

    filt.beta = 0.03   # lower beta for smooth tracking after calib

    print("\nIMU mouse control running.")
    print("Tilt to move  |  Tap to click  |  Ctrl+C to stop\n")

    try:
        while True:
            if _tap_flag.is_set():
                _tap_flag.clear()
                pyautogui.click()
                print("click")
                break

            if _latest:
                ax, ay, az, gx, gy, gz = _latest[-1]
                filt.update(gx, gy, gz, ax, ay, az)
                roll, pitch = filt.euler()

                # subtract calibration offset
                roll  -= roll_offset
                pitch -= pitch_offset

                dx =  _apply_dead_zone(roll)  * SENSITIVITY
                dy = -_apply_dead_zone(pitch) * SENSITIVITY

                dx = max(-MAX_SPEED, min(MAX_SPEED, dx))
                dy = max(-MAX_SPEED, min(MAX_SPEED, dy))

                if dx != 0 or dy != 0:
                    pyautogui.move(int(dx), int(dy))

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
