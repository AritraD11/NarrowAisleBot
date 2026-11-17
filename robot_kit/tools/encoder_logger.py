#!/usr/bin/env python3
"""
encoder_logger.py - log encoder data from the microcontroller and run the
PID calibration tests. Runs on the Pi (or any PC with the board plugged in).
No ROS needed: stop the base stack first, the serial port can only have one
reader (sudo systemctl stop robot.service).

    >>> WHEELS IN THE AIR for plant, staircase, steps and sweep. <<<

The robot kit firmware (firmware/robot_mcu) speaks the protocol these tests
need. If your microcontroller runs your OWN firmware, use --test raw: it logs
whatever CSV your board prints, timestamps it on the Pi, and can turn tick
counts into rad/s for you.

TESTS
  plant      Open-loop PWM steps, PID bypassed. Measures each motor's time
             constant tau and gain K, and prints the Kff, Ki and Kp they
             imply. Run this FIRST.
  staircase  PWM raised in small steps from rest. Fits Kff (slope) and
             Kstat (breakaway) per motor by least squares. Run once in the
             air, once on the floor: the difference is the ground load.
             On the floor this DRIVES. --mode rotate spins in place instead.
  steps      Closed-loop velocity steps. Rise, overshoot, settling time,
             steady-state error, PWM saturation: the verdict on a gain set.
  sweep      steps, repeated for several gain sets. One CSV each.
  record     Log telemetry for --duration seconds while nothing else drives
             (use the ROS telemetry logger to log while driving under ROS).
  raw        Log any CSV the board prints. For non-kit firmware.

EXAMPLES
  ./encoder_logger.py --test plant
  ./encoder_logger.py --test plant --only left           # one wheel at a time
  ./encoder_logger.py --test staircase --max-pwm 90
  ./encoder_logger.py --test steps --setpoints 1,2,4 --kff 16.1,16.6 --kstat 7.7,7.7
  ./encoder_logger.py --test sweep --gains "20,120,0 30,120,0 20,200,0"
  ./encoder_logger.py --test raw --port /dev/ttyACM0 --baud 115200 \\
        --columns t_ms,left_ticks,right_ticks --ticks left_ticks:1320,right_ticks:1320 \\
        --time-col t_ms --duration 30

Every run writes <logdir>/<test>_<timestamp>.csv plus a .json beside it with
what was commanded and when, so tools/analyze_log.py can redo the maths later.

Ctrl-C at any point sends <S>, <L0>, <E0>: motors stop. So does a crash.
"""

import argparse
import csv
import json
import math
import os
import signal
import subprocess
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KIT, "ros2", "robot_base"))

from robot_base import protocol as P  # noqa: E402
from robot_base.protocol import SerialLink  # noqa: E402

try:
    from robot_base.robot_model import load_config, ConfigError  # noqa: E402
except Exception:  # pragma: no cover  (PyYAML missing)
    load_config, ConfigError = None, Exception


# ══════════════════════════════════════════════════════════════════════
#  Small numerical helpers (pure Python, so this runs with pyserial only)
# ══════════════════════════════════════════════════════════════════════

def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def window(series, t0, t1):
    return [v for t, v in series if t0 <= t <= t1]


def estimate_tau(series, t_step, v_final):
    """Time from the step to 63.2 % of the final value (first-order lag),
    interpolated between the two samples either side of the crossing so the
    telemetry period does not round it up. Includes the dead time between
    the command and the first control tick that acts on it (<= 1 tick)."""
    if abs(v_final) < 1e-6:
        return None
    target = 0.632 * v_final
    prev = None
    for t, v in series:
        if t < t_step:
            continue
        if (v_final > 0 and v >= target) or (v_final < 0 and v <= target):
            if prev is not None and v != prev[1]:
                t = prev[0] + (target - prev[1]) * (t - prev[0]) / (v - prev[1])
            return max(0.0, t - t_step)
        prev = (t, v)
    return None


def settling_time(series, t_step, target, band=0.05, hold=0.2):
    """First moment after the step from which the signal stays within
    +/-band*|target| for the rest of THIS step's window."""
    if abs(target) < 1e-6:
        return None
    thr = abs(target) * band
    pts = [(t, v) for t, v in series if t >= t_step]
    for i, (t, _) in enumerate(pts):
        if all(abs(v - target) <= thr for _, v in pts[i:]):
            return (t - t_step) if pts[-1][0] - t >= hold else None
    return None


def centered_rate(series_, half=1):
    """d/dt by a centred difference: (p[k+h] - p[k-h]) / (t[k+h] - t[k-h]).
    Symmetric, so it adds no lag. Used on the wheel ANGLE, which the
    firmware reports unfiltered, to see the motor without the firmware's
    velocity filter in the way."""
    out = []
    for k in range(half, len(series_) - half):
        (t0, p0), (t1, p1) = series_[k - half], series_[k + half]
        if t1 > t0:
            out.append((series_[k][0], (p1 - p0) / (t1 - t0)))
    return out


def ols(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    sx, sy = sum(xs), sum(ys)
    sxx, sxy = sum(x * x for x in xs), sum(x * y for x, y in zip(xs, ys))
    d = n * sxx - sx * sx
    if abs(d) < 1e-12:
        return None
    m = (n * sxy - sx * sy) / d
    return m, (sy - m * sx) / n


# ══════════════════════════════════════════════════════════════════════
#  Setup: who is on the other end of the cable
# ══════════════════════════════════════════════════════════════════════

class Robot:
    """What the tests need to know about the robot, from the firmware's own
    <I> reply first and robot_config.yaml second."""

    def __init__(self, link, cfg):
        self.link = link
        ident = P.read_identity(link)
        cfg_names = [w["name"] for w in cfg["wheels"]] if cfg else None
        if ident["names"]:
            self.names = ident["names"]
            if cfg_names and cfg_names != self.names:
                print(f"  ! firmware says motors {self.names}, robot_config.yaml says {cfg_names}.\n"
                      f"    Using the firmware's. Regenerate and reflash if that is wrong.")
        elif cfg_names:
            self.names = cfg_names
            print("  ! firmware did not report [MOTORS,...]; using robot_config.yaml")
        else:
            raise RuntimeError("cannot tell how many motors there are: the firmware does not "
                               "report [MOTORS,...] and no robot_config.yaml was loaded")
        self.n = len(self.names)
        link.n = self.n
        self.info = ident["info"]
        self.lines = ident["lines"]
        self.pwm_max = 255
        self.vmax = None
        for ln in ident["lines"]:
            if ln.startswith("[LIMITS"):
                for kv in ln.strip("[]").split(",")[1:]:
                    k, _, v = kv.partition("=")
                    if k == "PWM_MAX":
                        self.pwm_max = int(float(v))
                    elif k == "Vmax":
                        self.vmax = float(v)
        if self.vmax is None and cfg:
            self.vmax = float(cfg["mcu"]["max_wheel_speed"])
        if self.vmax is None:
            self.vmax = 5.0
        self.model = cfg["_model"] if cfg and cfg_names == self.names else None


def pattern(robot, mode, only):
    """Per-motor sign for open-loop tests. translate = every wheel forward.
    rotate = the sign each wheel gets for a pure spin, from the kinematics."""
    if mode == "rotate":
        if robot.model is None:
            raise RuntimeError("--mode rotate needs robot_config.yaml matching the firmware")
        signs = robot.model.sign_pattern(0.0, 0.0, 1.0)
    else:
        signs = [1] * robot.n
    if only:
        signs = [s if robot.names[i] in only else 0 for i, s in enumerate(signs)]
    return signs


# ══════════════════════════════════════════════════════════════════════
#  Output
# ══════════════════════════════════════════════════════════════════════

def out_path(args, tag):
    d = os.path.expanduser(args.logdir)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{tag}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")


def write_run(path, robot, rows, meta):
    """rows must already be on the MCU clock (P.align_to_mcu_clock): the
    pi_time_s column is the MCU's sample time expressed on the Pi's clock."""
    ext = any(tel.extended for _, tel in rows)
    header = P.csv_header(robot.names, ext)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for t, tel in rows:
            vals = tel.values if ext else tel.values[:3 * robot.n]
            w.writerow([f"{t:.4f}", tel.mcu_ms] + [f"{v:g}" for v in vals])
    meta = dict(meta, motors=robot.names, firmware=robot.info, pwm_max=robot.pwm_max,
                csv=os.path.basename(path), columns=header, samples=len(rows))
    with open(path[:-4] + ".json", "w") as fh:
        json.dump(meta, fh, indent=2)
    print(f"\n    {len(rows)} samples -> {path}")
    if rows:
        span = rows[-1][0] - rows[0][0]
        print(f"    {span:.1f} s, {len(rows) / span if span > 0 else 0:.1f} Hz achieved")
    return path


def series(rows, i, field):
    return [(t, getattr(tel, field)[i]) for t, tel in rows if getattr(tel, field) is not None]


# ══════════════════════════════════════════════════════════════════════
#  Tests
# ══════════════════════════════════════════════════════════════════════

def hold_pwm(link, robot, signs, pwm, seconds):
    link.send(P.cmd_pwm([s * pwm for s in signs]), 0)
    time.sleep(seconds)


def hold_velocity(link, robot, signs, w, seconds):
    """Resend the target at 20 Hz so the firmware watchdog stays fed, the
    same way the ROS bridge feeds it."""
    cmd = P.cmd_velocity([s * w for s in signs])
    t_end = time.time() + seconds
    while time.time() < t_end:
        link.send(cmd, 0)
        time.sleep(0.05)


def open_loop_prelude(link, hz):
    link.send("<E1>")
    link.send("<W0>")          # <M> holds longer than the watchdog
    link.send("<Y0>")          # trips assume a velocity target; open loop has none
    link.send(f"<L2,{hz}>")


def open_loop_postlude(link, robot):
    link.send(P.cmd_pwm([0] * robot.n))
    time.sleep(0.5)
    rows = P.align_to_mcu_clock(link.stop_collect())
    link.send("<L0>")
    link.send("<W1>")
    link.send("<Y1>")
    return rows


def test_plant(link, robot, args):
    print("\n=== PLANT IDENTIFICATION (open loop, PID bypassed) ===")
    signs = pattern(robot, args.mode, args.only)
    levels = args.plant_pwm or [int(robot.pwm_max * f) for f in (0.30, 0.45, 0.65)]
    open_loop_prelude(link, 50)
    link.start_collect()
    marks = []
    t0 = time.time()
    for pwm in levels:
        for sgn in (+1, -1):
            hold_pwm(link, robot, signs, 0, 1.5)
            t_step = time.time()
            link.send(P.cmd_pwm([sgn * s * pwm for s in signs]), 0)
            marks.append((t_step, sgn * pwm))
            print(f"    step -> PWM {sgn * pwm:+5d}   ({time.time() - t0:5.1f} s)")
            time.sleep(args.plant_hold)
    rows = open_loop_postlude(link, robot)
    path = write_run(out_path(args, "plant"), robot, rows,
                     dict(test="plant", mode=args.mode, signs=signs, hold_s=args.plant_hold,
                          steps=[{"t": t, "pwm": p} for t, p in marks]))

    print("\n    tau(angle) is the motor itself, from the unfiltered wheel angle.")
    print("    tau(filtered) is what the PID sees, through the firmware's velocity filter.")
    print("\n    motor         PWM    v_ss(rad/s)   K=v/pwm   tau(angle)  tau(filtered)")
    result = {}
    for i, m in enumerate(robot.names):
        if signs[i] == 0:
            continue
        act = series(rows, i, "actual")
        rate = centered_rate(series(rows, i, "pos_rad"))
        ks, taus, ftaus, pts = [], [], [], []
        for t_step, pwm in marks:
            p = pwm * signs[i]
            v_ss = mean(window(act, t_step + args.plant_hold - 0.5, t_step + args.plant_hold))
            if math.isnan(v_ss) or abs(v_ss) < 0.05:
                print(f"    {m:<12} {p:+5d}   no motion")
                continue
            ftau = estimate_tau(act, t_step, v_ss)
            tau = estimate_tau(rate, t_step, v_ss) if rate else None
            ks.append(abs(v_ss / p))
            pts.append((abs(p), abs(v_ss)))
            if tau:
                taus.append(tau)
            if ftau:
                ftaus.append(ftau)
            print(f"    {m:<12} {p:+5d}   {v_ss:11.3f}   {abs(v_ss / p):8.5f}   "
                  f"{tau if tau else float('nan'):9.3f}  {ftau if ftau else float('nan'):12.3f}")
        result[m] = (ks, taus, pts, ftaus)

    print("\n    === WHAT TO DO WITH THIS (lambda = %.2f s) ===" % args.lam)
    print("    Kff = PWM per rad/s (line fit through the steps). Ki = Kff / lambda.")
    print("    Kp = tau * Ki is the textbook start; verify it with --test sweep.")
    for m, (ks, taus, pts, ftaus) in result.items():
        if not ks:
            print(f"    {m}: no usable steps. Check the wiring, motor_dir, and that the "
                  f"PWM levels are above breakaway.")
            continue
        fit = ols([p for p, _ in pts], [v for _, v in pts]) if len(pts) >= 2 else None
        if fit and fit[0] > 0:
            kff, kstat = 1.0 / fit[0], -fit[1] / fit[0]
        else:
            kff, kstat = 1.0 / mean(ks), 0.0
        tau = mean(taus) if taus else None
        ki = kff / args.lam
        line = f"    {m}: Kff {kff:6.2f}  Kstat {kstat:5.1f}  Ki {ki:6.1f}"
        if tau:
            line += f"  tau {tau:.3f} s  Kp {tau * ki:6.2f}"
            if ftaus:
                line += f"   (filter adds {mean(ftaus) - tau:+.3f} s)"
        else:
            line += "  tau not resolved (longer --plant-hold, or 50 Hz telemetry)"
        print(line)
    print("\n    Live:  <F,...> <K,...> <G,kp,ki,kd>.  Permanent: robot_config.yaml "
          "mcu.kff / kstat / pid, then generate.py and reflash.")
    return path


def test_staircase(link, robot, args):
    print("\n=== STATIC FRICTION STAIRCASE (open loop) ===")
    signs = pattern(robot, args.mode, args.only)
    lo = args.min_pwm if args.min_pwm is not None else max(1, int(robot.pwm_max * 0.01))
    hi = args.max_pwm if args.max_pwm is not None else int(robot.pwm_max * 0.35)
    step = args.pwm_step if args.pwm_step is not None else max(1, int(robot.pwm_max * 0.01))
    print(f"    PWM {lo} -> {hi} step {step}, {args.dwell:.1f} s each, mode {args.mode}")
    open_loop_prelude(link, 50)
    link.start_collect()
    marks = []
    for pwm in range(lo, hi + 1, step):
        hold_pwm(link, robot, signs, 0, 0.6)
        t_step = time.time()
        link.send(P.cmd_pwm([s * pwm for s in signs]), 0)
        marks.append((t_step, pwm))
        time.sleep(args.dwell)
        print(f"    PWM {pwm:4d}", end="\r", flush=True)
    rows = open_loop_postlude(link, robot)
    path = write_run(out_path(args, "staircase"), robot, rows,
                     dict(test="staircase", mode=args.mode, signs=signs, dwell_s=args.dwell,
                          steps=[{"t": t, "pwm": p} for t, p in marks]))

    active = [i for i in range(robot.n) if signs[i] != 0]
    print("\n     PWM " + "".join(f"{robot.names[i]:>12}" for i in active))
    table = {i: [] for i in active}
    for t_step, pwm in marks:
        cells = []
        for i in active:
            v = mean(window(series(rows, i, "actual"), t_step + args.dwell - 0.4, t_step + args.dwell))
            table[i].append((pwm, v * signs[i]))
            cells.append(f"{v:12.3f}" if not math.isnan(v) else f"{'-':>12}")
        print(f"    {pwm:4d} " + "".join(cells))

    print("\n    === LINE FIT  v = m*pwm + c   ->   Kff = 1/m,  Kstat = -c/m ===")
    kff, kstat = {}, {}
    for i in active:
        moving = [(p, v) for p, v in table[i] if not math.isnan(v) and v > 0.05]
        if len(moving) < 3:
            print(f"    {robot.names[i]}: only {len(moving)} moving points. Raise --max-pwm.")
            continue
        fit = ols([p for p, _ in moving], [v for _, v in moving])
        if not fit or fit[0] <= 0:
            print(f"    {robot.names[i]}: could not fit a positive slope.")
            continue
        kff[i], kstat[i] = 1.0 / fit[0], -fit[1] / fit[0]
        first = moving[0][0]
        print(f"    {robot.names[i]}: Kff {kff[i]:7.2f} PWM/(rad/s)   Kstat {kstat[i]:6.1f} PWM   "
              f"({len(moving)} points, first motion at PWM {first})")
    if len(kff) == len(active) == robot.n:
        print(f"\n    Live:  <F,{','.join(f'{kff[i]:.2f}' for i in range(robot.n))}>")
        print(f"           <K,{','.join(f'{max(0.0, kstat[i]):.1f}' for i in range(robot.n))}>")
        print("    Permanent: mcu.kff / mcu.kstat in robot_config.yaml, generate.py, reflash.")
    if args.mode == "rotate":
        print("    (rotate mode: each wheel still rolls on the floor, but rollers and tyres are\n"
              "     loaded at a slightly different angle than in a straight run.)")
    return path


def test_steps(link, robot, args, gains=None, tag="steps"):
    label = f"  Kp={gains[0]:g} Ki={gains[1]:g} Kd={gains[2]:g}" if gains else ""
    print(f"\n=== CLOSED-LOOP STEP RESPONSE{label} ===")
    signs = pattern(robot, "translate", args.only)
    setpoints = args.setpoints or [round(robot.vmax * f, 2) for f in (0.2, 0.4, 0.6, 0.85)]
    link.send("<E1>")
    link.send("<W1>")
    link.send("<Y1>")
    apply_feedforward(link, robot, args)
    if gains:
        link.send(P.cmd_gains(*gains))
    if args.no_slew:
        link.send("<A,0>")
        print("    slew limiter OFF: a true step into the controller")
    link.send("<L2,50>")
    link.start_collect()
    marks = []
    for sp in setpoints:
        hold_velocity(link, robot, signs, 0.0, args.rest)
        t_step = time.time()
        hold_velocity(link, robot, signs, sp, args.dwell)
        marks.append((t_step, sp))
        print(f"    setpoint {sp:.2f} rad/s")
    hold_velocity(link, robot, signs, 0.0, 1.0)
    rows = P.align_to_mcu_clock(link.stop_collect())
    link.send("<L0>")
    path = write_run(out_path(args, tag), robot, rows,
                     dict(test="steps", gains=gains, signs=signs, dwell_s=args.dwell,
                          no_slew=args.no_slew, steps=[{"t": t, "target": s} for t, s in marks]))

    sat_level = 0.98 * robot.pwm_max
    print("\n    setpt  motor          ss      err   overshoot  settle(s)  sat%")
    worst = 0.0
    summary = []
    for t_step, sp in marks:
        t_end = t_step + args.dwell
        for i, m in enumerate(robot.names):
            if signs[i] == 0:
                continue
            act = series(rows, i, "actual")
            pwm = series(rows, i, "pwm")
            ss = mean(window(act, t_end - 0.5, t_end))
            pk = max((abs(v) for v in window(act, t_step, t_end)), default=float("nan"))
            st = settling_time([(t, v) for t, v in act if t <= t_end], t_step, sp)
            win = window(pwm, t_step, t_end)
            sat = 100.0 * sum(1 for p in win if abs(p) >= sat_level) / len(win) if win else 0.0
            err = ss - sp
            worst = max(worst, abs(err))
            summary.append(dict(setpoint=sp, motor=m, ss=ss, overshoot=pk - sp, settle=st, sat=sat))
            print(f"    {sp:5.2f}  {m:<12} {ss:6.3f}  {err:+6.3f}  {pk - sp:+9.3f}  "
                  f"{(f'{st:.2f}' if st else 'none'):>9}  {sat:4.0f}")
    print(f"\n    worst steady-state error: {worst:.3f} rad/s")
    if worst > 0.15:
        print("    -> feedforward is off or Ki is too low. Run --test plant and refit.")
    if any(s["sat"] > 20 for s in summary):
        print("    -> PWM saturates on some steps: the top setpoint is beyond what this "
              "motor can hold. Lower max_wheel_speed (manual 9.8).")
    return path, summary


def apply_feedforward(link, robot, args):
    """--kff / --kstat: try fitted values live before making them permanent."""
    for letter, vals in (("F", args.kff), ("K", args.kstat)):
        if vals is None:
            continue
        if len(vals) != robot.n:
            raise RuntimeError(f"--{'kff' if letter == 'F' else 'kstat'} needs {robot.n} values")
        reply = link.query(P.cmd_per_motor(letter, vals), "OK," + ("FF" if letter == "F" else "KSTAT"))
        print(f"    {reply or 'no reply to <' + letter + ',...>'}")


def test_sweep(link, robot, args):
    results = []
    for g in args.gains:
        path, summary = test_steps(link, robot, args, gains=g,
                                   tag=f"sweep_kp{g[0]:g}_ki{g[1]:g}_kd{g[2]:g}")
        results.append((g, path, summary))
        hold_velocity(link, robot, [0] * robot.n, 0.0, 1.5)
    print("\n=== SWEEP SUMMARY ===")
    print("    Kp       Ki       Kd     mean overshoot   mean settle   worst |err|")
    for g, _, s in results:
        ov = mean(x["overshoot"] for x in s)
        st = [x["settle"] for x in s if x["settle"]]
        we = max(abs(x["ss"] - x["setpoint"]) for x in s)
        print(f"    {g[0]:<8g} {g[1]:<8g} {g[2]:<6g} {ov:14.3f}   "
              f"{(mean(st) if st else float('nan')):11.3f}   {we:11.3f}")
    print("\n    Prefer the lowest overshoot with settle under ~0.3 s and no saturation.")
    print("    On NarrowAisleBot the 'textbook' Kp = tau*Ki LOST to the existing Kp on\n"
          "    overshoot in 16 of 16 rows (manual 9.6). Let the sweep decide.")
    return [p for _, p, _ in results]


def bridge_running():
    try:
        out = subprocess.run(["pgrep", "-af", "mcu_bridge"], capture_output=True, text=True).stdout
        return [ln for ln in out.splitlines() if "pgrep" not in ln]
    except FileNotFoundError:
        return []


def test_record(link, robot, args):
    print("\n=== RECORD ===  (Ctrl-C to stop)")
    link.send(f"<L2,{args.hz:g}>")
    link.start_collect()
    t0 = time.time()
    try:
        while args.duration <= 0 or time.time() - t0 < args.duration:
            time.sleep(0.5)
            print(f"\r    {time.time() - t0:6.1f} s   {len(link.rows)} samples", end="", flush=True)
    except KeyboardInterrupt:
        print()
    rows = P.align_to_mcu_clock(link.stop_collect())
    link.send("<L0>")
    return write_run(out_path(args, "record"), robot, rows, dict(test="record"))


# ══════════════════════════════════════════════════════════════════════
#  raw mode: any firmware that prints CSV
# ══════════════════════════════════════════════════════════════════════

def test_raw(args):
    """Log every numeric CSV line. No protocol assumed."""
    import serial
    ticks = {}
    for item in (args.ticks or "").split(","):
        if item.strip():
            name, _, cpr = item.partition(":")
            ticks[name.strip()] = float(cpr)
    path = out_path(args, "raw")
    print(f"\n=== RAW LOG === {args.port} @ {args.baud}  ->  {path}")
    ser = serial.Serial(args.port, args.baud, timeout=0.1)
    time.sleep(args.open_delay)
    ser.reset_input_buffer()
    for c in args.send or []:
        ser.write(c.encode("ascii"))
        time.sleep(0.05)
    columns = args.columns.split(",") if args.columns else None
    ncol = len(columns) if columns else None
    rows, skipped = [], 0
    t0 = time.time()
    buf = b""
    try:
        while args.duration <= 0 or time.time() - t0 < args.duration:
            buf += ser.read(512)
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                t = time.time()
                line = raw.decode("ascii", "ignore").strip()
                if not line:
                    continue
                if line.startswith("#") and columns is None:
                    columns = [c.strip() for c in line[1:].split(",")]
                    ncol = len(columns)
                    print(f"    header from the board: {columns}")
                    continue
                try:
                    vals = [float(x) for x in line.split(",")]
                except ValueError:
                    skipped += 1
                    continue
                if ncol is None:
                    ncol = len(vals)
                    columns = [f"col{k}" for k in range(ncol)]
                if len(vals) != ncol:
                    skipped += 1
                    continue
                rows.append((t, vals))
            print(f"\r    {time.time() - t0:6.1f} s   {len(rows)} rows   {skipped} skipped",
                  end="", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
    print()
    missing = [k for k in ticks if not columns or k not in columns]
    if missing:
        print(f"    ! --ticks names not in the columns: {missing}")
    tcol = columns.index(args.time_col) if args.time_col and columns and args.time_col in columns else None
    derived = [k for k in ticks if columns and k in columns]
    header = ["pi_time_s"] + (columns or [])
    for k in derived:
        header += [f"{k}_rad", f"{k}_rads"]
    prev = None
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for t, vals in rows:
            extra = []
            tt = vals[tcol] / 1000.0 if tcol is not None else t
            for k in derived:
                ang = vals[columns.index(k)] * 2 * math.pi / ticks[k]
                vel = ""
                if prev is not None and tt > prev[0]:
                    vel = f"{(ang - prev[1][k]) / (tt - prev[0]):.4f}"
                extra += [f"{ang:.5f}", vel]
            w.writerow([f"{t:.4f}"] + [f"{v:g}" for v in vals] + extra)
            prev = (tt, {k: vals[columns.index(k)] * 2 * math.pi / ticks[k] for k in derived})
    print(f"    {len(rows)} rows -> {path}")
    return path


# ══════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════

def parse_gain_sets(text):
    out = []
    for chunk in text.split():
        parts = chunk.split(",")
        if len(parts) != 3:
            raise argparse.ArgumentTypeError(f"gain set '{chunk}' must be Kp,Ki,Kd")
        out.append(tuple(float(p) for p in parts))
    return out


def floats(text):
    return [float(x) for x in text.split(",") if x.strip()]


def ints(text):
    return [int(float(x)) for x in text.split(",") if x.strip()]


def main():
    ap = argparse.ArgumentParser(description="Encoder logger and PID calibration",
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("--test", required=True,
                    choices=["plant", "staircase", "steps", "sweep", "record", "raw"])
    ap.add_argument("--config", default=os.path.join(KIT, "robot_config.yaml"),
                    help="robot_config.yaml (motor names, port, limits). 'none' to skip.")
    ap.add_argument("--port", default=None, help="default: /dev/<mcu.device_name> from the config")
    ap.add_argument("--baud", type=int, default=None)
    ap.add_argument("--logdir", default=None, help="default: dashboard.log_dir, else ~/robot_logs")
    ap.add_argument("--only", default=None, help="comma list of motor names to test; others stay at 0")
    ap.add_argument("--mode", choices=["translate", "rotate"], default="translate",
                    help="plant/staircase: rotate spins in place using the kinematics")
    ap.add_argument("--yes", action="store_true", help="do not ask before moving")
    ap.add_argument("--open-delay", type=float, default=2.0,
                    help="seconds to wait after opening the port (most boards reset)")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--lam", type=float, default=0.15, help="closed-loop time constant for Ki")

    ap.add_argument("--plant-pwm", type=ints, default=None, help="e.g. 70,110,160")
    ap.add_argument("--plant-hold", type=float, default=2.5)
    ap.add_argument("--min-pwm", type=int, default=None)
    ap.add_argument("--max-pwm", type=int, default=None)
    ap.add_argument("--pwm-step", type=int, default=None)
    ap.add_argument("--dwell", type=float, default=1.5)
    ap.add_argument("--setpoints", type=floats, default=None, help="rad/s, e.g. 1,2,3")
    ap.add_argument("--rest", type=float, default=1.5)
    ap.add_argument("--no-slew", action="store_true")
    ap.add_argument("--gains", type=parse_gain_sets, default=None,
                    help='sweep: "kp,ki,kd kp,ki,kd ..."; steps: one set')
    ap.add_argument("--kff", type=floats, default=None, help="steps/sweep: send <F,...> first")
    ap.add_argument("--kstat", type=floats, default=None, help="steps/sweep: send <K,...> first")
    ap.add_argument("--duration", type=float, default=0, help="record/raw: seconds, 0 = until Ctrl-C")
    ap.add_argument("--hz", type=float, default=50, help="record: telemetry rate")

    ap.add_argument("--columns", default=None, help="raw: column names, comma separated")
    ap.add_argument("--ticks", default=None, help="raw: name:counts_per_rev,... to add rad and rad/s")
    ap.add_argument("--time-col", default=None, help="raw: a millisecond time column from the board")
    ap.add_argument("--send", action="append", help="raw: a command to send first (repeatable)")
    args = ap.parse_args()

    cfg = None
    if args.config != "none" and load_config and os.path.exists(os.path.expanduser(args.config)):
        try:
            cfg = load_config(args.config)
        except ConfigError as e:
            print(f"  ! robot_config.yaml: {e}  (continuing without it)")
    if args.port is None:
        args.port = f"/dev/{cfg['mcu']['device_name']}" if cfg else "/dev/ttyUSB0"
    if args.baud is None:
        args.baud = int(cfg["mcu"]["baud"]) if cfg else 115200
    if args.logdir is None:
        args.logdir = (cfg or {}).get("dashboard", {}).get("log_dir", "~/robot_logs")
    if args.only:
        args.only = [s.strip() for s in args.only.split(",")]
    if args.test == "sweep" and not args.gains:
        ap.error('--test sweep needs --gains "Kp,Ki,Kd Kp,Ki,Kd ..."')

    if args.test == "raw":
        return 0 if test_raw(args) else 1

    if args.test == "record":
        others = bridge_running()
        if others:
            print("  ! the ROS bridge seems to be running:\n    " + "\n    ".join(others))
            print("    Two programs reading one serial port corrupt each other's data.\n"
                  "    Stop it (sudo systemctl stop robot.service), or log under ROS with\n"
                  "    the dashboard's REC button instead.")
            return 1

    if not args.yes and args.test != "record":
        print("\n" + "=" * 64)
        if args.test in ("plant", "staircase") and args.mode == "translate":
            print("  Open loop. WHEELS IN THE AIR. On the floor this drives in a")
            print("  straight line and keeps going: clear a runway or use --mode rotate.")
        else:
            print("  Wheels will turn. Confirm they are clear and the battery")
            print("  disconnect is in reach.")
        print("  Ctrl-C stops everything (<S>, <L0>, <E0>).")
        print("=" * 64)
        try:
            input("  Enter to start, Ctrl-C to abort: ")
        except (KeyboardInterrupt, EOFError):
            print("\n  aborted.")
            return 1

    link = None
    try:
        link = SerialLink(args.port, args.baud, open_delay=args.open_delay, verbose=args.verbose)
        robot = Robot(link, cfg)
        print(f"\n    connected: {args.port} @ {args.baud}   firmware: {robot.info or 'unknown'}")
        print(f"    motors: {', '.join(robot.names)}   PWM_MAX {robot.pwm_max}   vmax {robot.vmax} rad/s")
        if args.only:
            bad = [m for m in args.only if m not in robot.names]
            if bad:
                raise RuntimeError(f"--only {bad}: not a motor name ({robot.names})")

        def bail(*_):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, bail)

        {"plant": test_plant, "staircase": test_staircase,
         "steps": lambda l, r, a: test_steps(l, r, a, gains=a.gains[0] if a.gains else None)[0],
         "sweep": test_sweep, "record": test_record}[args.test](link, robot, args)
    except KeyboardInterrupt:
        print("\n\n    interrupted: stopping motors.")
    except Exception as e:  # noqa: BLE001
        print(f"\n\n    FAILED: {e}", file=sys.stderr)
        return 1
    finally:
        if link:
            for r in link.drain_replies():
                if "TRIP" in r[1] or "ERR" in r[1]:
                    print(f"    firmware said: {r[1]}")
            link.close()
            print("    motors stopped, port closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
