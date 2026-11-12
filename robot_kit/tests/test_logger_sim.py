#!/usr/bin/env python3
"""Encoder logger, end to end, against the firmware simulator:

    python3 tests/test_logger_sim.py          (about 90 s, real time)

Builds tools/firmware_sim for robot_config.yaml, runs it on a pseudo
terminal, and drives tools/encoder_logger.py at it exactly as you would at a
real board. Because the simulator's motors have known constants, the numbers
the logger fits can be checked against the truth:

  plant      Kff within 8 % and tau within 30 % of the simulated motor
  staircase  Kff within 8 %, Kstat within 4 PWM
  steps      CSV has the documented header; every setpoint reached
  record     ~50 Hz of rows for the requested duration
  raw        logs the board's CSV with no protocol, adds rad and rad/s
  sweep      one CSV per gain set
"""
import csv
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

KIT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
LOGGER = os.path.join(KIT, "tools", "encoder_logger.py")
SIMDIR = os.path.join(KIT, "tools", "firmware_sim")
FAILS = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


subprocess.run([sys.executable, os.path.join(KIT, "generate.py")], check=True, capture_output=True)
subprocess.run(["make", "-s", "-C", SIMDIR], check=True)
sim = subprocess.Popen([os.path.join(SIMDIR, "sim"), "--pty"], stdout=subprocess.PIPE, text=True)
port = sim.stdout.readline().split()[1]
plant = dict(kv.split("=") for kv in sim.stdout.readline().split()[1:4])
kff_true, kstat_true, tau_true = (float(plant[k]) for k in ("kff", "kstat", "tau"))
truth = {"left": kff_true * 0.97, "right": kff_true * 1.00}   # sim.cpp spreads motors by 3 %
print(f"simulator on {port}: Kff {truth}, Kstat {kstat_true}, tau {tau_true}")

logdir = tempfile.mkdtemp()


def logger(*a, timeout=240):
    cmd = [sys.executable, LOGGER, "--port", port, "--yes", "--open-delay", "0.3",
           "--logdir", logdir, *a]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-3000:])
    return r


def newest(prefix):
    files = sorted(glob.glob(os.path.join(logdir, prefix + "_*.csv")), key=os.path.getmtime)
    return files[-1] if files else None


try:
    print("\nplant")
    r = logger("--test", "plant", "--plant-pwm", "90,150", "--plant-hold", "1.5")
    check(r.returncode == 0, "exit 0")
    for m in ("left", "right"):
        hit = re.search(rf"    {m}: Kff\s+([\d.]+)\s+Kstat\s+([-\d.]+)\s+Ki\s+([\d.]+)\s+tau ([\d.]+) s.*filter adds ([-+\d.]+) s", r.stdout)
        check(bool(hit), f"{m}: Kff / Kstat / Ki / tau printed")
        if hit:
            kff, tau = float(hit.group(1)), float(hit.group(4))
            check(abs(kff - truth[m]) / truth[m] < 0.08, f"{m}: Kff {kff:.2f} vs true {truth[m]:.2f}")
            check(abs(tau - tau_true) / tau_true < 0.30, f"{m}: tau {tau:.3f} s vs true {tau_true:.3f} s")
            print(f"       (the firmware's velocity filter adds {hit.group(5)} s on top, reported separately)")
    path = newest("plant")
    meta = json.load(open(path[:-4] + ".json"))
    check(meta["motors"] == ["left", "right"] and len(meta["steps"]) == 4, "sidecar JSON lists motors and 4 steps")

    print("\nstaircase")
    r = logger("--test", "staircase", "--min-pwm", "2", "--max-pwm", "50", "--pwm-step", "4", "--dwell", "0.9")
    check(r.returncode == 0, "exit 0")
    for m in ("left", "right"):
        hit = re.search(rf"    {m}: Kff\s+([\d.]+) PWM/\(rad/s\)\s+Kstat\s+([-\d.]+) PWM", r.stdout)
        check(bool(hit), f"{m}: fit printed")
        if hit:
            kff, kstat = float(hit.group(1)), float(hit.group(2))
            check(abs(kff - truth[m]) / truth[m] < 0.08, f"{m}: Kff {kff:.2f} vs true {truth[m]:.2f}")
            check(abs(kstat - kstat_true) < 4.0, f"{m}: Kstat {kstat:.1f} vs true {kstat_true:.1f}")
    check("<F," in r.stdout and "<K," in r.stdout, "prints the live <F,...> and <K,...> commands")

    print("\nsteps")
    # Feedforward from the staircase fit, as the manual's procedure does it.
    r = logger("--test", "steps", "--setpoints", "2,5", "--dwell", "1.5", "--rest", "0.8",
               "--kff", f"{truth['left']:.2f},{truth['right']:.2f}", "--kstat", f"{kstat_true:.2f},{kstat_true:.2f}",
               "--gains", "20,100,0")
    check(r.returncode == 0, "exit 0")
    path = newest("steps")
    with open(path) as fh:
        rows = list(csv.reader(fh))
    want = ["pi_time_s", "mcu_ms", "left_target_rads", "left_actual_rads", "left_pwm",
            "right_target_rads", "right_actual_rads", "right_pwm", "left_error", "left_ff",
            "left_iterm", "left_pos_rad", "right_error", "right_ff", "right_iterm", "right_pos_rad"]
    check(rows[0] == want, "CSV header is the documented one")
    check(all(len(x) == len(want) for x in rows[1:]), "every row has every column")
    errs = [float(x) for x in re.findall(r"\n\s+[\d.]+\s+(?:left|right)\s+[\d.]+\s+([-+][\d.]+)", r.stdout)]
    check(len(errs) == 4 and all(abs(e) < 0.10 for e in errs), f"steady-state errors {errs}")
    check("[OK,FF" in r.stdout, "--kff was applied live and acknowledged")

    print("\nsweep")
    r = logger("--test", "sweep", "--setpoints", "3", "--dwell", "1.2", "--rest", "0.6",
               "--gains", "10,50,0 20,80,0")
    check(r.returncode == 0 and "SWEEP SUMMARY" in r.stdout, "summary printed")
    check(len(glob.glob(os.path.join(logdir, "sweep_*.csv"))) == 2, "one CSV per gain set")

    print("\nrecord")
    r = logger("--test", "record", "--duration", "3", "--hz", "50")
    path = newest("record")
    n = sum(1 for _ in open(path)) - 1 if path else 0
    check(r.returncode == 0 and 120 <= n <= 160, f"{n} rows in 3 s at 50 Hz")

    print("\nraw (no protocol assumed)")
    cols = "t_ms,lt,la,lp,rt,ra,rp"
    r = logger("--test", "raw", "--send", "<L1,25>", "--duration", "2", "--columns", cols,
               "--ticks", "la:1,ra:1", "--time-col", "t_ms")
    path = newest("raw")
    with open(path) as fh:
        rows = list(csv.reader(fh))
    check(r.returncode == 0 and rows[0][:8] == ["pi_time_s"] + cols.split(","), "header = pi_time_s + given columns")
    check("la_rads" in rows[0] and "ra_rad" in rows[0], "derived rad and rad/s columns added")
    check(35 <= len(rows) - 1 <= 60, f"{len(rows) - 1} rows in 2 s at 25 Hz")
finally:
    sim.terminate()
    sim.wait(5)

print()
if FAILS:
    print(f"{len(FAILS)} FAILED")
    sys.exit(1)
print("all encoder logger checks passed")
