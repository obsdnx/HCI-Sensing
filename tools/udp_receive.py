"""
Receive UDP stream from ESP32 WiFi mode and save to CSV.
Run this on your computer while the ESP32 is in MODE='wifi'.

Usage:
    python tools/udp_receive.py
"""
import csv
import socket
from datetime import datetime
from pathlib import Path

PORT = 5005
COLS = ["ax", "ay", "az", "gx", "gy", "gz", "roll", "pitch", "yaw"]


def main():
    out = Path("data") / f"udp_{datetime.now():%Y%m%d_%H%M%S}.csv"
    out.parent.mkdir(exist_ok=True)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))
    print(f"Listening on UDP :{PORT}  →  {out}")
    print("Ctrl+C to stop\n")

    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLS)
        while True:
            try:
                data, addr = sock.recvfrom(256)
                line = data.decode().strip()
                print(line)
                w.writerow(line.split(","))
                f.flush()
            except KeyboardInterrupt:
                break

    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
