"""UDP stream over WiFi. Runs on ESP32 MicroPython."""
import network
import socket
import time


class WiFiStream:
    def __init__(self, ssid, password, host_ip, port=5005):
        self._host = host_ip
        self._port = port
        self._sock = None
        self._connect(ssid, password)

    def _connect(self, ssid, password):
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        if not wlan.isconnected():
            print(f"Connecting to {ssid}...")
            wlan.connect(ssid, password)
            timeout = 15
            while not wlan.isconnected() and timeout > 0:
                time.sleep(1)
                timeout -= 1
            if not wlan.isconnected():
                raise RuntimeError("WiFi failed — check SSID/password in config.py")
        print(f"WiFi: {wlan.ifconfig()}")
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, sample):
        line = "{:.4f},{:.4f},{:.4f},{:.4f},{:.4f},{:.4f},{:.2f},{:.2f},{:.2f}".format(
            sample["ax"], sample["ay"], sample["az"],
            sample["gx"], sample["gy"], sample["gz"],
            sample.get("roll", 0), sample.get("pitch", 0), sample.get("yaw", 0),
        )
        self._sock.sendto(line.encode(), (self._host, self._port))
