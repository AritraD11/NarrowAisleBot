#!/usr/bin/env python3
"""Kinematics checks. Standard library only:  python3 tests/test_kinematics.py

What this proves:
  1. Differential drive matches the textbook formula.
  2. Mecanum matches the textbook formula, and reproduces NarrowAisleBot's
     asymmetric IK exactly (the equations in aislebot_esp32.ino).
  3. forward(inverse(q)) == q for every drive type (the odometry is the true
     inverse of the command path).
  4. A non-holonomic base reports vy = 0 and ignores commanded vy.
  5. scale_to_limit keeps the ratio between wheels.
  6. The odometry integrator closes a square.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ros2", "robot_base"))

from robot_base.kinematics import Wheel, DriveModel, OdometryIntegrator  # noqa: E402

FAILS = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def close(a, b, tol=1e-9):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


print("differential")
r, T = 0.05, 0.30
diff = DriveModel([Wheel("left", 0, T / 2), Wheel("right", 0, -T / 2)], r, False)
vx, wz = 0.2, 0.7
wl, wr = diff.inverse(vx, 0.0, wz)
check(close([wl, wr], [(vx - wz * T / 2) / r, (vx + wz * T / 2) / r]),
      "IK: left = (v - w T/2)/r, right = (v + w T/2)/r")
check(close(diff.forward([wl, wr]), (vx, 0.0, wz)), "FK inverts IK")
check(close(diff.inverse(vx, 0.5, wz), [wl, wr]), "commanded vy ignored")

print("mecanum, symmetric")
lx, ly = 0.2, 0.15
mec = DriveModel([Wheel("front_left", lx, ly, 1, -1), Wheel("front_right", lx, -ly, 1, 1),
                  Wheel("rear_left", -lx, ly, 1, 1), Wheel("rear_right", -lx, -ly, 1, -1)],
                 r, True)
q = (0.1, -0.07, 0.4)
k = lx + ly
expect = [(q[0] - q[1] - k * q[2]) / r, (q[0] + q[1] + k * q[2]) / r,
          (q[0] + q[1] - k * q[2]) / r, (q[0] - q[1] + k * q[2]) / r]
check(close(mec.inverse(*q), expect), "IK matches the textbook mecanum formula")
check(close(mec.forward(mec.inverse(*q)), q), "FK inverts IK")
w = mec.inverse(*q)
fk_textbook = (r / 4 * (w[0] + w[1] + w[2] + w[3]),
               r / 4 * (-w[0] + w[1] + w[2] - w[3]),
               r / (4 * k) * (-w[0] + w[1] - w[2] + w[3]))
check(close(mec.forward(w), fk_textbook), "least squares FK equals the textbook sum/4 form")
check(mec.sign_pattern(0, 0, 1) == [-1, 1, -1, 1], "spin in place: left side back, right side forward")
check(mec.sign_pattern(0, 1, 0) == [-1, 1, 1, -1], "strafe left: FL and RR backwards")

print("mecanum, NarrowAisleBot asymmetric geometry (order FR, FL, RR, RL)")
R, L1, L2, D = 0.0762, 0.403, 0.333, 0.15769
nab = DriveModel([Wheel("FR", L1, -D, 1, 1), Wheel("FL", L2, D, 1, -1),
                  Wheel("RR", -L2, -D, 1, -1), Wheel("RL", -L1, D, 1, 1)], R, True)
KO, KI = L1 + D, L2 + D
for q in [(0.1, 0, 0), (0, 0.1, 0), (0, 0, 0.3), (0.05, -0.08, 0.2)]:
    vx, vy, wz = q
    esp32 = [(vx + vy + wz * KO) / R, (vx - vy - wz * KI) / R,
             (vx - vy + wz * KI) / R, (vx + vy - wz * KO) / R]
    check(close(nab.inverse(*q), esp32, 1e-12), f"IK equals aislebot_esp32.ino mecanumIK for {q}")
    check(close(nab.forward(nab.inverse(*q)), q, 1e-9), f"FK inverts IK for {q}")

print("skid steer, 4 wheels, track scale 1.3")
sk = DriveModel([Wheel("front_left", 0.15, 0.2), Wheel("front_right", 0.15, -0.2),
                 Wheel("rear_left", -0.15, 0.2), Wheel("rear_right", -0.15, -0.2)],
                0.06, False, track_width_scale=1.3)
q = (0.15, 0.0, 0.5)
w = sk.inverse(*q)
check(abs(w[0] - (0.15 - 0.5 * 0.2 * 1.3) / 0.06) < 1e-9, "track scale widens the effective lever arm")
check(close(sk.forward(w), q), "FK inverts IK with the scale applied both ways")

print("omni, three wheels at 120 deg")
om = []
for i, a in enumerate((90, 210, 330)):
    th = math.radians(a)
    x, y = 0.15 * math.cos(th), 0.15 * math.sin(th)
    d = th + math.pi / 2                 # drive direction tangent to the circle
    om.append(Wheel(f"w{i}", x, y, math.cos(d), math.sin(d)))
omni = DriveModel(om, 0.03, True)
q = (0.12, -0.05, 0.6)
check(close(omni.forward(omni.inverse(*q)), q), "FK inverts IK")

print("lateral scale")
mec_s = DriveModel(mec.wheels, r, True, lateral_scale=0.92)
fx, fy, fz = mec_s.forward(mec_s.inverse(0, 0.1, 0))
check(abs(fy - 0.092) < 1e-12 and abs(fx) < 1e-12, "odometry vy is multiplied by lateral_scale")

print("limits")
s = DriveModel.scale_to_limit([2.0, -8.0, 4.0], 4.0)
check(close(s, [1.0, -4.0, 2.0]), "scale_to_limit keeps wheel ratios")
check(DriveModel.scale_to_limit([1.0, -2.0], 4.0) == [1.0, -2.0], "no scaling under the limit")

print("odometry integrator, 1 m square with 90 deg left turns")
odo = OdometryIntegrator()
for _ in range(4):
    for _ in range(100):
        odo.step(0.01, 0.0, 0.0)
    for _ in range(90):
        odo.step(0.0, 0.0, math.radians(1.0))
check(abs(odo.x) < 1e-9 and abs(odo.y) < 1e-9 and abs(odo.theta) < 1e-9, "closes to the start")
odo.reset()
for _ in range(1000):                      # a quarter circle of radius 1 m
    odo.step(math.pi / 2 / 1000, 0.0, math.pi / 2 / 1000)
check(abs(odo.x - 1.0) < 1e-6 and abs(odo.y - 1.0) < 1e-6, "arc ends at (1, 1)")

print()
if FAILS:
    print(f"{len(FAILS)} FAILED")
    sys.exit(1)
print("all kinematics checks passed")
