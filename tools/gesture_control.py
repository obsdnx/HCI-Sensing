"""
Hand gesture screen control — swipe/pinch to control the projector screen.
Uses FaceTime camera + MediaPipe hand tracking.

Gestures:
  Swipe left  → next tab     (Cmd+Tab)
  Swipe right → previous tab (Cmd+Shift+Tab)
  Pinch in    → zoom out     (Cmd+-)
  Pinch out   → zoom in      (Cmd+=)

Usage:
    python tools/gesture_control.py
Press Q or Esc to quit.
"""
import math
import os
import time
import urllib.request

import cv2
import mediapipe as mp
import pyautogui
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0

# ── Model ─────────────────────────────────────────────────────────────────────

MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
if not os.path.exists(MODEL_PATH):
    print("Downloading model (~25 MB)...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

# ── Tuning ────────────────────────────────────────────────────────────────────

SWIPE_MIN_DIST   = 0.20   # fraction of frame width to count as a swipe
SWIPE_MIN_SPEED  = 0.40   # must move fast enough (dist / time)
PINCH_CLOSE      = 0.06   # index-thumb distance = pinched
PINCH_OPEN       = 0.18   # index-thumb distance = spread
COOLDOWN         = 0.8    # seconds between actions

# ── Colours ───────────────────────────────────────────────────────────────────

C_LABEL   = (255, 255, 255)
C_ACTION  = (0, 220, 100)
C_NEUTRAL = (100, 100, 100)

# ── Helpers ───────────────────────────────────────────────────────────────────

def hand_centre(lm):
    """Palm centre = average of wrist (0) and middle MCP (9)."""
    return ((lm[0].x + lm[9].x) / 2, (lm[0].y + lm[9].y) / 2)

def pinch_dist(lm):
    return math.sqrt((lm[8].x - lm[4].x)**2 + (lm[8].y - lm[4].y)**2)

def draw_hud(frame, gesture, action):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 50), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    colour = C_ACTION if action else C_NEUTRAL
    cv2.putText(frame, gesture, (12, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, colour, 2, cv2.LINE_AA)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    options = mp_vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=mp_vision.RunningMode.IMAGE,
        num_hands=2,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    detector = mp_vision.HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        raise RuntimeError("Cannot open camera")

    cv2.namedWindow("Gesture Control  —  Q to quit", cv2.WINDOW_NORMAL)

    # Per-hand swipe tracking: {hand_index: (start_x, start_y, start_time)}
    swipe_start = {}
    # Two-hand pinch tracking
    prev_two_hand_dist = None
    last_action = 0.0
    gesture_label = "ready"

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame = cv2.flip(frame, 1)
        h, w  = frame.shape[:2]

        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = detector.detect(mp_img)

        now      = time.time()
        action   = False
        lm_list  = result.hand_landmarks  # list of per-hand landmarks

        # ── Draw skeleton ─────────────────────────────────────────────────────
        for lm in lm_list:
            for pt in lm:
                cv2.circle(frame, (int(pt.x*w), int(pt.y*h)), 4, (0, 180, 255), -1)

        # ── Single hand: swipe + single-hand pinch zoom ───────────────────────
        for idx, lm in enumerate(lm_list):
            cx, cy = hand_centre(lm)

            if idx not in swipe_start:
                swipe_start[idx] = (cx, cy, now)

            sx, sy, st = swipe_start[idx]
            dx = cx - sx
            dt = now - st

            if dt > 0.05:   # enough time to measure speed
                speed = abs(dx) / dt
                if abs(dx) > SWIPE_MIN_DIST and speed > SWIPE_MIN_SPEED:
                    if (now - last_action) > COOLDOWN:
                        if dx < 0:
                            pyautogui.hotkey('command', 'tab')
                            gesture_label = "▶  next tab"
                        else:
                            pyautogui.hotkey('command', 'shift', 'tab')
                            gesture_label = "◀  prev tab"
                        last_action = now
                        action = True
                    swipe_start[idx] = (cx, cy, now)

                if dt > 0.4:   # reset if hand is still
                    swipe_start[idx] = (cx, cy, now)

            # Single-hand pinch zoom (one hand only)
            if len(lm_list) == 1:
                pd = pinch_dist(lm)
                if prev_two_hand_dist is not None:
                    diff = pd - prev_two_hand_dist
                    if abs(diff) > 0.04 and (now - last_action) > COOLDOWN:
                        if diff > 0:
                            pyautogui.hotkey('command', '=')
                            gesture_label = "🔍  zoom in"
                        else:
                            pyautogui.hotkey('command', '-')
                            gesture_label = "🔎  zoom out"
                        last_action = now
                        action = True
                prev_two_hand_dist = pd

        # ── Two hands: spread/pinch zoom ─────────────────────────────────────
        if len(lm_list) == 2:
            c0 = hand_centre(lm_list[0])
            c1 = hand_centre(lm_list[1])
            two_dist = math.sqrt((c0[0]-c1[0])**2 + (c0[1]-c1[1])**2)

            if prev_two_hand_dist is not None:
                diff = two_dist - prev_two_hand_dist
                if abs(diff) > 0.06 and (now - last_action) > COOLDOWN:
                    if diff > 0:
                        pyautogui.hotkey('command', '=')
                        gesture_label = "🔍  zoom in"
                    else:
                        pyautogui.hotkey('command', '-')
                        gesture_label = "🔎  zoom out"
                    last_action = now
                    action = True
            prev_two_hand_dist = two_dist
        else:
            prev_two_hand_dist = None

        draw_hud(frame, gesture_label, action)

        # Guide lines
        cv2.line(frame, (w//3, 55), (w//3, h), (60,60,60), 1)
        cv2.line(frame, (2*w//3, 55), (2*w//3, h), (60,60,60), 1)
        cv2.putText(frame, "swipe", (w//2 - 20, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80,80,80), 1)

        cv2.imshow("Gesture Control  —  Q to quit", frame)
        if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q'), 27):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
