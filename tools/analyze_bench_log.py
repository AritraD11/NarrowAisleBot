#!/usr/bin/env python3
"""
NarrowAisleBot — bench/ground telemetry analyzer
==================================================
Turns one raw telemetry CSV (the 13+ column format written by the ESP32's
<L1>/<L2> serial telemetry and recorded by phone_dashboard.py or
nab_pid_logger.py) into a markdown analysis report plus two plots, using
the same checks applied by hand to every CSV reviewed in this project:

  - RMS tracking error per motor, absolute and as % of peak commanded
  - PWM saturation % and headroom
  - Direction-sign mismatch count (tgt/act opposite sign at speed —
    the tell for a MOTOR_DIR_SIGN/ENC_DIR_SIGN fault)
  - Diagonal-pair deviation (FR-RL, FL-RR), computed ONLY over rows where
    both wheels are commanded the same sign — rotation commands legitimately
    put diagonal pairs at opposite sign and will otherwise produce a false
    alarm (this exact mistake was made and corrected once already on this
    project — see docs/Research_Journal.md Part XVI 16.2)
  - Sample-rate / gap check (drop-outs, pauses in the recording)
  - Embedded-timestamp sanity: does pi_time_s decode to a plausible date,
    and does it match the filename (the Pi has no battery-backed RTC —
    Research_Journal.md Part XVI 16.4)

USAGE
-----
    ./tools/analyze_bench_log.py data/bench_logs/bench/run_XXXXXXXX_XXXXXX.csv

Writes, next to an `analysis/` folder beside the input CSV:
    analysis/<name>.md              the report
    analysis/<name>_tracking.png    target vs actual, all 4 motors
    analysis/<name>_error_pwm.png   error + PWM dual-axis, all 4 motors

No dependency beyond pandas/numpy/matplotlib.
"""

import argparse
import os
import sys
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MOTORS = ["FR", "FL", "RR", "RL"]
COLORS = {"FR": "#3b82f6", "FL": "#10b981", "RR": "#f59e0b", "RL": "#ef4444"}
PWM_MAX = 255
PWM_SAT = 230
IST = timezone(timedelta(hours=5, minutes=30))


def load(path):
    df = pd.read_csv(path)
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["time"] = df["pi_time_s"] - df["pi_time_s"].iloc[0]
    for m in MOTORS:
        df[f"{m}_error"] = df[f"{m}_actual_rads"] - df[f"{m}_target_rads"]
    return df


def gaps(df, threshold=0.3):
    dt = np.diff(df["time"].values)
    idx = np.where(dt > threshold)[0]
    return [(df["time"].values[i], dt[i]) for i in idx]


def diagonal_rms(df, a, b):
    """RMS of act[a]-act[b], restricted to rows where a and b are commanded
    the same sign (or either is ~0) -- excludes rotation commands, where
    a diagonal pair legitimately carries opposite-sign targets."""
    ta, tb = df[f"{a}_target_rads"], df[f"{b}_target_rads"]
    mask = (ta * tb) >= 0
    d = df.loc[mask, f"{a}_actual_rads"] - df.loc[mask, f"{b}_actual_rads"]
    return float(np.sqrt((d ** 2).mean())) if mask.any() else float("nan"), int(mask.sum()), int((~mask).sum())


def sign_mismatches(df, m, tgt_floor=0.3, act_floor=0.15):
    tgt, act = df[f"{m}_target_rads"], df[f"{m}_actual_rads"]
    bad = (tgt.abs() > tgt_floor) & (np.sign(tgt) != np.sign(act)) & (act.abs() > act_floor)
    return int(bad.sum())


def decode_timestamp(pi_time_s):
    u = datetime.fromtimestamp(pi_time_s, tz=timezone.utc)
    return u.astimezone(IST)


def metrics(df, path):
    T = df["time"].values
    dur = T[-1] - T[0]
    fs = len(df) / dur if dur > 0 else float("nan")

    rows = []
    for m in MOTORS:
        err = df[f"{m}_error"].values
        rms = float(np.sqrt(np.nanmean(err ** 2)))
        peak = float(df[f"{m}_target_rads"].abs().max())
        pct = 100.0 * rms / peak if peak > 1e-6 else float("nan")
        pwm = df[f"{m}_pwm"].values
        sat_pct = 100.0 * (np.abs(pwm) >= PWM_SAT).mean()
        pwm_peak = float(np.abs(pwm).max())
        mismatches = sign_mismatches(df, m)
        rows.append(dict(motor=m, rms=rms, peak=peak, pct=pct,
                          sat_pct=sat_pct, pwm_peak=pwm_peak, mismatches=mismatches))

    fr_rl_rms, fr_rl_n, fr_rl_excl = diagonal_rms(df, "FR", "RL")
    fl_rr_rms, fl_rr_n, fl_rr_excl = diagonal_rms(df, "FL", "RR")

    gap_list = gaps(df)

    fname = os.path.basename(path)
    ts0 = df["pi_time_s"].iloc[0]
    decoded = decode_timestamp(ts0)
    # does the filename encode a timestamp we can cross-check?
    filename_ts = None
    stem = fname.replace(".csv", "")
    parts = stem.split("_")
    if len(parts) >= 3:
        try:
            filename_ts = datetime.strptime(parts[-2] + parts[-1], "%Y%m%d%H%M%S").replace(tzinfo=IST)
        except ValueError:
            filename_ts = None
    clock_ok = None
    if filename_ts is not None:
        clock_ok = abs((decoded - filename_ts).total_seconds()) < 5

    return dict(
        fname=fname, samples=len(df), duration=dur, fs=fs,
        rows=rows, fr_rl_rms=fr_rl_rms, fr_rl_n=fr_rl_n, fr_rl_excl=fr_rl_excl,
        fl_rr_rms=fl_rr_rms, fl_rr_n=fl_rr_n, fl_rr_excl=fl_rr_excl,
        gaps=gap_list, decoded=decoded, filename_ts=filename_ts, clock_ok=clock_ok,
    )


def plot_tracking(df, m_out, title):
    fig, axes = plt.subplots(4, 1, figsize=(13, 11), sharex=True)
    fig.suptitle(title, fontweight="bold")
    T = df["time"].values
    for ax, m in zip(axes, MOTORS):
        col = COLORS[m]
        tgt = df[f"{m}_target_rads"].values
        act = df[f"{m}_actual_rads"].values
        err = act - tgt
        rms = np.sqrt(np.nanmean(err ** 2))
        peak = np.abs(tgt).max()
        pct = 100 * rms / peak if peak > 1e-6 else float("nan")
        ax.plot(T, tgt, "--", color=col, lw=1.0, alpha=0.6, label="target")
        ax.plot(T, act, "-", color=col, lw=0.9, label="actual")
        ax.axhline(0, color="gray", lw=0.5, ls=":")
        ax.set_title(f"{m}  RMS={rms:.3f} rad/s ({pct:.1f}% of peak)",
                     fontsize=10, color=col, fontweight="bold")
        ax.set_ylabel("rad/s")
        ax.legend(loc="upper right", fontsize=8)
    axes[-1].set_xlabel("time (s)")
    plt.tight_layout()
    plt.savefig(m_out, dpi=130)
    plt.close(fig)


def plot_error_pwm(df, m_out, title):
    fig, axes = plt.subplots(4, 1, figsize=(13, 11), sharex=True)
    fig.suptitle(title, fontweight="bold")
    T = df["time"].values
    for ax, m in zip(axes, MOTORS):
        col = COLORS[m]
        err = df[f"{m}_error"].values
        pwm = df[f"{m}_pwm"].values
        sat_mask = np.abs(pwm) >= PWM_SAT
        e_min, e_max = float(np.nanmin(err)), float(np.nanmax(err))
        pad = max(abs(e_max - e_min) * 0.1, 0.05)
        ylim = (e_min - pad, e_max + pad)
        ax.fill_between(T, ylim[0], ylim[1], where=sat_mask, alpha=0.10, color="#dc2626")
        ax.plot(T, err, "-", color=col, lw=0.9)
        ax.axhline(0, color="gray", lw=0.5, ls=":")
        ax.set_ylim(ylim)
        ax.set_ylabel("error (rad/s)", color=col)
        ax2 = ax.twinx()
        ax2.plot(T, pwm, "-", color="#9ca3af", lw=0.5, alpha=0.5)
        ax2.axhline(PWM_SAT, color="#dc2626", lw=0.6, ls="--", alpha=0.5)
        ax2.axhline(-PWM_SAT, color="#dc2626", lw=0.6, ls="--", alpha=0.5)
        ax2.set_ylim(-PWM_MAX - 20, PWM_MAX + 20)
        ax2.set_ylabel("PWM", color="#6b7280")
        sat_pct = 100 * sat_mask.mean()
        ax.set_title(f"{m}  PWM sat={sat_pct:.1f}%", fontsize=10, color=col, fontweight="bold")
    axes[-1].set_xlabel("time (s)")
    plt.tight_layout()
    plt.savefig(m_out, dpi=130)
    plt.close(fig)


def write_report(md_path, csv_relpath, plot1_name, plot2_name, m, notes):
    lines = []
    lines.append(f"# Bench log analysis — `{m['fname']}`\n")
    lines.append(f"Source: [`{csv_relpath}`]({os.path.basename(csv_relpath)})\n")
    lines.append("## Capture\n")
    lines.append(f"- Samples: {m['samples']}")
    lines.append(f"- Duration: {m['duration']:.2f} s")
    lines.append(f"- Sample rate: {m['fs']:.1f} Hz")
    lines.append(f"- Embedded timestamp: `{m['decoded'].strftime('%Y-%m-%d %H:%M:%S %Z')}`")
    if m['filename_ts'] is not None:
        status = "matches filename" if m['clock_ok'] else "**does NOT match filename — clock may have been wrong at record time**"
        lines.append(f"- Filename timestamp check: {status}")
    if m['gaps']:
        lines.append(f"- ⚠ {len(m['gaps'])} gap(s) > 0.3 s in the recording:")
        for t, dt in m['gaps']:
            lines.append(f"  - at t={t:.2f}s, gap={dt:.2f}s")
    else:
        lines.append("- No gaps > 0.3 s (continuous capture)")
    lines.append("")

    lines.append("## Per-motor tracking\n")
    lines.append("| Motor | RMS error (rad/s) | % of peak | PWM sat % | PWM peak | Sign mismatches |")
    lines.append("|---|---|---|---|---|---|")
    for r in m["rows"]:
        lines.append(f"| {r['motor']} | {r['rms']:.3f} | {r['pct']:.1f}% | {r['sat_pct']:.1f}% | "
                      f"{r['pwm_peak']:.0f}/{PWM_MAX} | {r['mismatches']} |")
    lines.append("")

    lines.append("## Diagonal-pair deviation (rotation-excluded)\n")
    lines.append(f"Computed only over samples where both wheels of the pair are commanded the same sign "
                  f"(excludes rotation, where FR/RL and FL/RR are *supposed* to be opposite-sign — "
                  f"see Research_Journal.md Part XVI §16.2 for why this exclusion matters).\n")
    lines.append(f"- FR−RL RMS: {m['fr_rl_rms']:.3f} rad/s  ({m['fr_rl_n']} samples used, {m['fr_rl_excl']} excluded as rotation)")
    lines.append(f"- FL−RR RMS: {m['fl_rr_rms']:.3f} rad/s  ({m['fl_rr_n']} samples used, {m['fl_rr_excl']} excluded as rotation)")
    lines.append("")

    lines.append("## Plots\n")
    lines.append(f"![tracking]({plot1_name})\n")
    lines.append(f"![error and PWM]({plot2_name})\n")

    if notes:
        lines.append("## Notes\n")
        for n in notes:
            lines.append(f"- {n}")
        lines.append("")

    with open(md_path, "w") as fh:
        fh.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="path to the telemetry CSV")
    ap.add_argument("--title", default=None, help="plot title override")
    ap.add_argument("--note", action="append", default=[], help="extra note line for the report (repeatable)")
    args = ap.parse_args()

    csv_path = args.csv
    out_dir = os.path.join(os.path.dirname(csv_path), "analysis")
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.basename(csv_path).replace(".csv", "")

    df = load(csv_path)
    m = metrics(df, csv_path)

    title = args.title or f"{m['fname']} — {m['decoded'].strftime('%Y-%m-%d %H:%M IST')}"
    plot1 = os.path.join(out_dir, f"{stem}_tracking.png")
    plot2 = os.path.join(out_dir, f"{stem}_error_pwm.png")
    plot_tracking(df, plot1, title)
    plot_error_pwm(df, plot2, title)

    md = os.path.join(out_dir, f"{stem}.md")
    write_report(md, os.path.relpath(csv_path, out_dir),
                 os.path.basename(plot1), os.path.basename(plot2), m, args.note)

    print(f"Report: {md}")
    print(f"Plots:  {plot1}")
    print(f"        {plot2}")

    worst = max(m["rows"], key=lambda r: r["pct"])
    print(f"\nWorst motor: {worst['motor']}  RMS={worst['rms']:.3f} rad/s ({worst['pct']:.1f}% of peak)")
    print(f"Max sign mismatches: {max(r['mismatches'] for r in m['rows'])}")
    if m["gaps"]:
        print(f"⚠ {len(m['gaps'])} timing gap(s) > 0.3s")
    if m["filename_ts"] is not None and not m["clock_ok"]:
        print("⚠ embedded timestamp does not match filename — check clock reliability")


if __name__ == "__main__":
    main()
