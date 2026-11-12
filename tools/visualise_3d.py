"""
Live 3D board visualiser.
Reads serial CSV, runs Madgwick filter on host, renders a rotating box.

Usage:
    python tools/visualise_3d.py --port /dev/tty.usbserial-110
"""
import argparse
import math
import threading
import sys
from collections import deque

try:
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import serial
except ImportError:
    sys.exit("pip install numpy matplotlib pyserial")

# ── Madgwick filter (host-side) ──────────────────────────────────────────────

class Madgwick:
    def __init__(self, beta=0.05, dt=0.01):
        self.beta = beta
        self.dt   = dt
        self.q    = np.array([1.0, 0.0, 0.0, 0.0])

    def update(self, gx, gy, gz, ax, ay, az):
        gx, gy, gz = math.radians(gx), math.radians(gy), math.radians(gz)
        q = self.q
        norm = math.sqrt(ax*ax + ay*ay + az*az)
        if norm < 1e-10:
            return
        ax /= norm; ay /= norm; az /= norm

        q0,q1,q2,q3 = q
        s0 = 4*q0*q2*q2 + 2*q2*ax + 4*q0*q1*q1 - 2*q1*ay
        s1 = 4*q1*q3*q3 - 2*q3*ax + 4*q0*q0*q1 - 2*q0*ay - 4*q1 + 8*q1*q1*q1 + 8*q1*q2*q2 + 4*q1*az
        s2 = 4*q0*q0*q2 + 2*q0*ax + 4*q2*q3*q3 - 2*q3*ay - 4*q2 + 8*q2*q1*q1 + 8*q2*q2*q2 + 4*q2*az
        s3 = 4*q1*q1*q3 - 2*q1*ax + 4*q2*q2*q3 - 2*q2*ay
        ns = math.sqrt(s0*s0+s1*s1+s2*s2+s3*s3)
        if ns > 0:
            s0/=ns; s1/=ns; s2/=ns; s3/=ns

        qd0 = 0.5*(-q1*gx-q2*gy-q3*gz) - self.beta*s0
        qd1 = 0.5*( q0*gx+q2*gz-q3*gy) - self.beta*s1
        qd2 = 0.5*( q0*gy-q1*gz+q3*gx) - self.beta*s2
        qd3 = 0.5*( q0*gz+q1*gy-q2*gx) - self.beta*s3

        q = q + np.array([qd0,qd1,qd2,qd3]) * self.dt
        self.q = q / np.linalg.norm(q)

    def rotation_matrix(self):
        q0,q1,q2,q3 = self.q
        return np.array([
            [1-2*(q2*q2+q3*q3), 2*(q1*q2-q0*q3),   2*(q1*q3+q0*q2)],
            [2*(q1*q2+q0*q3),   1-2*(q1*q1+q3*q3), 2*(q2*q3-q0*q1)],
            [2*(q1*q3-q0*q2),   2*(q2*q3+q0*q1),   1-2*(q1*q1+q2*q2)],
        ])

# ── Board geometry ────────────────────────────────────────────────────────────

# Thin rectangular box representing the ESP32 board (w x h x d)
W, H, D = 1.6, 0.8, 0.08
_verts = np.array([
    [-W/2,-H/2,-D/2],[W/2,-H/2,-D/2],[W/2,H/2,-D/2],[-W/2,H/2,-D/2],
    [-W/2,-H/2, D/2],[W/2,-H/2, D/2],[W/2,H/2, D/2],[-W/2,H/2, D/2],
])
_faces = [
    [0,1,2,3],  # bottom
    [4,5,6,7],  # top
    [0,1,5,4],  # front
    [2,3,7,6],  # back
    [0,3,7,4],  # left
    [1,2,6,5],  # right
]
_face_colors = ["#1a6b9a","#2196f3","#0d47a1","#1565c0","#1976d2","#42a5f5"]

# ── Shared state ──────────────────────────────────────────────────────────────

_latest = deque(maxlen=1)   # holds latest (ax,ay,az,gx,gy,gz)
_filter = None


def _read_serial(port, baud):
    with serial.Serial(port, baud, timeout=1) as ser:
        while True:
            raw = ser.readline().decode("utf-8", errors="ignore").strip()
            if not raw or "," not in raw:
                continue
            parts = raw.split(",")
            if len(parts) < 7:
                continue
            try:
                vals = [float(parts[i]) for i in range(1, 7)]
                _latest.append(vals)
            except ValueError:
                continue


def _animate(frame, poly, ax3d, title_text):
    global _filter
    if not _latest:
        return poly,

    ax_v, ay_v, az_v, gx_v, gy_v, gz_v = _latest[-1]
    _filter.update(gx_v, gy_v, gz_v, ax_v, ay_v, az_v)
    R = _filter.rotation_matrix()

    rotated = (_verts @ R.T)
    face_verts = [[rotated[i] for i in face] for face in _faces]

    poly.set_verts(face_verts)

    roll  = math.degrees(math.atan2(2*(_filter.q[0]*_filter.q[1]+_filter.q[2]*_filter.q[3]),
                                     1-2*(_filter.q[1]**2+_filter.q[2]**2)))
    pitch = math.degrees(math.asin(max(-1,min(1,2*(_filter.q[0]*_filter.q[2]-_filter.q[3]*_filter.q[1])))))
    yaw   = math.degrees(math.atan2(2*(_filter.q[0]*_filter.q[3]+_filter.q[1]*_filter.q[2]),
                                     1-2*(_filter.q[2]**2+_filter.q[3]**2)))
    title_text.set_text(f"roll {roll:+.1f}°   pitch {pitch:+.1f}°   yaw {yaw:+.1f}°")
    return poly,


def main():
    global _filter

    p = argparse.ArgumentParser()
    p.add_argument("--port", required=True)
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--beta", type=float, default=0.05, help="Madgwick beta (higher=faster but noisier)")
    args = p.parse_args()

    _filter = Madgwick(beta=args.beta, dt=0.01)

    t = threading.Thread(target=_read_serial, args=(args.port, args.baud), daemon=True)
    t.start()

    fig = plt.figure(figsize=(7, 6), facecolor="#111")
    ax3d = fig.add_subplot(111, projection="3d", facecolor="#111")
    ax3d.set_xlim(-1.2, 1.2); ax3d.set_ylim(-1.2, 1.2); ax3d.set_zlim(-1.2, 1.2)
    ax3d.set_xlabel("X", color="#888"); ax3d.set_ylabel("Y", color="#888"); ax3d.set_zlabel("Z", color="#888")
    ax3d.tick_params(colors="#555")
    for spine in ax3d.spines.values():
        spine.set_color("#333")

    face_verts = [[_verts[i] for i in face] for face in _faces]
    poly = Poly3DCollection(face_verts, alpha=0.85,
                            facecolors=_face_colors, edgecolors="#ffffff44", linewidths=0.5)
    ax3d.add_collection3d(poly)

    title_text = ax3d.set_title("", color="white", fontsize=11, pad=12)

    ani = animation.FuncAnimation(fig, _animate, fargs=(poly, ax3d, title_text),
                                  interval=20, blit=False, cache_frame_data=False)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
