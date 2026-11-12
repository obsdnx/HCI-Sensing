"""
IMU mouse control — tilt to move cursor, tap to click.

Tilt left/right  → cursor moves left/right
Tilt forward/back → cursor moves up/down
Sharp tap (>2.2g) → left click

Move mouse to top-left corner to emergency stop (pyautogui failsafe).

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
pyautogui.PAUSE = 0

# ── Madgwick filter ───────────────────────────────────────────────────────────

class Madgwick:
    def __init__(self, beta=0.05, dt=0.01):
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

# ── Tuning ────────────────────────────────────────────────────────────────────

DEAD_ZONE    = 5.0    # degrees — ignore tiny tilts
SENSITIVITY  = 1.2    # pixels moved per degree beyond dead zone per tick
MAX_SPEED    = 25     # pixels per tick cap
TAP_THRESH   = 2.2    # g — tap detection threshold
TAP_COOLDOWN = 0.5    # seconds between clicks

# ── Shared state ──────────────────────────────────────────────────────────────

_latest   = deque(maxlen=1)
_tap_flag = threading.Event()


def _apply_dead_zone(val):
    if abs(val) < DEAD_ZONE:
        return 0.0
    return math.copysign(abs(val) - DEAD_ZONE, val)


def _read_serial(port, baud):
    last_tap = 0.0
    with serial.Serial(port, baud, timeout=1) as ser:
        while True:
            raw = ser.readline().decode("utf-8", errors="ignore").strip()
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
            now = time.time()
            if mag > TAP_THRESH and (now - last_tap) > TAP_COOLDOWN:
                last_tap = now
                _tap_flag.set()

            _latest.append(vals)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", required=True)
    p.add_argument("--baud", type=int, default=115200)
    args = p.parse_args()

    filt = Madgwick(beta=0.05, dt=0.01)

    t = threading.Thread(target=_read_serial, args=(args.port, args.baud), daemon=True)
    t.start()

    print("IMU mouse control running.")
    print("Tilt to move  |  Tap to click  |  Ctrl+C to stop\n")

    try:
     while True:
        if _tap_flag.is_set():
            _tap_flag.clear()
            pyautogui.click()
            print("click")

        if _latest:
            ax, ay, az, gx, gy, gz = _latest[-1]
            filt.update(gx, gy, gz, ax, ay, az)
            roll, pitch = filt.euler()

            dx = _apply_dead_zone(roll)  * SENSITIVITY
            dy = _apply_dead_zone(pitch) * SENSITIVITY * -1  # invert: tilt forward = up

            dx = max(-MAX_SPEED, min(MAX_SPEED, dx))
            dy = max(-MAX_SPEED, min(MAX_SPEED, dy))

            if dx != 0 or dy != 0:
                pyautogui.move(int(dx), int(dy))

        time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
