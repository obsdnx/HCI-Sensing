"""
Quick plot of a captured session CSV.

Usage:
    python tools/plot.py data/session_20241029_120000.csv
"""
import sys
from pathlib import Path

try:
    import pandas as pd
    import matplotlib.pyplot as plt
except ImportError:
    sys.exit("Install deps: pip install pandas matplotlib")


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python tools/plot.py <csv_file>")

    path = Path(sys.argv[1])
    df = pd.read_csv(path)
    df["t_s"] = df["t_ms"] / 1000.0

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)

    ax1.plot(df["t_s"], df["ax"], label="ax")
    ax1.plot(df["t_s"], df["ay"], label="ay")
    ax1.plot(df["t_s"], df["az"], label="az")
    ax1.set_ylabel("Accel (g)")
    ax1.legend()
    ax1.grid(True)

    ax2.plot(df["t_s"], df["gx"], label="gx")
    ax2.plot(df["t_s"], df["gy"], label="gy")
    ax2.plot(df["t_s"], df["gz"], label="gz")
    ax2.set_ylabel("Gyro (°/s)")
    ax2.set_xlabel("Time (s)")
    ax2.legend()
    ax2.grid(True)

    fig.suptitle(path.stem)
    plt.tight_layout()
    plt.savefig(path.with_suffix(".png"), dpi=150)
    plt.show()
    print(f"Saved plot to {path.with_suffix('.png')}")


if __name__ == "__main__":
    main()
