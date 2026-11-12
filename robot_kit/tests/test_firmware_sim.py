#!/usr/bin/env python3
"""Firmware checks in simulation:  python3 tests/test_firmware_sim.py

For every config in the kit, generates robot_config.h, compiles the REAL
robot_mcu.ino against tools/firmware_sim (mock Arduino core + simulated
motors with static friction and quadrature encoders), and checks:

  closed loop     targets reached within 5 % in 2.5 s, both directions
  telemetry       exactly 1+3N columns after <L1>, 1+7N after <L2>
  open loop       <M> drives the wheel at the speed the plant predicts
  watchdog        silence stops the wheels and prints [WARN,WATCHDOG]
  E-STOP          <S> latches: <V> is ignored until <E1>
  runaway trip    an encoder wired backwards latches [TRIP,RUNAWAY] in < 2 s
  <B>             a forward body twist drives every wheel forward
  identity        <I> reports [MOTORS,N,names...]
  odometry        <O> wheel angle matches the integral of velocity; <R> zeroes it
  bad input       a malformed command gets [ERR,...], not a crash

Needs g++ and make. Not covered: the ESP32-only code (PCNT, ledc, FreeRTOS
tasks). That code is NarrowAisleBot's, which runs on the real robot.
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

import yaml

KIT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SIMDIR = os.path.join(KIT, "tools", "firmware_sim")
FAILS = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def run(sim, script, until, *extra):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write(script)
        path = fh.name
    out = subprocess.run([sim, "--script", path, "--until", str(until), *extra],
                         capture_output=True, text=True, timeout=300).stdout
    os.unlink(path)
    lines = []
    plant = {}
    for ln in out.splitlines():
        if ln.startswith("#PLANT"):
            plant = dict(kv.split("=") for kv in ln.split()[1:])
            continue
        t, _, body = ln.partition(" ")
        lines.append((int(t), body))
    return lines, {k: float(v) for k, v in plant.items()}


def telemetry(lines, n):
    rows = []
    for t, b in lines:
        if b and b[0].isdigit() and "," in b:
            rows.append((t, [float(x) for x in b.split(",")]))
    return rows


def replies(lines, prefix):
    return [(t, b) for t, b in lines if b.startswith("[" + prefix)]


for cfg_path in [os.path.join(KIT, "robot_config.yaml")] + sorted(glob.glob(os.path.join(KIT, "examples", "*.yaml"))):
    cfg = yaml.safe_load(open(cfg_path))
    n = len(cfg["wheels"])
    names = [w["name"] for w in cfg["wheels"]]
    vmax = float(cfg["mcu"]["max_wheel_speed"])
    wd = int(cfg["mcu"].get("watchdog_ms", 750))
    print(f"\n{os.path.relpath(cfg_path, KIT)}  ({n} motors, {cfg['driver']['type']}, "
          f"x{cfg['wheels'][0].get('encoder_decoding', 4)}, {cfg['mcu'].get('control_hz', 100)} Hz)")
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, os.path.join(KIT, "generate.py"), "--config", cfg_path,
                        "--out", tmp], check=True, capture_output=True)
        fw = os.path.join(tmp, "firmware", "robot_mcu")
        shutil.copy(os.path.join(KIT, "firmware", "robot_mcu", "robot_mcu.ino"), fw)
        build = os.path.join(tmp, "simbuild")
        shutil.copytree(SIMDIR, build, ignore=shutil.ignore_patterns("sim"))
        r = subprocess.run(["make", "-s", f"FW={fw}", "CXXFLAGS=-std=c++17 -O2 -Wall -Werror "
                            "-Wno-unused-function -Wno-unused-variable"],
                           cwd=build, capture_output=True, text=True)
        check(r.returncode == 0, "compiles with -Wall -Werror" + ("" if r.returncode == 0 else "\n" + r.stderr[-2000:]))
        if r.returncode:
            continue
        sim = os.path.join(build, "sim")

        # Pick targets the plant can reach with headroom, signs alternating.
        a, b = 0.4 * vmax, -0.25 * vmax
        tg = [a if i % 2 == 0 else b for i in range(n)]
        vcmd = "<V," + ",".join(f"{x:.3f}" for x in tg) + ">"

        lines, plant = run(sim, f"0 <E1>\n0 <L2,20>\n100-2600/50 {vcmd}\n2650 <O>\n2700 <L1,20>\n", 3000)
        rows = telemetry(lines, n)
        ext = [v for t, v in rows if 300 < t < 2650]
        basic = [v for t, v in rows if t > 2760]
        check(ext and all(len(v) == 1 + 7 * n for v in ext), f"<L2> rows have {1 + 7 * n} columns")
        check(basic and all(len(v) == 1 + 3 * n for v in basic), f"<L1> rows have {1 + 3 * n} columns")
        last = [v for t, v in rows if 2400 <= t <= 2600]
        ok = True
        for i in range(n):
            act = sum(v[1 + 3 * i + 1] for v in last) / len(last)
            err = abs(act - tg[i]) / abs(tg[i])
            ok &= err < 0.05
            print(f"       {names[i]:<12} target {tg[i]:+.3f}  actual {act:+.3f}  ({100 * err:.1f} %)")
        check(ok, "closed loop reaches every target within 5 %")
        odo = replies(lines, "ODOM")
        if odo:
            pos = [float(x) for x in odo[0][1].strip("[]").split(",")[1:]]
            integ = []
            prev_t = None
            for i in range(n):
                s, pt = 0.0, None
                for t, v in rows:
                    if t > 2650:
                        break
                    if pt is not None:
                        s += v[1 + 3 * i + 1] * (t - pt) / 1000.0
                    pt = t
                integ.append(s)
            close = all(abs(p - q) < 0.15 * max(abs(q), 0.5) for p, q in zip(pos, integ))
            check(close, f"<O> angles {['%.2f' % p for p in pos]} match the integrated velocity "
                         f"{['%.2f' % q for q in integ]}")
        else:
            check(False, "<O> answered")

        # Open loop: the plant's own steady state is (pwm - kstat) / kff.
        pwm = int(0.5 * (2 ** int(cfg['mcu'].get('pwm_bits', 8)) - 1))
        lines, plant = run(sim, f"0 <E1>\n0 <W0>\n0 <Y0>\n0 <L1,50>\n100 <M,{','.join([str(pwm)] * n)}>\n", 1600)
        rows = telemetry(lines, n)
        ss = [v for t, v in rows if 1200 <= t <= 1600]
        pred = (pwm - plant["kstat"]) / plant["kff"]
        got = sum(ss[-1][1 + 3 * i + 1] for i in range(n)) / n
        check(abs(got - pred) / pred < 0.06, f"<M,{pwm}> open loop: mean {got:.3f} rad/s, plant predicts "
                                             f"{pred:.3f} (motors differ by +/-3 %)")
        check(any(b.startswith("[OK,M") for _, b in lines), "<M> acknowledged")

        # Watchdog.
        lines, _ = run(sim, f"0 <E1>\n0 <L1,20>\n100-600/50 {vcmd}\n", 600 + wd + 1500)
        rows = telemetry(lines, n)
        w = replies(lines, "WARN,WATCHDOG")
        check(bool(w) and 600 + wd - 60 <= w[0][0] <= 600 + wd + 60,
              f"watchdog fires about {wd} ms after the last command (at {w[0][0] if w else None} ms)")
        tail = [v for t, v in rows if t > 600 + wd + 1200]
        check(tail and all(abs(v[1 + 3 * i + 1]) < 0.05 for v in tail for i in range(n)),
              "wheels stopped after the watchdog")

        # E-STOP latches.
        lines, _ = run(sim, f"0 <E1>\n0 <L1,20>\n100 <S>\n150-1100/50 {vcmd}\n1200 <E1>\n1250-2500/50 {vcmd}\n", 2600)
        rows = telemetry(lines, n)
        latched = [v for t, v in rows if 300 <= t <= 1150]
        check(any(b == "[OK,ESTOP_LATCHED]" for _, b in lines), "<S> acknowledged")
        check(latched and all(v[1 + 3 * i + 2] == 0 for v in latched for i in range(n)),
              "PWM stays 0 while latched, even with <V> arriving")
        after = [v for t, v in rows if t > 2300]
        check(after and abs(after[-1][2] - tg[0]) / abs(tg[0]) < 0.1, "<E1> clears it and driving resumes")

        # A backwards encoder must latch a trip. Which one depends on the motor:
        # if it can outrun 1.3 x max_wheel_speed, OVERSPEED gets there first;
        # if it cannot (NarrowAisleBot's 60 RPM motors), only RUNAWAY catches it.
        lines, _ = run(sim, f"0 <E1>\n0 !encflip 0\n100-3000/50 {vcmd}\n", 3000)
        trip = replies(lines, "TRIP")
        check(bool(trip) and trip[0][0] < 2100, f"fast motor, backwards encoder: {trip[0][1] if trip else 'no trip'} "
                                                 f"at {trip[0][0] if trip else None} ms")
        slow_kff = (2 ** int(cfg['mcu'].get('pwm_bits', 8)) - 1) / (1.1 * vmax)
        lines, _ = run(sim, f"0 <E1>\n0 !encflip 0\n100-3000/50 {vcmd}\n", 3000, "--kff", f"{slow_kff:.4f}")
        trip = replies(lines, "TRIP,RUNAWAY")
        check(bool(trip) and trip[0][0] < 2100, f"motor that cannot overspeed: [TRIP,RUNAWAY] at "
                                                 f"{trip[0][0] if trip else None} ms")

        # Body twist, identity, errors.
        lines, _ = run(sim, "0 <E1>\n0 <L1,20>\n100-1500/50 <B,0.1,0,0>\n1600 <I>\n1650 <V,1>\n1700 <Q>\n1710-2900/100 <?>\n3000 <R>\n3050 <O>\n", 3100)
        rows = telemetry(lines, n)
        lastv = [v for t, v in rows if 1200 <= t <= 1500]
        check(lastv and all(lastv[-1][1 + 3 * i + 1] > 0 for i in range(n)), "<B,0.1,0,0> drives every wheel forward")
        mot = replies(lines, "MOTORS")
        check(bool(mot) and mot[-1][1] == "[MOTORS," + ",".join([str(n)] + names) + "]",
              f"<I> reports {mot[-1][1] if mot else None}")
        check(any(b == "[ERR,BAD_V]" for _, b in lines), "a <V> with the wrong count is rejected")
        check(any(b.startswith("[ERR,UNKNOWN") for _, b in lines), "an unknown command is rejected")
        odo = replies(lines, "ODOM")
        check(bool(odo) and all(abs(float(x)) < 1e-3 for x in odo[-1][1].strip("[]").split(",")[1:]),
              "<R> zeroes the wheel angles")
        rows = telemetry(lines, n)
        late = [v for t, v in rows if t > 2800]
        # Tolerance = one encoder count seen through the firmware's velocity window.
        cpr = min(float(w.get("counts_per_rev") if w.get("counts_per_rev") not in (None, "auto") else
                        w["encoder_ppr"] * w.get("encoder_decoding", 4) * w.get("gear_ratio", 1))
                  for w in cfg["wheels"])
        hz = float(cfg["mcu"].get("control_hz", 100))
        q1 = 2 * 3.14159265 / (cpr / hz)
        quantum = q1 / max(1, min(8, -(-q1 // 0.05)))
        check(late and all(abs(v[1 + 3 * i + 1]) <= quantum + 0.01 for v in late for i in range(n)),
              "status queries (<?> every 100 ms) do NOT keep the robot moving: watchdog still stops it")

print()
if FAILS:
    print(f"{len(FAILS)} FAILED")
    sys.exit(1)
print("all firmware simulation checks passed")
