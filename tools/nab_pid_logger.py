#!/usr/bin/env python3
"""
NarrowAisleBot — PID bench logger / test driver
===============================================
Runs on the Raspberry Pi 5. Talks to the ESP32 over USB serial, drives a
scripted test, and writes a CSV. No ROS 2, no serial monitor, no
copy-pasting a terminal buffer — the file lands in ~/aislebot_logs/ and is
ready for aislebot_pid_analysis_v2.py or to be sent on for tuning.

    >>> WHEELS IN THE AIR for every test except --test record. <<<

The CSV's first 13 columns are exactly the format
aislebot_pid_analysis_v2.py already expects:

    pi_time_s, FR_target_rads, FR_actual_rads, FR_pwm,
               FL_target_rads, FL_actual_rads, FL_pwm,
               RR_target_rads, RR_actual_rads, RR_pwm,
               RL_target_rads, RL_actual_rads, RL_pwm

With <L2> telemetry another 16 follow (error / feedforward / integral term
/ accumulated angle, per motor). The analysis notebook ignores them; the
tuning maths needs them.


TESTS
-----
  plant      Open-loop PWM steps (PID bypassed) at 50 Hz.
             Measures the mechanical time constant tau and the DC gain.
             *** This is the missing measurement.*** Kp in the firmware is
             currently the only gain that is an estimate rather than a
             fit, because tau has never been logged on this robot. Run
             this one first.

  staircase  PWM ramped up in small steps from rest, per motor.
             Finds start-of-motion PWM = Kstat, and the low-speed slope.
             Run it in the air, then again on the floor — the difference
             between those two numbers is the ground-load correction.

  steps      Closed-loop velocity steps through the PID.
             Rise time, overshoot, settling time, steady-state error.
             This is the one that says whether a gain set is good.

  sweep      Closed-loop steps repeated over several gain sets.
             Give it --gains "45,250,0.5 60,250,0.5 45,400,0.5" and it
             logs one CSV per set so they can be compared directly.

  record     Log only, drive the robot however you like (ROS 2 teleop,
             joystick, anything). Ctrl-C to stop.


EXAMPLES
--------
    ./nab_pid_logger.py --test plant
    ./nab_pid_logger.py --test staircase --max-pwm 60
    ./nab_pid_logger.py --test steps --setpoints 1.0,2.0,3.0,4.5
    ./nab_pid_logger.py --test sweep --gains "45,250,0.5 45,400,0.5 70,250,1.5"
    ./nab_pid_logger.py --test record --duration 120

Ctrl-C at any point sends <S> then <E0>. So does any crash.

Aritra Das (25D0074) — IIT Bombay — Prof. Ambarish Kunwar
"""

import argparse
import csv
import math
import os
import signal
import sys
import threading
import time
from datetime import datetime

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    sys.exit("pyserial missing.  sudo apt install python3-serial   "
             "(or: pip install pyserial)")


MOTORS = ["FR", "FL", "RR", "RL"]

BASE_HEADER = ["pi_time_s"] + [
    f"{m}_{f}" for m in MOTORS
    for f in ("target_rads", "actual_rads", "pwm")
]
EXT_HEADER = [
    f"{m}_{f}" for m in MOTORS
    for f in ("error", "ff", "iterm", "pos_rad")
]


# ══════════════════════════════════════════════════════════════════════
#  Serial link
# ══════════════════════════════════════════════════════════════════════

class ESP32Link:
    """Serial link with a background reader that timestamps every
    telemetry row on arrival. Timestamping in the reader thread rather
    than at write time keeps jitter down to the USB latency instead of
    adding whatever the writer was doing."""

    def __init__(self, port, baud, verbose=False):
        self.port = port or self._autodetect()
        if not self.port:
            raise RuntimeError("No ESP32 found. Pass --port /dev/ttyUSB0.")

        self.ser = serial.Serial(self.port, baud, timeout=0.1, write_timeout=1.0)
        time.sleep(2.0)                     # ESP32 resets on port open
        self.ser.reset_input_buffer()

        self.verbose = verbose
        self.rows = []                      # [(t, [floats])]
        self.replies = []                   # [(t, "[OK,...]")]
        self._collect = False
        self._lock = threading.Lock()
        self._running = True
        self._t0 = None

        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    @staticmethod
    def _autodetect():
        for p in serial.tools.list_ports.comports():
            blob = f"{p.description or ''} {p.manufacturer or ''}"
            if any(k in blob for k in ("CP210", "CH340", "Silicon Labs", "FTDI")):
                return p.device
        for p in serial.tools.list_ports.comports():
            if "USB" in (p.device or ""):
                return p.device
        return None

    # ── reader thread ────────────────────────────────────────────────
    def _reader(self):
        buf = b""
        while self._running:
            try:
                chunk = self.ser.read(512)
                if not chunk:
                    continue
                buf += chunk
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    self._handle(raw.decode("ascii", "ignore").strip())
            except serial.SerialException as e:
                print(f"\n!! serial error: {e}", file=sys.stderr)
                self._running = False
            except Exception:
                pass

    def _handle(self, line):
        if not line:
            return
        now = time.time()

        if line.startswith("["):
            with self._lock:
                self.replies.append((now, line))
            if self.verbose or line.startswith(("[ERR", "[TRIP", "[WARN")):
                print(f"    {line}")
            return

        # Telemetry: first field is the ESP32 millis() stamp.
        if not line[0].isdigit() or "," not in line:
            if self.verbose:
                print(f"    {line}")
            return
        try:
            vals = [float(x) for x in line.split(",")]
        except ValueError:
            return
        if len(vals) < 13:
            return
        with self._lock:
            if self._collect:
                self.rows.append((now, vals[1:]))   # drop the ESP32 stamp

    # ── control ──────────────────────────────────────────────────────
    def send(self, cmd, settle=0.02):
        self.ser.write(cmd.encode("ascii"))
        self.ser.flush()
        if settle:
            time.sleep(settle)

    def start_collect(self):
        with self._lock:
            self.rows.clear()
            self._collect = True
            self._t0 = time.time()

    def stop_collect(self):
        with self._lock:
            self._collect = False
            return list(self.rows)

    def drain_replies(self):
        with self._lock:
            r = list(self.replies)
            self.replies.clear()
        return r

    def close(self):
        self._running = False
        try:
            self.send("<S>", 0.05)
            self.send("<L0>", 0.05)
            self.send("<E0>", 0.05)
        except Exception:
            pass
        time.sleep(0.1)
        try:
            self.ser.close()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════
#  CSV
# ══════════════════════════════════════════════════════════════════════

def write_csv(rows, path, extended):
    header = BASE_HEADER + (EXT_HEADER if extended else [])
    ncol = len(header) - 1
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for t, vals in rows:
            v = vals[:ncol] + [""] * max(0, ncol - len(vals))
            w.writerow([f"{t:.4f}"] + [f"{x:g}" if x != "" else "" for x in v])
    return path


def run_path(logdir, tag):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(os.path.expanduser(logdir), f"{tag}_{ts}.csv")


# ══════════════════════════════════════════════════════════════════════
#  Analysis helpers — enough to tell you on the spot whether the run
#  was any good, without waiting to get the file onto a laptop.
# ══════════════════════════════════════════════════════════════════════

def col(rows, motor_idx, field, extended):
    """field: 0=target 1=actual 2=pwm, or 'err'/'ff'/'i'/'pos' when extended."""
    if isinstance(field, int):
        j = motor_idx * 3 + field
    else:
        base = 12 + motor_idx * 4
        j = base + {"err": 0, "ff": 1, "i": 2, "pos": 3}[field]
    out = []
    for t, vals in rows:
        if j < len(vals):
            out.append((t, vals[j]))
    return out


def estimate_tau(series, t_step, v_final):
    """First-order time constant: time from the step to 63.2 % of the
    final value. Crude by design — it is robust, and one number measured
    beats one number assumed."""
    if abs(v_final) < 0.2:
        return None
    target = 0.632 * v_final
    for t, v in series:
        if t < t_step:
            continue
        if (v_final > 0 and v >= target) or (v_final < 0 and v <= target):
            return t - t_step
    return None


def steady_state(series, t_from, t_to):
    vals = [v for t, v in series if t_from <= t <= t_to]
    return sum(vals) / len(vals) if vals else float("nan")


def peak(series, t_from, t_to):
    vals = [abs(v) for t, v in series if t_from <= t <= t_to]
    return max(vals) if vals else float("nan")


def settling_time(series, t_step, target, band=0.05, hold=0.2):
    """First moment after the step where the signal stays inside
    +/-band*|target| for `hold` seconds and never leaves again."""
    if abs(target) < 0.1:
        return None
    thr = abs(target) * band
    pts = [(t, v) for t, v in series if t >= t_step]
    for i, (t, _) in enumerate(pts):
        if all(abs(v - target) <= thr for _, v in pts[i:]):
            if pts[-1][0] - t >= hold:
                return t - t_step
    return None


# ══════════════════════════════════════════════════════════════════════
#  Tests
# ══════════════════════════════════════════════════════════════════════

def test_plant(link, args):
    """Open-loop PWM step. Bypasses the PID entirely (<M>), so what comes
    back is the plant on its own: gain and time constant, no controller
    in the way. tau from this run is what pins down Kp."""
    print("\n=== PLANT IDENTIFICATION (open loop, PID bypassed) ===")
    print("    Wheels in the air. Drives all four at once.\n")

    link.send("<E1>")
    link.send("<W0>")          # no command watchdog — <M> is not a <V>
    link.send("<Y0>")          # trips off: open loop has no velocity target
    link.send("<L2,50>")
    link.start_collect()

    t0 = time.time()
    marks = []
    for pwm in args.plant_pwm:
        for sign in (+1, -1):
            link.send("<M,0,0,0,0>", 0)
            time.sleep(1.5)
            t_step = time.time()
            link.send(f"<M,{sign*pwm},{sign*pwm},{sign*pwm},{sign*pwm}>", 0)
            marks.append((t_step, sign * pwm))
            print(f"    step -> PWM {sign*pwm:+4d}   ({time.time()-t0:5.1f} s)")
            time.sleep(args.plant_hold)

    link.send("<M,0,0,0,0>")
    time.sleep(1.0)
    rows = link.stop_collect()
    link.send("<L0>")
    link.send("<W1>")
    link.send("<Y1>")

    path = write_csv(rows, run_path(args.logdir, "plant"), True)
    print(f"\n    {len(rows)} samples -> {path}")

    print("\n    motor  PWM    v_ss(rad/s)   K=v/pwm    tau(s)")
    print("    -----  ----   -----------   --------   ------")
    gains, taus = {m: [] for m in MOTORS}, {m: [] for m in MOTORS}
    for i, m in enumerate(MOTORS):
        act = col(rows, i, 1, True)
        for t_step, pwm in marks:
            t_end = t_step + args.plant_hold
            v_ss = steady_state(act, t_end - 0.5, t_end)
            if math.isnan(v_ss) or abs(v_ss) < 0.2:
                continue
            tau = estimate_tau(act, t_step, v_ss)
            k = abs(v_ss / pwm)
            gains[m].append(k)
            if tau:
                taus[m].append(tau)
            print(f"    {m:<5}  {pwm:+4d}   {v_ss:11.3f}   {k:8.5f}   "
                  f"{tau if tau else float('nan'):6.3f}")

    print("\n    === WHAT TO DO WITH THIS ===")
    for m in MOTORS:
        if not gains[m]:
            print(f"    {m}: no usable steps — check the wiring.")
            continue
        k = sum(gains[m]) / len(gains[m])
        tau = sum(taus[m]) / len(taus[m]) if taus[m] else None
        line = f"    {m}: K = {k:.5f} rad/s per PWM  ->  Kff ~ {1/k:6.1f}"
        if tau:
            lam = 0.15
            print(line + f"   tau = {tau:.3f} s")
            print(f"         lambda=0.15 s  ->  Ki = {1/(k*lam):6.0f}   "
                  f"Kp = {tau/(k*lam):6.1f}")
        else:
            print(line + "   tau: not resolved (raise --plant-hold or the rate)")
    print("\n    Kp = tau * Ki, Ki = 1/(K*lambda). Send the CSV on if you "
          "want the numbers checked before flashing.")
    return path


def ols_fit(xs, ys):
    """Least-squares line y = m*x + c. Pure Python -- no numpy dependency,
    this script only needs pyserial so it stays runnable on the Pi as-is."""
    n = len(xs)
    if n < 2:
        return None
    sx = sum(xs); sy = sum(ys)
    sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-9:
        return None
    m = (n * sxy - sx * sy) / denom
    c = (sy - m * sx) / n
    return m, c


def test_staircase(link, args):
    """PWM up in small steps from rest. The first step that produces
    motion is a conservative (slightly high) estimate of breakaway PWM.
    The more accurate numbers come from a straight-line fit through the
    moving points: v = m*pwm + c, so Kff = 1/m (the viscous slope) and
    Kstat = -c/m (the PWM x-intercept -- where the line crosses v=0, a
    tighter estimate of true breakaway than 'first step that moved').
    Do this in the air, then again on the floor -- the two Kff/Kstat
    fits are what quantify the ground-load correction, not a guess."""
    print("\n=== STATIC FRICTION STAIRCASE (open loop) ===")
    print(f"    PWM {args.min_pwm} -> {args.max_pwm} step {args.pwm_step}, "
          f"{args.dwell:.1f} s each.\n")

    link.send("<E1>")
    link.send("<W0>")
    link.send("<Y0>")
    link.send("<L2,50>")
    link.start_collect()

    marks = []
    for pwm in range(args.min_pwm, args.max_pwm + 1, args.pwm_step):
        link.send("<M,0,0,0,0>", 0)
        time.sleep(0.6)                       # let it come fully to rest
        t_step = time.time()
        link.send(f"<M,{pwm},{pwm},{pwm},{pwm}>", 0)
        marks.append((t_step, pwm))
        time.sleep(args.dwell)
        print(f"    PWM {pwm:3d}")

    link.send("<M,0,0,0,0>")
    time.sleep(0.5)
    rows = link.stop_collect()
    link.send("<L0>")
    link.send("<W1>")
    link.send("<Y1>")

    path = write_csv(rows, run_path(args.logdir, "staircase"), True)
    print(f"\n    {len(rows)} samples -> {path}")

    print("\n    PWM  " + "".join(f"{m:>10}" for m in MOTORS))
    breakaway = {m: None for m in MOTORS}
    for t_step, pwm in marks:
        cells = []
        for i, m in enumerate(MOTORS):
            v = steady_state(col(rows, i, 1, True),
                             t_step + args.dwell - 0.4, t_step + args.dwell)
            cells.append(f"{v:10.3f}" if not math.isnan(v) else f"{'—':>10}")
            if breakaway[m] is None and not math.isnan(v) and abs(v) > 0.05:
                breakaway[m] = pwm
        print(f"    {pwm:3d}  " + "".join(cells))

    print("\n    === BREAKAWAY PWM (raw, conservative -- first step that moved) ===")
    for m in MOTORS:
        b = breakaway[m]
        print(f"    {m}: {b if b is not None else 'not reached'}")

    # Straight-line fit through the moving region: v = m*pwm + c.
    # Only points at or above breakaway are in the linear (non-stiction)
    # regime; below breakaway v=0 by definition and would bias the fit.
    print("\n    === LINE FIT (v = m*pwm + c) -> Kff=1/m, Kstat=x-intercept ===")
    fit_kff, fit_kstat = {}, {}
    for i, m in enumerate(MOTORS):
        if breakaway[m] is None:
            print(f"    {m}: never broke away in this PWM range -- raise --max-pwm")
            continue
        pts = [(pwm, steady_state(col(rows, i, 1, True), t + args.dwell - 0.4, t + args.dwell))
               for t, pwm in marks if pwm >= breakaway[m]]
        pts = [(p, v) for p, v in pts if not math.isnan(v) and v > 0.02]
        fit = ols_fit([p for p, _ in pts], [v for _, v in pts])
        if fit is None or fit[0] <= 1e-6:
            print(f"    {m}: not enough clean points to fit ({len(pts)} usable) -- "
                  f"widen --max-pwm or --pwm-step")
            continue
        slope, intercept = fit
        kff = 1.0 / slope
        kstat = -intercept / slope
        fit_kff[m], fit_kstat[m] = kff, kstat
        print(f"    {m}: Kff={kff:6.2f} pwm/(rad/s)   Kstat={kstat:5.1f} pwm   "
              f"(n={len(pts)} points, breakaway was {breakaway[m]})")

    if len(fit_kstat) == len(MOTORS):
        print(f"\n    Firmware:  <F,{','.join(f'{fit_kff[m]:.2f}' for m in MOTORS)}>")
        print(f"               <K,{','.join(f'{fit_kstat[m]:.1f}' for m in MOTORS)}>")
        print("    Then make these permanent in Kff[]/Kstat[] in aislebot_esp32.ino.")
        print("\n    These Kff values also refine Ki (Ki = Kff / lambda, lambda=0.15s\n"
              "    by default) and, once you have tau from --test plant, Kp = tau * Ki.\n"
              "    See docs/PID_Calibration.md for the full derivation.")
    else:
        print("\n    Not all four motors got a clean fit -- see warnings above before "
              "trusting these numbers.")
    return path


def test_steps(link, args, gains=None, tag="steps"):
    """Closed-loop velocity steps. The verdict test for a gain set."""
    label = f" Kp={gains[0]} Ki={gains[1]} Kd={gains[2]}" if gains else ""
    print(f"\n=== CLOSED-LOOP STEP RESPONSE{label} ===")

    link.send("<E1>")
    link.send("<W1>")
    link.send("<Y1>")
    if gains:
        link.send(f"<G,{gains[0]},{gains[1]},{gains[2]}>")
    if args.no_slew:
        link.send("<A,0>")
        print("    slew limiter OFF — raw step into the controller")
    link.send("<L2,50>")
    link.start_collect()

    marks = []
    for sp in args.setpoints:
        # Hold zero first so each step starts from a clean, identical state.
        _hold(link, 0.0, args.rest)
        t_step = time.time()
        _hold(link, sp, args.dwell)
        marks.append((t_step, sp))
        print(f"    setpoint {sp:.2f} rad/s")
    _hold(link, 0.0, 1.0)

    rows = link.stop_collect()
    link.send("<L0>")
    link.send("<V,0,0,0,0>")

    path = write_csv(rows, run_path(args.logdir, tag), True)
    print(f"\n    {len(rows)} samples -> {path}")

    print("\n    setpt  motor    ss     err   overshoot  settle(s)  sat%")
    print("    -----  -----  ------  ------  ---------  ---------  ----")
    worst_err = 0.0
    for t_step, sp in marks:
        t_end = t_step + args.dwell
        for i, m in enumerate(MOTORS):
            act = col(rows, i, 1, True)
            pwm = col(rows, i, 2, True)
            ss = steady_state(act, t_end - 0.5, t_end)
            pk = peak(act, t_step, t_end)
            st = settling_time(act, t_step, sp)
            win = [p for t, p in pwm if t_step <= t <= t_end]
            sat = 100.0 * sum(1 for p in win if abs(p) >= 250) / len(win) if win else 0.0
            err = ss - sp
            worst_err = max(worst_err, abs(err))
            print(f"    {sp:5.2f}  {m:<5}  {ss:6.3f}  {err:+6.3f}  "
                  f"{pk - sp:+9.3f}  "
                  f"{(f'{st:.2f}' if st else '  none'):>9}  {sat:4.0f}")

    print(f"\n    worst steady-state error: {worst_err:.3f} rad/s")
    if worst_err > 0.15:
        print("    -> feedforward is off, or Ki is still too low. Run "
              "--test plant and refit.")
    return path


def test_sweep(link, args):
    paths = []
    for gs in args.gain_sets:
        paths.append(test_steps(link, args, gains=gs,
                                tag=f"sweep_kp{gs[0]:g}_ki{gs[1]:g}_kd{gs[2]:g}"))
        _hold(link, 0.0, 1.5)
    print("\n=== SWEEP DONE ===")
    for p in paths:
        print(f"    {p}")
    print("\n    Compare settle time and overshoot across the sets above. "
          "Lowest settle with overshoot under ~5 % wins.")
    return paths


def test_record(link, args):
    print("\n=== RECORD ===")
    print("    Logging only — drive the robot however you like.")
    print("    Ctrl-C to stop.\n")

    link.send("<L2,50>")
    link.start_collect()
    t0 = time.time()
    try:
        while args.duration <= 0 or time.time() - t0 < args.duration:
            time.sleep(0.5)
            n = len(link.rows)
            print(f"\r    {time.time()-t0:6.1f} s   {n} samples", end="", flush=True)
    except KeyboardInterrupt:
        print()
    rows = link.stop_collect()
    link.send("<L0>")
    path = write_csv(rows, run_path(args.logdir, "record"), True)
    print(f"\n    {len(rows)} samples -> {path}")
    return path


def _hold(link, setpoint, seconds):
    """Hold a velocity setpoint, resending at 20 Hz so the ESP32's command
    watchdog stays fed the same way the ROS 2 bridge feeds it."""
    cmd = f"<V,{setpoint:.3f},{setpoint:.3f},{setpoint:.3f},{setpoint:.3f}>"
    t_end = time.time() + seconds
    while time.time() < t_end:
        link.send(cmd, 0)
        time.sleep(0.05)


# ══════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════

def parse_gain_sets(text):
    out = []
    for chunk in text.split():
        parts = chunk.split(",")
        if len(parts) != 3:
            raise argparse.ArgumentTypeError(
                f"gain set '{chunk}' must be Kp,Ki,Kd")
        out.append(tuple(float(p) for p in parts))
    return out


def main():
    ap = argparse.ArgumentParser(
        description="NarrowAisleBot PID bench logger",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)

    ap.add_argument("--test", required=True,
                    choices=["plant", "staircase", "steps", "sweep", "record"])
    ap.add_argument("--port", default=None, help="default: autodetect")
    ap.add_argument("--baud", type=int, default=921600)
    ap.add_argument("--logdir", default="~/aislebot_logs")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="echo every [..] reply from the ESP32")

    ap.add_argument("--plant-pwm", default="70,110,160",
                    help="plant: PWM levels to step to (default 70,110,160)")
    ap.add_argument("--plant-hold", type=float, default=2.5,
                    help="plant: seconds held at each level")

    ap.add_argument("--min-pwm", type=int, default=2, help="staircase: first PWM")
    ap.add_argument("--max-pwm", type=int, default=40, help="staircase: last PWM")
    ap.add_argument("--pwm-step", type=int, default=2, help="staircase: increment")
    ap.add_argument("--dwell", type=float, default=1.5,
                    help="staircase/steps: seconds per level")

    ap.add_argument("--setpoints", default="1.0,2.0,3.0,4.5",
                    help="steps/sweep: velocity setpoints rad/s")
    ap.add_argument("--rest", type=float, default=1.5,
                    help="steps: seconds at zero between steps")
    ap.add_argument("--no-slew", action="store_true",
                    help="steps: disable the setpoint slew limiter, so the "
                         "controller sees a true step")
    ap.add_argument("--gains", type=parse_gain_sets, dest="gain_sets",
                    default=None,
                    help='sweep: e.g. "45,250,0.5 60,250,0.5 45,400,1.5"')

    ap.add_argument("--duration", type=float, default=0,
                    help="record: seconds, 0 = until Ctrl-C")

    args = ap.parse_args()
    args.plant_pwm = [int(x) for x in args.plant_pwm.split(",")]
    args.setpoints = [float(x) for x in args.setpoints.split(",")]
    if args.test == "sweep" and not args.gain_sets:
        ap.error('--test sweep needs --gains "Kp,Ki,Kd Kp,Ki,Kd ..."')

    if args.test != "record":
        print("\n" + "=" * 62)
        print("  WHEELS MUST BE IN THE AIR. This drives all four motors.")
        print("  Ctrl-C stops everything (<S> then <E0>).")
        print("=" * 62)
        try:
            input("  Enter to start, Ctrl-C to bail: ")
        except (KeyboardInterrupt, EOFError):
            print("\n  aborted.")
            return 1

    link = None
    try:
        link = ESP32Link(args.port, args.baud, args.verbose)
        print(f"\n    connected: {link.port} @ {args.baud}")
        link.send("<P>", 0.2)
        link.send("<I>", 0.3)
        for _, r in link.drain_replies():
            print(f"    {r}")

        def bail(*_):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, bail)

        {"plant": test_plant,
         "staircase": test_staircase,
         "steps": test_steps,
         "sweep": test_sweep,
         "record": test_record}[args.test](link, args)

    except KeyboardInterrupt:
        print("\n\n    interrupted — stopping motors.")
    except Exception as e:
        print(f"\n\n    FAILED: {e}", file=sys.stderr)
        return 1
    finally:
        if link:
            link.close()
            print("    motors stopped, port closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
