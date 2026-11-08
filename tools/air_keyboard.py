"""
Air keyboard — tilt ESP32 to move cursor, tap to select.
Reads serial CSV stream, uses pitch/roll for cursor, accel spike for tap.

Usage:
    python tools/air_keyboard.py --port /dev/tty.usbserial-110
"""
import argparse
import math
import threading
import time
import tkinter as tk

try:
    import serial
except ImportError:
    import sys; sys.exit("pip install pyserial")

ROWS = [
    list("QWERTYUIOP"),
    list("ASDFGHJKL"),
    list("ZXCVBNM"),
    ["SPACE", "DEL"],
]

KEY_W, KEY_H, PAD = 58, 48, 5
TILT_RANGE   = 25    # degrees of tilt to reach edge of keyboard
TAP_THRESHOLD = 2.2  # g
TAP_COOLDOWN  = 0.4  # seconds

BG       = "#1e1e1e"
KEY_CLR  = "#3a3a3a"
SEL_CLR  = "#0066aa"
HIT_CLR  = "#00cc66"
FG       = "#ffffff"


class AirKeyboard:
    def __init__(self, port, baud=115200):
        self._pitch = 0.0
        self._roll  = 0.0
        self._last_tap = 0.0
        self._typed = ""
        self._cursor_pos = [0.0, 0.0]

        self._root = tk.Tk()
        self._root.title("Air Keyboard")
        self._root.configure(bg=BG)
        self._root.resizable(False, False)

        self._build_ui()
        self._ser = serial.Serial(port, baud, timeout=1)
        t = threading.Thread(target=self._read_serial, daemon=True)
        t.start()
        self._root.after(50, self._tick)

    def _build_ui(self):
        # Text display
        self._text_var = tk.StringVar(value="")
        tk.Label(self._root, textvariable=self._text_var,
                 font=("Courier", 14), bg="#111", fg=FG,
                 anchor="w", width=42, padx=8, pady=6).pack(fill="x", padx=8, pady=(8, 0))

        max_cols = max(len(r) for r in ROWS)
        cw = max_cols * (KEY_W + PAD) + PAD
        ch = len(ROWS) * (KEY_H + PAD) + PAD

        self._cv = tk.Canvas(self._root, width=cw, height=ch,
                             bg="#2a2a2a", highlightthickness=0)
        self._cv.pack(padx=8, pady=8)
        self._cw, self._ch = cw, ch

        self._rects = {}
        self._keys  = []  # (row, col, label, cx, cy)

        for r, row in enumerate(ROWS):
            rw = sum((KEY_W*2 if k in ("SPACE","DEL") else KEY_W) + PAD for k in row) - PAD
            xo = (cw - rw) // 2
            x = xo
            for c, key in enumerate(row):
                kw = KEY_W*2 if key in ("SPACE","DEL") else KEY_W
                y  = PAD + r * (KEY_H + PAD)
                rect = self._cv.create_rectangle(x, y, x+kw, y+KEY_H,
                                                  fill=KEY_CLR, outline="#555", width=1)
                self._cv.create_text(x+kw//2, y+KEY_H//2,
                                     text=key, fill=FG, font=("Helvetica", 10))
                self._rects[(r, c)] = rect
                self._keys.append((r, c, key, x+kw//2, y+KEY_H//2))
                x += kw + PAD

        self._cursor = self._cv.create_oval(0, 0, 18, 18,
                                            fill="#00aaff", outline=FG, width=2)

        self._status = tk.StringVar(value="")
        tk.Label(self._root, textvariable=self._status,
                 font=("Courier", 9), bg=BG, fg="#666").pack(pady=(0, 6))

    def _read_serial(self):
        while True:
            try:
                raw = self._ser.readline().decode("utf-8", errors="ignore").strip()
            except Exception:
                continue
            if not raw or "," not in raw:
                continue
            parts = raw.split(",")
            if len(parts) < 7:
                continue
            try:
                ax = float(parts[1])
                ay = float(parts[2])
                az = float(parts[3])
            except ValueError:
                continue

            self._pitch = math.degrees(math.atan2(ay, math.sqrt(ax*ax + az*az)))
            self._roll  = math.degrees(math.atan2(ax, math.sqrt(ay*ay + az*az)))

            mag = math.sqrt(ax*ax + ay*ay + az*az)
            now = time.time()
            if mag > TAP_THRESHOLD and (now - self._last_tap) > TAP_COOLDOWN:
                self._last_tap = now
                self._root.after(0, self._on_tap)

    def _tick(self):
        cx = self._cw/2 + (self._roll  / TILT_RANGE) * (self._cw/2)
        cy = self._ch/2 - (self._pitch / TILT_RANGE) * (self._ch/2)
        cx = max(10, min(self._cw-10, cx))
        cy = max(10, min(self._ch-10, cy))
        self._cursor_pos = [cx, cy]

        self._cv.coords(self._cursor, cx-9, cy-9, cx+9, cy+9)

        nearest = self._nearest(cx, cy)
        for key, rect in self._rects.items():
            self._cv.itemconfig(rect, fill=KEY_CLR)
        if nearest:
            self._cv.itemconfig(self._rects[nearest[:2]], fill=SEL_CLR)

        self._status.set(f"pitch {self._pitch:+.1f}°  roll {self._roll:+.1f}°  "
                         f"tilt to move · tap to select")
        self._root.after(50, self._tick)

    def _nearest(self, cx, cy):
        best, bd = None, float("inf")
        for entry in self._keys:
            d = (cx - entry[3])**2 + (cy - entry[4])**2
            if d < bd:
                bd, best = d, entry
        return best

    def _on_tap(self):
        cx, cy = self._cursor_pos
        hit = self._nearest(cx, cy)
        if not hit:
            return
        r, c, key = hit[0], hit[1], hit[2]
        if key == "DEL":
            self._typed = self._typed[:-1]
        elif key == "SPACE":
            self._typed += " "
        else:
            self._typed += key
        self._text_var.set(self._typed)

        self._cv.itemconfig(self._rects[(r, c)], fill=HIT_CLR)
        self._root.after(180, lambda: self._cv.itemconfig(self._rects[(r, c)], fill=KEY_CLR))

    def run(self):
        self._root.mainloop()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", required=True, help="e.g. /dev/tty.usbserial-110")
    p.add_argument("--baud", type=int, default=115200)
    args = p.parse_args()
    AirKeyboard(args.port, args.baud).run()


if __name__ == "__main__":
    main()
