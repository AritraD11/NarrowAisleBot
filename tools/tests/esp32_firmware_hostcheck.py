#!/usr/bin/env python3
"""esp32_firmware_hostcheck.py — build the real firmware on this PC, step it,
and push what it prints through the real Pi-side parser.

WHY THIS EXISTS. There is no ESP32 toolchain on the machines this repo is
usually edited from, and the robot is the only place the firmware runs.
A firmware change that doesn't compile costs a flash cycle; one that
compiles but prints a line the bridge misreads costs a drive. This test
closes both gaps as far as a PC can:

  1. compiles aislebot_esp32.ino, unmodified, against the host stand-ins
     in tools/tests/esp32_fw_host/stubs/ as C++23 with -Wall -Wextra
     -Werror (arduino-esp32 3.x builds sketches as gnu++2b, and its
     "More"/"All" warning settings turn -Wall into errors)
  2. runs host_check.cpp: the IMU init/decode/recovery logic against a
     BNO055 register model, the v3.2 calibration-profile save/restore
     against an in-memory NVS (stubs/Preferences.h), the telemetry bytes
     against v3.0's, the watchdog rule, and every status line's
     comma-field count
  3. takes the [IMU] lines the firmware actually printed and feeds them
     to the shipped esp32_bridge.parse_esp32_line(), the way
     dashboard_html_syntax.py tests the string Python actually produces
     rather than the source text
  4. compiles firmware/nab_imu_i2c_scan_esp32.ino and runs it through every
     wiring fault it should recognise (open SDA or SCL, crossed wires, ADR
     high, a wire on the wrong pin, no power), asserting the verdict text
  5. compiles firmware/nab_imu_function_test_esp32.ino and runs every command
     against a BNO055 model whose data registers follow the fake clock:
     healthy board, then each fault it should catch (wrong chip ID, failed
     self test, gyro offset, wrong gyro scale, flipped gyro sign, dead or
     flipped accelerometer axis, a chip that stops answering)

What it can't do: catch an API that differs on the real arduino-esp32
core, or anything about the real chip or timing. After flashing, read the
boot banner and <N?> on the robot.

    python3 tools/tests/esp32_firmware_hostcheck.py     # repo root, needs g++
"""
import ast
import math
import shutil
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path

HOST = Path('tools/tests/esp32_fw_host')
BRIDGE = Path('src/mecanum_robot/mecanum_robot/esp32_bridge.py')
_fails = []


def chk(cond, label):
    print(f'  {"PASS" if cond else "FAIL"}  {label}')
    if not cond:
        _fails.append(label)


if not (HOST / 'host_check.cpp').exists() or not BRIDGE.exists():
    sys.exit('run me from the repo root')
gxx = shutil.which('g++')
if not gxx:
    sys.exit('g++ not found')

print('build')
with tempfile.TemporaryDirectory() as tmp:
    exe = Path(tmp) / 'host_check'
    cmd = [gxx, '-std=gnu++2b', '-Wall', '-Wextra', '-Werror',
           '-I', str(HOST / 'stubs'), str(HOST / 'host_check.cpp'), '-o', str(exe)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    chk(r.returncode == 0, 'aislebot_esp32.ino compiles as C++23 with -Wall -Wextra -Werror')
    if r.returncode != 0:
        print(r.stderr[-4000:])
        sys.exit(1)
    r = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
out = r.stdout
print(out, end='')
chk(r.returncode == 0, 'host_check: every firmware check passed')

print('IMU I2C scan sketch (firmware/nab_imu_i2c_scan_esp32.ino)')
with tempfile.TemporaryDirectory() as tmp:
    exe = Path(tmp) / 'scan_check'
    cmd = [gxx, '-std=gnu++2b', '-Wall', '-Wextra', '-Werror',
           '-I', str(HOST / 'stubs'), str(HOST / 'scan_check.cpp'), '-o', str(exe)]
    r2 = subprocess.run(cmd, capture_output=True, text=True)
    chk(r2.returncode == 0, 'scan sketch compiles as C++23 with -Wall -Wextra -Werror')
    if r2.returncode != 0:
        print(r2.stderr[-3000:])
        sys.exit(1)
    r2 = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
print(r2.stdout, end='')
chk(r2.returncode == 0, 'scan_check: every wiring-fault verdict is right')

print('IMU function test sketch (firmware/nab_imu_function_test_esp32.ino)')
with tempfile.TemporaryDirectory() as tmp:
    exe = Path(tmp) / 'imu_test_check'
    cmd = [gxx, '-std=gnu++2b', '-Wall', '-Wextra', '-Werror',
           '-I', str(HOST / 'stubs'), str(HOST / 'imu_test_check.cpp'), '-o', str(exe)]
    r3 = subprocess.run(cmd, capture_output=True, text=True)
    chk(r3.returncode == 0, 'function-test sketch compiles as C++23 with -Wall -Wextra -Werror')
    if r3.returncode != 0:
        print(r3.stderr[-3000:])
        sys.exit(1)
    r3 = subprocess.run([str(exe)], capture_output=True, text=True, timeout=120)
print(r3.stdout, end='')
chk(r3.returncode == 0, 'imu_test_check: every function-test verdict is right')

print('firmware [IMU] lines through the shipped bridge parser')
imu_lines = [ln[len('IMU_LINE:'):].strip() for ln in out.splitlines()
             if ln.startswith('IMU_LINE:')]
chk(len(imu_lines) == 2, 'two [IMU] lines captured from the firmware')

tree = ast.parse(BRIDGE.read_text(encoding='utf-8'))
cls = next(n for n in ast.walk(tree)
           if isinstance(n, ast.ClassDef) and n.name == 'ESP32Bridge')
funcs = [n for n in cls.body if isinstance(n, ast.FunctionDef)
         and n.name not in {'__init__', 'destroy_node'}]


class Msg:
    def __init__(self):
        self.data = None


class Imu:
    def __init__(self):
        self.header = types.SimpleNamespace(stamp=None, frame_id=None)
        self.orientation = types.SimpleNamespace()
        self.angular_velocity = types.SimpleNamespace()
        self.linear_acceleration = types.SimpleNamespace()
        self.orientation_covariance = [0.0] * 9
        self.angular_velocity_covariance = [0.0] * 9
        self.linear_acceleration_covariance = [0.0] * 9


ns = {'Float64MultiArray': Msg, 'String': Msg, 'Imu': Imu, 'math': math, 'time': time}
exec(compile(ast.Module(body=funcs, type_ignores=[]), str(BRIDGE), 'exec'), ns)

log = []


class Pub:
    def __init__(self, topic):
        self.topic = topic

    def publish(self, msg):
        log.append((self.topic, msg))


b = types.SimpleNamespace()
for f in funcs:
    setattr(b, f.name, types.MethodType(ns[f.name], b))
b.enable_imu = True
b.imu_rate_hz = 50.0
b.imu_gyro_var, b.imu_accel_var, b.imu_orient_var = 3e-5, 1e-2, 1e-3
b.actual_speeds = [0.0] * 4
b.pub_telemetry_raw = Pub('raw')
b.telemetry_pub = Pub('/motor_telemetry')
b.pub_actual = Pub('/wheel_velocities_actual')
b.pub_imu = Pub('/imu/data')
b.get_clock = lambda: types.SimpleNamespace(now=lambda: types.SimpleNamespace(to_msg=lambda: 'T'))

for ln in imu_lines:
    b.parse_esp32_line(ln)
imus = [m for t, m in log if t == '/imu/data']
chk(len(imus) == len(imu_lines), 'every firmware [IMU] line became one Imu message')
chk(not [m for t, m in log if t in ('/wheel_velocities_actual', '/motor_telemetry', 'raw')],
    'nothing leaked onto wheel speeds, motor telemetry or the raw topic')


def close(a, b_, tol):
    return all(abs(x - y) <= tol for x, y in zip(a, b_))


# What host_check.cpp put in the registers, in SI units. Tolerances are one
# register LSB: 1/16384 for q, 1/900 rad/s for gyro, 0.01 m/s^2 for accel.
expected = [
    ((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.2), (0.0, 0.0, 9.81)),
    ((11585 / 16384, 0.0, 0.0, 11585 / 16384), (-90 / 900, 45 / 900, -270 / 900),
     (0.12, -0.05, 9.79)),
]
for k, (m, (q, g, a)) in enumerate(zip(imus, expected), start=1):
    got_q = (m.orientation.w, m.orientation.x, m.orientation.y, m.orientation.z)
    got_g = (m.angular_velocity.x, m.angular_velocity.y, m.angular_velocity.z)
    got_a = (m.linear_acceleration.x, m.linear_acceleration.y, m.linear_acceleration.z)
    chk(close(got_q, q, 1 / 16384), f'sample {k}: quaternion survives firmware print + bridge parse')
    chk(close(got_g, g, 1 / 900), f'sample {k}: gyro (rad/s) survives')
    chk(close(got_a, a, 0.0101), f'sample {k}: accel (m/s^2) survives')
    chk(m.header.frame_id == 'imu_link', f'sample {k}: frame_id imu_link')

print()
if _fails:
    print(f'{len(_fails)} FAILED:')
    for f in _fails:
        print('  -', f)
    sys.exit(1)
print('all checks passed')
