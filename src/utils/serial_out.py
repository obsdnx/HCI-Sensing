"""CSV over USB serial. Format: t_ms,ax,ay,az,gx,gy,gz,roll,pitch,yaw"""
import time


class SerialOut:
    def __init__(self):
        self._t0 = time.ticks_ms()

    def send(self, sample: dict):
        t = time.ticks_diff(time.ticks_ms(), self._t0)
        print("{},{:.4f},{:.4f},{:.4f},{:.4f},{:.4f},{:.4f},{:.2f},{:.2f},{:.2f}".format(
            t,
            sample["ax"], sample["ay"], sample["az"],
            sample["gx"], sample["gy"], sample["gz"],
            sample.get("roll", 0), sample.get("pitch", 0), sample.get("yaw", 0),
        ))
