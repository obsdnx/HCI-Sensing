"""
Real-time gesture inference from serial stream.
Detects gesture onset (accel energy spike), collects a window, classifies.

Usage:
    python tools/gesture_infer.py --port /dev/tty.usbserial-110
"""
import argparse
import math
import sys
from collections import deque
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
    import joblib
    import serial
except ImportError:
    sys.exit("pip install numpy pandas scikit-learn joblib pyserial")

MODEL_PATH     = Path("data/gesture_model.pkl")
WINDOW         = 80       # samples to collect per gesture
ONSET_THRESH   = 1.5      # g magnitude above baseline triggers capture
COOLDOWN_SECS  = 1.0
COLS           = ["ax", "ay", "az", "gx", "gy", "gz"]


def extract_features(rows):
    df = pd.DataFrame(rows, columns=COLS)
    feats = []
    for col in COLS:
        x = df[col].values
        feats += [x.mean(), x.std(), x.min(), x.max(),
                  np.percentile(x, 25), np.percentile(x, 75)]
        fft = np.abs(np.fft.rfft(x))[:len(x)//2]
        feats += sorted(fft, reverse=True)[:3]
    return feats


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", required=True)
    p.add_argument("--baud", type=int, default=115200)
    args = p.parse_args()

    if not MODEL_PATH.exists():
        sys.exit(f"No model at {MODEL_PATH}. Run gesture_train.py first.")

    bundle = joblib.load(MODEL_PATH)
    clf, le = bundle["model"], bundle["encoder"]
    print(f"Model loaded. Classes: {list(le.classes_)}")
    print("Waiting for gestures...\n")

    import time
    buf = deque(maxlen=WINDOW)
    capturing = False
    cap_buf = []
    last_gesture = 0.0

    with serial.Serial(args.port, args.baud, timeout=1) as ser:
        while True:
            raw = ser.readline().decode("utf-8", errors="ignore").strip()
            if not raw or "," not in raw:
                continue
            parts = raw.split(",")
            if len(parts) < 7:
                continue
            try:
                row = [float(parts[i]) for i in range(1, 7)]
            except ValueError:
                continue

            ax, ay, az = row[0], row[1], row[2]
            mag = math.sqrt(ax*ax + ay*ay + az*az)

            now = time.time()
            if not capturing and mag > ONSET_THRESH and (now - last_gesture) > COOLDOWN_SECS:
                capturing = True
                cap_buf = [row]
                print("  [capturing...]", end="", flush=True)
            elif capturing:
                cap_buf.append(row)
                if len(cap_buf) >= WINDOW:
                    capturing = False
                    last_gesture = now
                    feats = extract_features(cap_buf)
                    pred = clf.predict([feats])[0]
                    label = le.inverse_transform([pred])[0]
                    proba = clf.predict_proba([feats])[0].max()
                    print(f" → {label}  ({proba:.0%})")


if __name__ == "__main__":
    main()
