"""
Finger keyboard — virtual QWERTY over FaceTime camera.
Point with index finger to highlight a key.
Pinch (index tip + thumb tip close together) to press it.

Usage:
    python tools/finger_keyboard.py
Press Q or Esc to quit.
"""
import math
import os
import time
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

# ── Model download ────────────────────────────────────────────────────────────

MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)

if not os.path.exists(MODEL_PATH):
    print("Downloading hand landmarker model (~25 MB)...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("Done.")

# ── Layout ────────────────────────────────────────────────────────────────────

ROWS = [
    list("QWERTYUIOP"),
    list("ASDFGHJKL"),
    list("ZXCVBNM"),
    ["SPACE", "DEL"],
]

KEY_W, KEY_H, PAD = 58, 46, 6

C_BG      = (40,  40,  40)
C_HOVER   = (170, 120,  0)
C_PRESSED = (0,  180,  80)
C_TEXT    = (255, 255, 255)
C_CURSOR  = (0,  200, 255)
C_TYPED   = (0,  200, 255)

PINCH_THRESHOLD = 0.055
PRESS_COOLDOWN  = 0.45

# ── Key geometry ──────────────────────────────────────────────────────────────

def build_keys(frame_w, frame_h):
    total_h = len(ROWS) * (KEY_H + PAD) + PAD
    kb_top  = frame_h - total_h - 10
    keys = []
    for r, row in enumerate(ROWS):
        row_w = sum((KEY_W*2 if k in ("SPACE","DEL") else KEY_W) + PAD for k in row) - PAD
        xo = (frame_w - row_w) // 2
        x  = xo
        for key in row:
            kw = KEY_W * 2 if key in ("SPACE", "DEL") else KEY_W
            y1 = kb_top + r * (KEY_H + PAD) + PAD
            keys.append((key, x, y1, x + kw, y1 + KEY_H))
            x += kw + PAD
    return keys


def nearest_key(keys, px, py):
    best, bd = None, float("inf")
    for entry in keys:
        _, x1, y1, x2, y2 = entry
        cx, cy = (x1+x2)//2, (y1+y2)//2
        d = (px-cx)**2 + (py-cy)**2
        if d < bd:
            bd, best = d, entry
    return best


def in_key(entry, px, py):
    _, x1, y1, x2, y2 = entry
    return x1 <= px <= x2 and y1 <= py <= y2

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    options = mp_vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=mp_vision.RunningMode.IMAGE,
        num_hands=1,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    detector = mp_vision.HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Cannot open camera")

    typed       = ""
    last_press  = 0.0
    flash_key   = None
    flash_until = 0.0

    # Force window to front on macOS
    cv2.namedWindow("Finger Keyboard  —  pinch to type  |  Q to quit", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Finger Keyboard  —  pinch to type  |  Q to quit", 800, 600)

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Camera read failed")
            break

        frame = cv2.flip(frame, 1)
        h, w  = frame.shape[:2]
        keys  = build_keys(w, h)

        # Darken keyboard area
        kb_top = keys[0][2] - PAD
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, kb_top - PAD), (w, h), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

        now = time.time()

        # Draw keys
        for key, x1, y1, x2, y2 in keys:
            colour = C_PRESSED if (flash_key == key and now < flash_until) else C_BG
            cv2.rectangle(frame, (x1, y1), (x2, y2), colour, -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (90, 90, 90), 1)
            fs = 0.45 if key in ("SPACE","DEL") else 0.5
            tx = x1 + (x2-x1)//2 - len(key)*6
            ty = y1 + (y2-y1)//2 + 5
            cv2.putText(frame, key, (tx, ty),
                        cv2.FONT_HERSHEY_SIMPLEX, fs, C_TEXT, 1, cv2.LINE_AA)

        # Hand detection
        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = detector.detect(mp_img)

        hovered = None
        if result.hand_landmarks:
            lm = result.hand_landmarks[0]

            ix, iy = int(lm[8].x * w), int(lm[8].y * h)
            tx, ty = int(lm[4].x * w), int(lm[4].y * h)

            cv2.circle(frame, (ix, iy), 10, C_CURSOR, -1)
            cv2.circle(frame, (tx, ty),  7, (100, 100, 255), -1)

            nearest = nearest_key(keys, ix, iy)
            if nearest and in_key(nearest, ix, iy):
                hovered = nearest
                _, x1, y1, x2, y2 = hovered
                cv2.rectangle(frame, (x1, y1), (x2, y2), C_HOVER, 2)

            pinch_dist = math.sqrt((lm[8].x - lm[4].x)**2 + (lm[8].y - lm[4].y)**2)
            is_pinch   = pinch_dist < PINCH_THRESHOLD

            if is_pinch and hovered and (now - last_press) > PRESS_COOLDOWN:
                last_press  = now
                key_label   = hovered[0]
                flash_key   = key_label
                flash_until = now + 0.25
                if key_label == "DEL":
                    typed = typed[:-1]
                elif key_label == "SPACE":
                    typed += " "
                else:
                    typed += key_label

            if is_pinch:
                cv2.line(frame, (ix, iy), (tx, ty), C_PRESSED, 2)

        # Text bar
        cv2.rectangle(frame, (0, 0), (w, 38), (20, 20, 20), -1)
        display = typed[-55:] if len(typed) > 55 else typed
        cv2.putText(frame, display + "|", (10, 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, C_TYPED, 1, cv2.LINE_AA)

        cv2.imshow("Finger Keyboard  —  pinch to type  |  Q to quit", frame)
        if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q'), 27):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Typed:", typed)


if __name__ == "__main__":
    main()
