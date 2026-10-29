"""
Serialises IMU samples to USB serial as CSV lines.
Format: ax,ay,az,gx,gy,gz
Host tools parse this format.
"""
import time


class SerialOut:
    def __init__(self):
        self._t0 = time.ticks_ms()

    def send(self, sample: dict):
        t = time.ticks_diff(time.ticks_ms(), self._t0)
        line = "{},{:.4f},{:.4f},{:.4f},{:.4f},{:.4f},{:.4f}".format(
            t,
            sample["ax"], sample["ay"], sample["az"],
            sample["gx"], sample["gy"], sample["gz"],
        )
        print(line)
