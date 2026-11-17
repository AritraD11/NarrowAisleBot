#!/usr/bin/env python3
"""
analyze_log.py - summarise and plot a telemetry CSV.

Works on any CSV written by tools/encoder_logger.py (plant, staircase,
steps, sweep, record) or by the dashboard's REC button. Both use the same
header: pi_time_s, mcu_ms, then <motor>_target_rads, _actual_rads, _pwm per
motor, then optionally _error, _ff, _iterm, _pos_rad per motor.

    python3 analyze_log.py ~/robot_logs/steps_20261112_101500.csv
    python3 analyze_log.py run.csv --no-plot          # numbers only
    python3 analyze_log.py run.csv --pwm-max 1023     # 10-bit PWM

Prints, per motor:
    RMS tracking error   while the target is non-zero
    saturation %         samples at >= 98 % of PWM_MAX: no headroom left
    sign mismatch %      wheel turning against its target (wiring or slip)
    distance             integral of |actual| in radians and metres
Writes <csv>_plot.png beside the CSV if matplotlib is installed
(sudo apt install python3-matplotlib).
"""
import argparse
import csv
import json
import math
import os
import sys


def load(path):
    with open(path) as fh:
        r = csv.reader(fh)
        header = next(r)
        rows = [[float(x) if x not in ("", None) else float("nan") for x in row] for row in r if row]
    motors = [h[:-len("_target_rads")] for h in header if h.endswith("_target_rads")]
    col = {h: i for i, h in enumerate(header)}
    t0 = rows[0][0] if rows else 0.0
    data = {"t": [row[0] - t0 for row in rows]}
    for m in motors:
        for f in ("target_rads", "actual_rads", "pwm", "error", "ff", "iterm", "pos_rad"):
            k = f"{m}_{f}"
            if k in col:
                data[k] = [row[col[k]] if col[k] < len(row) else float("nan") for row in rows]
    return motors, data, t0


def summarise(motors, data, pwm_max, radius):
    t = data["t"]
    out = {}
    print(f"\n    {len(t)} samples over {t[-1] - t[0] if t else 0:.1f} s "
          f"({(len(t) - 1) / (t[-1] - t[0]) if len(t) > 1 and t[-1] > t[0] else 0:.1f} Hz)")
    print("\n    motor          RMS err   sat %   mismatch %   distance")
    for m in motors:
        tg, ac, pw = data[f"{m}_target_rads"], data[f"{m}_actual_rads"], data[f"{m}_pwm"]
        moving = [(a - b) ** 2 for a, b in zip(ac, tg) if abs(b) > 0.05]
        rms = math.sqrt(sum(moving) / len(moving)) if moving else float("nan")
        sat = 100.0 * sum(1 for p in pw if abs(p) >= 0.98 * pwm_max) / len(pw)
        mism = [1 for a, b in zip(ac, tg) if abs(b) > 0.2 and a * b < 0]
        mis = 100.0 * len(mism) / max(1, sum(1 for b in tg if abs(b) > 0.2))
        dist = sum(abs(ac[k]) * (t[k] - t[k - 1]) for k in range(1, len(t)))
        dist_s = f"{dist:7.2f} rad" + (f" = {dist * radius:.2f} m" if radius else "")
        print(f"    {m:<12} {rms:9.3f}   {sat:5.1f}   {mis:10.1f}   {dist_s}")
        out[m] = dict(rms=rms, sat=sat, mismatch=mis, dist_rad=dist)
        if sat > 10:
            print(f"      ! {m} saturates {sat:.0f} % of the time: not enough PWM for what was asked")
        if mis > 5:
            print(f"      ! {m} turns against its target {mis:.0f} % of the time: check motor_dir / encoder_dir")
    return out


def plot(path, motors, data, meta, t0):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n    (no matplotlib: sudo apt install python3-matplotlib for the plot)")
        return None
    n = len(motors)
    fig, axes = plt.subplots(n, 2, figsize=(12, 2.6 * n), sharex=True, squeeze=False)
    t = data["t"]
    marks = [s.get("t", 0) - t0 for s in (meta or {}).get("steps", [])]
    for i, m in enumerate(motors):
        a, b = axes[i]
        a.plot(t, data[f"{m}_target_rads"], color="#888888", lw=1.2, label="target")
        a.plot(t, data[f"{m}_actual_rads"], color="#1f5fbf", lw=1.0, label="actual")
        a.set_ylabel(f"{m}\nrad/s")
        b.plot(t, data[f"{m}_pwm"], color="#c0392b", lw=0.9, label="pwm")
        if f"{m}_ff" in data:
            b.plot(t, data[f"{m}_ff"], color="#27ae60", lw=0.8, label="feedforward")
            b.plot(t, data[f"{m}_iterm"], color="#8e44ad", lw=0.8, label="I term")
        for x in marks:
            a.axvline(x, color="#cccccc", lw=0.6, zorder=0)
            b.axvline(x, color="#cccccc", lw=0.6, zorder=0)
        if i == 0:
            a.legend(loc="upper right", fontsize=8)
            b.legend(loc="upper right", fontsize=8)
        a.grid(alpha=0.3)
        b.grid(alpha=0.3)
    axes[-1][0].set_xlabel("time (s)")
    axes[-1][1].set_xlabel("time (s)")
    fig.suptitle(os.path.basename(path), fontsize=10)
    fig.tight_layout()
    out = path[:-4] + "_plot.png"
    fig.savefig(out, dpi=110)
    print(f"\n    plot -> {out}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--pwm-max", type=float, default=None, help="default: from the .json sidecar, else 255")
    ap.add_argument("--radius", type=float, default=None, help="wheel radius in m, to print metres")
    ap.add_argument("--no-plot", action="store_true")
    args = ap.parse_args()
    meta = None
    side = args.csv[:-4] + ".json"
    if os.path.exists(side):
        meta = json.load(open(side))
    pwm_max = args.pwm_max or (meta or {}).get("pwm_max", 255)
    motors, data, t0 = load(args.csv)
    if not motors:
        print("no <motor>_target_rads columns: is this a raw-mode CSV? Open it in a spreadsheet instead.")
        return 1
    print(f"\n  {args.csv}" + (f"   ({meta.get('test')} test)" if meta else ""))
    summarise(motors, data, pwm_max, args.radius)
    if not args.no_plot:
        plot(args.csv, motors, data, meta, t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
