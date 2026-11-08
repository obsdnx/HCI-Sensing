"""SD card logger via SPI. Runs on ESP32 MicroPython. Requires lib/sdcard.py."""
import os
from machine import SPI, Pin
import config


class SDLogger:
    def __init__(self):
        spi = SPI(1, baudrate=1_000_000, polarity=0, phase=0,
                  sck=Pin(config.SD_SCK),
                  mosi=Pin(config.SD_MOSI),
                  miso=Pin(config.SD_MISO))
        import sdcard
        sd = sdcard.SDCard(spi, Pin(config.SD_CS))
        os.mount(sd, "/sd")

        # Find next free filename
        idx = 0
        while True:
            path = f"/sd/session_{idx:04d}.csv"
            try:
                os.stat(path)
                idx += 1
            except OSError:
                break

        self._f = open(path, "w")
        self._f.write("ax,ay,az,gx,gy,gz,roll,pitch,yaw\n")
        print(f"SD logging to {path}")

    def send(self, sample):
        line = "{:.4f},{:.4f},{:.4f},{:.4f},{:.4f},{:.4f},{:.2f},{:.2f},{:.2f}\n".format(
            sample["ax"], sample["ay"], sample["az"],
            sample["gx"], sample["gy"], sample["gz"],
            sample.get("roll", 0), sample.get("pitch", 0), sample.get("yaw", 0),
        )
        self._f.write(line)
        self._f.flush()
