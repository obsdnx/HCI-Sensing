"""
Host-side serial capture tool.
Reads CSV lines from the Pico over USB serial and saves to a timestamped CSV.

Usage:
    python tools/capture.py --port /dev/tty.usbmodem* --out data/session.csv
"""
import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import serial
except ImportError:
    sys.exit("Install pyserial: pip install pyserial")

COLS = ["t_ms", "ax", "ay", "az", "gx", "gy", "gz"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True, help="Serial port, e.g. /dev/tty.usbmodem1101")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--out", default=None, help="Output CSV path (auto-named if omitted)")
    args = parser.parse_args()

    out_path = Path(args.out) if args.out else Path("data") / f"session_{datetime.now():%Y%m%d_%H%M%S}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Capturing from {args.port} → {out_path}")
    print("Press Ctrl+C to stop.\n")

    with serial.Serial(args.port, args.baud, timeout=1) as ser, \
         open(out_path, "w", newline="") as f:

        writer = csv.writer(f)
        writer.writerow(COLS)

        while True:
            try:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
            except KeyboardInterrupt:
                break

            if not line or line.startswith("I2C") or line.startswith("IMU") or line == "START":
                print(f"[info] {line}")
                continue

            parts = line.split(",")
            if len(parts) == 7:
                writer.writerow(parts)
                f.flush()
                print(line)

    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
