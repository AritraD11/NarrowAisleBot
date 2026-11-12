#!/usr/bin/env python3
"""scan_math, list_usb_serial and the protocol helpers:  python3 tests/test_scan_and_tools.py"""
import math
import os
import subprocess
import sys
import tempfile

KIT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(KIT, "ros2", "robot_base"))
from robot_base import scan_math as S  # noqa: E402
from robot_base import protocol as P  # noqa: E402

FAILS = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


print("scan_math")
check(S.in_arc(170, 135, 225) and S.in_arc(-170, 135, 225) and not S.in_arc(0, 135, 225),
      "in_arc wraps across +/-180")
check(S.in_arc(-90, -135, -45) and not S.in_arc(90, -135, -45), "in_arc, plain arc")
n = 360
inc = 2 * math.pi / n
amin = -math.pi
ranges = [1.0 + k / 1000 for k in range(n)]
r2, _, mn, mx = S.mirror(ranges, [], amin, amin + inc * (n - 1))
# beam that was reported at angle a must now sit at -a
k = 100
a_rep = amin + k * inc
k_new = round((-a_rep - mn) / inc)
check(abs(r2[k_new] - ranges[k]) < 1e-12, "mirror puts the beam reported at a at exactly -a")
r3, _, mn3, mx3 = S.mirror(*S.mirror(ranges, [], amin, amin + inc * (n - 1))[0:1], [], mn, mx)
check(r3 == ranges and abs(mn3 - amin) < 1e-12, "mirror twice is the identity")
masked, cnt = S.apply_mask(ranges, amin, inc, [(135, 225)])
check(abs(cnt - 91) <= 1 and all(math.isnan(masked[k]) for k in (0, 1, 359)) and not math.isnan(masked[180]),
      f"mask [135, 225] blanks the rear quarter ({cnt} beams) and only it")
check(S.pairs([1, 2, 3, 4]) == [(1.0, 2.0), (3.0, 4.0)], "pairs() from the flat parameter list")
pts = S.scan_to_points([1.0, float("nan"), 0.05, 2.0], 0.0, math.pi / 2, 0.1, 10.0)
check(len(pts) == 2 and abs(pts[0][0] - 1.0) < 1e-12 and abs(pts[1][1] + 2.0) < 1e-9 and abs(pts[1][0]) < 1e-9,
      "scan_to_points skips NaN and short returns")

print("protocol")
check(P.cmd_velocity([1, -2.5]) == "<V,1.000,-2.500>", "velocity command")
check(P.cmd_pwm([10.4, -3.6]) == "<M,10,-4>", "PWM command rounds")
t = P.parse_telemetry("1234,1.0,0.9,40,-1.0,-0.95,-41", 2)
check(t is not None and t.actual == [0.9, -0.95] and not t.extended, "basic telemetry parsed")
t = P.parse_telemetry("1234,1,0.9,40,-1,-0.95,-41,0.1,30,10,5.5,-0.05,-30,-11,-5.5", 2)
check(t is not None and t.extended and t.pos_rad == [5.5, -5.5], "extended telemetry parsed")
check(P.parse_telemetry("1234,1,2,3", 2) is None, "wrong column count rejected")
check(P.parse_telemetry("[OK,ENABLED]", 2) is None, "reply is not telemetry")
check(P.parse_reply("[MOTORS,2,left,right]") == ("MOTORS", ["2", "left", "right"]), "reply parsed")


class Tel:
    def __init__(self, ms):
        self.mcu_ms = ms


rows = [(100.000 + k * 0.02 + (0.03 if k % 5 == 0 else 0.002), Tel(5000 + 20 * k)) for k in range(50)]
al = P.align_to_mcu_clock(rows)
gaps = [al[k + 1][0] - al[k][0] for k in range(len(al) - 1)]
check(all(abs(g - 0.02) < 1e-9 for g in gaps), "MCU-clock alignment removes 30 ms delivery jitter")

print("list_usb_serial.py on a fake /sys")
with tempfile.TemporaryDirectory() as root:
    def mkdev(port, intf, tty, vid, pid, serial, acm=False):
        usb = os.path.join(root, "sys/devices/platform/usb1", port)
        os.makedirs(usb, exist_ok=True)
        for k, v in (("idVendor", vid), ("idProduct", pid), ("serial", serial), ("product", "X")):
            open(os.path.join(usb, k), "w").write(v + "\n")
        if acm:
            devdir = os.path.join(usb, intf)
            ttydir = os.path.join(devdir, "tty", tty)
        else:
            devdir = os.path.join(usb, intf, tty)
            ttydir = os.path.join(devdir, "tty", tty)
        os.makedirs(ttydir, exist_ok=True)
        os.symlink(devdir, os.path.join(ttydir, "device"))
        os.makedirs(os.path.join(root, "sys/class/tty"), exist_ok=True)
        os.symlink(ttydir, os.path.join(root, "sys/class/tty", tty))
        os.makedirs(os.path.join(root, "dev"), exist_ok=True)
        open(os.path.join(root, "dev", tty), "w").close()
    mkdev("4-1", "4-1:1.0", "ttyUSB0", "10c4", "ea60", "0001")
    mkdev("2-2", "2-2:1.0", "ttyUSB1", "10c4", "ea60", "0001")
    mkdev("1-1.3", "1-1.3:1.0", "ttyACM0", "2341", "0042", "8573", acm=True)
    os.symlink(os.path.join(root, "dev", "ttyUSB0"), os.path.join(root, "dev", "esp32"))
    out = subprocess.run([sys.executable, os.path.join(KIT, "setup", "list_usb_serial.py"), "--root", root],
                         capture_output=True, text=True).stdout
    check(out.count("usb_vendor_id") == 3, "finds ttyUSB and ttyACM devices")
    check('this socket is "4-1"' in out and 'this socket is "1-1.3"' in out, "reports the physical port path")
    check("SAME vendor, product and serial" in out, "warns about the two identical CP2102s")
    check("already linked as: /dev/esp32" in out, "shows an existing udev symlink")

print()
if FAILS:
    print(f"{len(FAILS)} FAILED")
    sys.exit(1)
print("all scan/protocol/tool checks passed")
