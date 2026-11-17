#!/usr/bin/env python3
"""esp32_bridge_imu_parse.py — does an IMU line stay out of the wheel data?

WHY THIS EXISTS. esp32_bridge.parse_esp32_line() reads every line the ESP32
prints. The wheel-speed fallback in it accepts any line with a comma, nine or
more fields and a non-digit first field. An `[IMU]qw,qx,qy,qz,gx,gy,gz,ax,ay,az`
line is exactly that: ten comma-separated fields, first one `[IMU]0.99`.

Before the fix, the first IMU line on the wire was published on
/wheel_velocities_actual as four "wheel speeds" taken from fields 2, 4, 6 and 8
(a quaternion component, a gyro rate, a gyro rate, an acceleration).
odometry_publisher integrates that topic, so the pose would have been
corrupted at the IMU rate, and `enable_imu` False did not prevent it.

Nothing about that raises. It would show up on the floor as odometry that
walks while the robot sits still.

    python3 tools/tests/esp32_bridge_imu_parse.py      # from the repo root

Extracts the shipped ESP32Bridge methods with ast and drives them against
stubs, so there is no rclpy import, no ROS and no serial port, and no second
copy of the parsing logic to drift out of step with the real one.
"""
import ast
import math
import sys
import time
import types
from pathlib import Path

SRC = Path('src/mecanum_robot/mecanum_robot/esp32_bridge.py')
_fails = []


def chk(cond, label):
    print(f'  {"PASS" if cond else "FAIL"}  {label}')
    if not cond:
        _fails.append(label)


if not SRC.exists():
    sys.exit(f'run me from the repo root; {SRC} not found')

tree = ast.parse(SRC.read_text(encoding='utf-8'))
cls = next((n for n in ast.walk(tree)
            if isinstance(n, ast.ClassDef) and n.name == 'ESP32Bridge'), None)
if cls is None:
    sys.exit('class ESP32Bridge not found in esp32_bridge.py')

# Every method except the two that call super(), which needs the real class.
SKIP = {'__init__', 'destroy_node'}
funcs = [n for n in cls.body
         if isinstance(n, ast.FunctionDef) and n.name not in SKIP]
if 'parse_esp32_line' not in {f.name for f in funcs}:
    sys.exit('parse_esp32_line not found in ESP32Bridge')


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


ns = {'Float64MultiArray': Msg, 'String': Msg, 'Imu': Imu, 'math': math,
      'time': time}
exec(compile(ast.Module(body=funcs, type_ignores=[]), str(SRC), 'exec'), ns)


class Pub:
    def __init__(self, topic, log):
        self.topic, self.log = topic, log

    def publish(self, msg):
        self.log.append((self.topic, msg))


def make_bridge(enable_imu):
    b = types.SimpleNamespace()
    for f in funcs:
        setattr(b, f.name, types.MethodType(ns[f.name], b))
    log = []
    b.enable_imu = enable_imu
    b.imu_rate_hz = 50.0
    b.imu_gyro_var, b.imu_accel_var, b.imu_orient_var = 3e-5, 1e-2, 1e-3
    b.actual_speeds = [0.0] * 4
    b.pub_telemetry_raw = Pub('raw', log)
    b.telemetry_pub = Pub('/motor_telemetry', log)
    b.pub_actual = Pub('/wheel_velocities_actual', log)
    b.pub_imu = Pub('/imu/data', log)
    b.get_clock = lambda: types.SimpleNamespace(
        now=lambda: types.SimpleNamespace(to_msg=lambda: 'T'))
    return b, log


def on(log, topic):
    return [m for t, m in log if t == topic]


# Distinct values per field, so a wrong index cannot pass by coincidence.
TEL = '123456,1.0,1.1,10,2.0,2.1,20,3.0,3.1,30,4.0,4.1,40'
TEL_ACTUAL = [1.1, 2.1, 3.1, 4.1]          # fields 2, 5, 8, 11
IMU = '[IMU]0.9,0.1,0.2,0.3,0.01,0.02,0.2,0.5,0.6,9.8'

print('wheel telemetry, unchanged')
b, log = make_bridge(False)
b.parse_esp32_line(TEL)
chk(len(on(log, '/motor_telemetry')) == 1, 'one /motor_telemetry message')
chk(on(log, '/motor_telemetry')[0].data[:3] == [1.0, 1.1, 10.0],
    '/motor_telemetry carries the 12 motor values')
chk(len(on(log, '/wheel_velocities_actual')) == 1
    and on(log, '/wheel_velocities_actual')[0].data == TEL_ACTUAL,
    'wheel speeds taken from fields 2, 5, 8, 11')

print('IMU line, enable_imu True')
b, log = make_bridge(True)
b.parse_esp32_line(IMU)
msgs = on(log, '/imu/data')
chk(len(msgs) == 1, 'one /imu/data message')
chk(not on(log, '/wheel_velocities_actual'),
    'nothing reaches /wheel_velocities_actual')
chk(not on(log, '/motor_telemetry'), 'nothing reaches /motor_telemetry')
if msgs:
    m = msgs[0]
    chk(m.header.frame_id == 'imu_link', 'frame_id is imu_link')
    chk((m.orientation.w, m.orientation.x, m.orientation.y, m.orientation.z)
        == (0.9, 0.1, 0.2, 0.3), 'quaternion order is w, x, y, z')
    chk((m.angular_velocity.x, m.angular_velocity.y, m.angular_velocity.z)
        == (0.01, 0.02, 0.2), 'angular velocity order is gx, gy, gz')
    chk((m.linear_acceleration.x, m.linear_acceleration.y,
         m.linear_acceleration.z) == (0.5, 0.6, 9.8),
        'linear acceleration order is ax, ay, az')

print('IMU line, enable_imu False (the default)')
b, log = make_bridge(False)
b.parse_esp32_line(IMU)
chk(not on(log, '/wheel_velocities_actual'),
    'nothing reaches /wheel_velocities_actual')
chk(not on(log, '/motor_telemetry'), 'nothing reaches /motor_telemetry')
chk(not on(log, '/imu/data'), 'nothing published on /imu/data')

print('interleaved, as on the real wire (wheels 20 Hz, IMU 100 Hz)')
b, log = make_bridge(True)
for line in (TEL, IMU, IMU, IMU, IMU, IMU, TEL):
    b.parse_esp32_line(line)
chk(len(on(log, '/wheel_velocities_actual')) == 2
    and all(m.data == TEL_ACTUAL for m in on(log, '/wheel_velocities_actual')),
    'two wheel-speed messages, both the real wheel values')
chk(len(on(log, '/imu/data')) == 5, 'five IMU messages')

print('malformed IMU lines')
for bad in ('[IMU]', '[IMU]0.9,0.1,0.2', '[IMU]a,b,c,d,e,f,g,h,i,j'):
    b, log = make_bridge(True)
    try:
        b.parse_esp32_line(bad)
        raised = False
    except Exception:
        raised = True
    chk(not raised, f'{bad!r} does not raise')
    chk(not on(log, '/wheel_velocities_actual') and not on(log, '/imu/data'),
        f'{bad!r} publishes nothing structured')

print('other bracketed lines from the firmware')
for line in ('[READY]', '[PONG]', '[TRIP,STALL,FR,pwm=255,vel=0.000]'):
    b, log = make_bridge(True)
    b.parse_esp32_line(line)
    chk(not on(log, '/wheel_velocities_actual') and not on(log, '/imu/data'),
        f'{line!r} publishes nothing structured')

print('firmware v3.1 additions')
IMU11 = IMU + ',3313000'
b, log = make_bridge(True)
b.parse_esp32_line(IMU11)
msgs = on(log, '/imu/data')
chk(len(msgs) == 1, '11-field [IMU] line (with t_us) is accepted')
chk(not on(log, 'raw'), '[IMU] lines are not republished on motor_telemetry_raw')
if msgs:
    m = msgs[0]
    chk([m.angular_velocity_covariance[i] for i in (0, 4, 8)] == [3e-5] * 3
        and m.angular_velocity_covariance[1] == 0.0,
        'gyro covariance diagonal set, off-diagonal zero')
    chk([m.linear_acceleration_covariance[i] for i in (0, 4, 8)] == [1e-2] * 3,
        'accel covariance diagonal set')
    chk([m.orientation_covariance[i] for i in (0, 4, 8)] == [1e-3] * 3,
        'orientation covariance diagonal set')
for line in ('[IMUS,RUN,cal=s0g3a1m0,sys=5,err=0,T=25C,sw=0x0311]',
             '[IMUC,n=1200,i2c=0,bad=0,dup=3,reinit=0]',
             '[IMUS,UP,chip=0xA0,sw=0x0311,sys=5]',
             '[IMUS,DOWN,i2c_fails=5]',
             '[IMUCFG,addr=0x28,mode=0x08,axis=0x24/0x00,xtal=0,rst=27]',
             '[OK,IMU_STREAM=1,HZ=50.0]'):
    b, log = make_bridge(True)
    b.parse_esp32_line(line)
    chk(not on(log, '/wheel_velocities_actual') and not on(log, '/imu/data'),
        f'{line[:28]!r}... publishes nothing structured')
b, _ = make_bridge(True)
chk(b._imu_stream_cmd() == '<N1,50>', 'enable_imu True asks for <N1,50>')
b, _ = make_bridge(False)
chk(b._imu_stream_cmd() == '<N0>', 'enable_imu False sends <N0>')

print()
if _fails:
    print(f'{len(_fails)} FAILED:')
    for f in _fails:
        print('  -', f)
    sys.exit(1)
print('all checks passed')
