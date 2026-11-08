"""
Record labelled gesture samples.
Press a letter key to start recording one gesture, then hold still.
Saves each gesture to data/gestures/<label>_<timestamp>.csv

Usage:
    python tools/gesture_record.py --port /dev/tty.usbserial-110 --samples 80
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
    sys.exit("pip install pyserial")

COLS = ["ax", "ay", "az", "gx", "gy", "gz"]


def read_samples(ser, n):
    buf = []
    while len(buf) < n:
        raw = ser.readline().decode("utf-8", errors="ignore").strip()
        if not raw or "," not in raw:
            continue
        parts = raw.split(",")
        if len(parts) < 7:
            continue
        try:
            buf.append([float(parts[i]) for i in range(1, 7)])
        except ValueError:
            continue
    return buf


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", required=True)
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--samples", type=int, default=80, help="Samples per gesture")
    args = p.parse_args()

    out_dir = Path("data/gestures")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Recording {args.samples} samples per gesture.")
    print("Type a label (e.g. 'swipe_left'), press Enter, then perform the gesture.")
    print("Type 'quit' to stop.\n")

    with serial.Serial(args.port, args.baud, timeout=1) as ser:
        while True:
            label = input("Label > ").strip()
            if label.lower() == "quit":
                break
            if not label:
                continue

            input(f"  Ready to record '{label}' — press Enter then perform gesture immediately...")
            print(f"  Recording {args.samples} samples...", end="", flush=True)

            buf = read_samples(ser, args.samples)

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = out_dir / f"{label}_{ts}.csv"
            with open(path, "w", newline="") as f:
                csv.writer(f).writerows([COLS] + buf)

            print(f" saved to {path}")

    print("Done.")


if __name__ == "__main__":
    main()
