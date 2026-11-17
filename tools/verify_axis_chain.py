#!/usr/bin/env python3
"""
verify_axis_chain.py -- prove, without hardware, that a keypress moves the
robot the way the map says it does, and that every file that carries an axis
agrees about which way "forward" is.

THE CONVENTION THIS FILE GUARDS (standard, REP-103, since 5 Oct 2026)

        base_link, odom, map:   +X = NOSE (forward)   +Y = LEFT   +Z = UP
        yaw = angle of the nose from map +X, counterclockwise positive

    Until 5 Oct 2026 this robot ran +X = RIGHT, +Y = NOSE (a LiDAR labelling
    choice from 11 Aug, Research_Journal.md 17.9 and 17.10) and this file
    guarded that. docs/Axis_Convention.md has the history and the
    old-to-new conversion. The wheel kinematics and the dashboard joystick
    were standard all along, which is why the refactor mostly deleted
    conversions.

WHY THIS EXISTS
    The axis convention has been re-derived, re-argued and re-broken more
    times than any other single fact in the project (17.10, 17.12, 17.19,
    17.20, 17.36, 17.37, 17.38). Every round ended in prose, and prose does
    not fail a build when someone edits the code out from under it. This
    does. It runs the ACTUAL arithmetic from the drive chain end to end and
    asserts the four statements the operator cares about:

        W (forward)      -> map +X
        S (backward)     -> map -X
        D (strafe right) -> map -Y
        A (strafe left)  -> map +Y

    It then reads the files themselves (odometry, LiDAR relay, URDF,
    footprints, dashboard constants, goal and zero-mark tools) and fails if
    any of them still describes the other convention. Nothing is
    transcribed where it can be parsed: copied arithmetic drifts, and drift
    is the failure mode being guarded.

WHAT IT SIMULATES
    keypress -> phone_dashboard sendDrive() -> /cmd_vel_manual -> twist_mux
    -> mecanum_teleop_asymmetric.compute_wheel_speeds() -> wheel speeds ->
    odometry_publisher forward kinematics -> integration -> published
    odom->base_link -> (map->odom = identity at SLAM start) -> map frame.

WHAT IT DOES NOT SIMULATE, DELIBERATELY
    Wheel slip, roller scrub beyond the modelled lateral_scale, encoder
    noise, loop closure, and the LiDAR hardware. This answers "do the axes
    agree", not "is the odometry accurate". Magnitudes are checked only for
    sign and dominant axis.

USAGE
    python3 tools/verify_axis_chain.py           # run everything
    python3 tools/verify_axis_chain.py -v        # show the numbers

    Pure standard library. No ROS, no hardware, no network.
"""

import ast
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def P(*parts):
    return os.path.join(REPO, *parts)


ODOM_SRC = P('src/mecanum_robot/mecanum_robot/odometry_publisher.py')
TELEOP_SRC = P('src/mecanum_robot/mecanum_robot/mecanum_teleop_asymmetric.py')
DASH_SRC = P('src/mecanum_robot/mecanum_robot/phone_dashboard.py')
GOAL_SRC = P('src/mecanum_navigation/mecanum_navigation/goal_pose_adapter.py')
ADAPTER_SRC = P('src/mecanum_navigation/mecanum_navigation/cmd_vel_axis_adapter.py')
RELAY_SRC = P('src/scan_relay/scan_relay.py')
URDF_SRC = P('src/mecanum_robot/urdf/aislebot.urdf')
NAV2_SRC = P('src/mecanum_navigation/config/nav2_params.yaml')
NAV_LAUNCHES = [P('src/mecanum_navigation/launch/nav2_slam.launch.py'),
                P('src/mecanum_navigation/launch/navigation.launch.py')]
# ZERO_POINT_YAW has moved between launch files before (1 Sep, 17.49). Search
# both rather than pinning to whichever holds it today.
LAUNCH_SRCS = [P('src/mecanum_robot/launch/sensors.launch.py'),
               P('src/mecanum_robot/launch/mapping_full.launch.py')]
# Every tool that converts "N m right / N m forward" into a map offset.
BODY_TO_MAP_TOOLS = [P('tools/nav_goal.py'), P('tools/zero_point_scan.py'),
                     P('tools/repeatability_test.py'), P('tools/trajectory_viz.py')]

# ── Geometry ─────────────────────────────────────────────────────────────
# These mirror the declare_parameter() defaults in the nodes.
# check_parameter_defaults() reads the real defaults out of the source and
# fails if they have drifted from these.
WHEEL_R = 0.0762
L1 = 0.403
L2 = 0.333
D = 0.15769
LATERAL_SCALE = 0.92
MAX_WHEEL = 6.28

K_OUTER = L1 + D
K_INNER = L2 + D

VERBOSE = '-v' in sys.argv or '--verbose' in sys.argv


def read(path):
    with open(path, 'r', encoding='utf-8') as fh:
        return fh.read()


# ── The real arithmetic, transcribed from the nodes ──────────────────────

def dashboard_twist(key, speed=0.20):
    """phone_dashboard.py sendDrive(): vx = joyY, vy = -joyX (REP-103).

    W/S drive joyY, A/D drive joyX. Q/E are yaw and are NOT strafe -- the
    mix-up that produced a false alarm in 17.36.
    """
    kx = ky = kz = 0.0
    if key == 'w':
        ky = 1.0
    elif key == 's':
        ky = -1.0
    elif key == 'd':
        kx = 1.0
    elif key == 'a':
        kx = -1.0
    elif key == 'q':
        kz = 1.0
    elif key == 'e':
        kz = -1.0
    else:
        raise ValueError('unknown key: %r' % key)
    return (ky * speed, -kx * speed, kz * speed)


def teleop_inverse_kinematics(vx, vy, wz):
    """mecanum_teleop_asymmetric.compute_wheel_speeds(), REP-103 in."""
    inv_r = 1.0 / WHEEL_R
    speeds = [
        inv_r * (vx + vy + K_OUTER * wz),   # FR
        inv_r * (vx - vy - K_INNER * wz),   # FL
        inv_r * (vx - vy + K_INNER * wz),   # RR
        inv_r * (vx + vy - K_OUTER * wz),   # RL
    ]
    max_abs = max(abs(s) for s in speeds)
    if max_abs > MAX_WHEEL:
        speeds = [s * (MAX_WHEEL / max_abs) for s in speeds]
    return speeds


def odometry_forward_kinematics(w_fr, w_fl, w_rr, w_rl):
    """odometry_publisher.py forward kinematics. Internal REP-103."""
    vx = (WHEEL_R / 4.0) * (w_fr + w_fl + w_rr + w_rl)
    vy = (WHEEL_R / 4.0) * (w_fr - w_fl - w_rr + w_rl) * LATERAL_SCALE
    wz = (WHEEL_R / 4.0) * (
        w_fr / K_OUTER - w_fl / K_INNER + w_rr / K_INNER - w_rl / K_OUTER
    )
    return vx, vy, wz


class _Self(object):
    """Stands in for the node instance when evaluating its own expressions."""

    def __init__(self, x, y, theta):
        self.x, self.y, self.theta = x, y, theta


_PUB_NAMES = ('pub_x', 'pub_y', 'pub_theta', 'pub_vx', 'pub_vy')


def _extract_publish_exprs():
    """Pull the five pub_* right-hand sides straight out of odometry_publisher.

    Transcribing this arithmetic into the test would let the two drift apart.
    So the expressions are parsed from the real module and evaluated. Only
    these right-hand sides are compiled, from a file in this repo; nothing
    else in the module is executed, which is also why this needs no ROS.
    """
    tree = ast.parse(read(ODOM_SRC), ODOM_SRC)
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in _PUB_NAMES:
                expr = ast.Expression(body=node.value)
                ast.fix_missing_locations(expr)
                found[target.id] = compile(expr, ODOM_SRC, 'eval')
    missing = set(_PUB_NAMES) - set(found)
    if missing:
        raise SystemExit(
            'verify_axis_chain: could not find %s in %s -- the published-frame '
            'block has been restructured, update this parser before trusting '
            'any result below.' % (', '.join(sorted(missing)), ODOM_SRC))
    return found


_PUB_EXPRS = _extract_publish_exprs()


def publish_frame(x_int, y_int, theta_int, vx=0.0, vy=0.0):
    """odometry_publisher.py's published frame, read from source."""
    ns = {'self': _Self(x_int, y_int, theta_int), 'math': math,
          'vx': vx, 'vy': vy}
    return tuple(eval(_PUB_EXPRS[n], ns) for n in _PUB_NAMES)


def simulate(key, seconds=2.0, start_theta_int=0.0, dt=0.02, speed=0.20):
    """Run the whole chain and return the PUBLISHED (map-frame) pose delta."""
    vx_cmd, vy_cmd, wz_cmd = dashboard_twist(key, speed)
    wheels = teleop_inverse_kinematics(vx_cmd, vy_cmd, wz_cmd)

    x = y = 0.0
    theta = start_theta_int
    steps = int(round(seconds / dt))
    for _ in range(steps):
        vx, vy, wz = odometry_forward_kinematics(*wheels)
        half = wz * dt * 0.5
        cos_mid = math.cos(theta + half)
        sin_mid = math.sin(theta + half)
        x += (vx * cos_mid - vy * sin_mid) * dt
        y += (vx * sin_mid + vy * cos_mid) * dt
        theta += wz * dt
        theta = math.atan2(math.sin(theta), math.cos(theta))

    px0, py0, pth0, _, _ = publish_frame(0.0, 0.0, start_theta_int)
    px1, py1, pth1, _, _ = publish_frame(x, y, theta)
    return (px1 - px0, py1 - py0, pth1, pth0)


# ── Checks ───────────────────────────────────────────────────────────────

FAILURES = []


def check(name, condition, detail=''):
    if condition:
        print('  PASS  %s' % name)
    else:
        print('  FAIL  %s   %s' % (name, detail))
        FAILURES.append(name)


def check_operator_table():
    """The four statements the operator actually cares about."""
    print('\n[1] Operator table -- keypress to map axis, from the zero mark')
    cases = [
        ('w', 'forward', 'x', +1),
        ('s', 'backward', 'x', -1),
        ('d', 'strafe right', 'y', -1),
        ('a', 'strafe left', 'y', +1),
    ]
    for key, label, axis, sign in cases:
        dx, dy, _, _ = simulate(key)
        moved = dx if axis == 'x' else dy
        other = dy if axis == 'x' else dx
        if VERBOSE:
            print('        %s (%s): dmap = (%+.4f, %+.4f)' % (key.upper(), label, dx, dy))
        ok = (moved * sign > 0.01) and (abs(other) < 0.01 * max(abs(moved), 1e-9) + 1e-6)
        check('%s (%-12s) -> map %s%s' % (key.upper(), label, '+' if sign > 0 else '-', axis.upper()),
              ok, 'got dmap=(%+.4f, %+.4f)' % (dx, dy))


def check_zero_mark_yaw():
    """A freshly-zeroed robot on the mark must publish yaw 0."""
    print('\n[2] Published yaw at a freshly-zeroed odometry')
    _, _, _, pth0 = simulate('w', seconds=0.02)
    check('odom->base_link yaw == 0 deg on the mark',
          abs(pth0) < 1e-9, 'got %.4f deg' % math.degrees(pth0))


def check_general_invariant():
    """The property that must hold at EVERY heading, not just zero.

    A body-frame displacement of (forward, left) must land in the map as
    Rot(published_yaw) applied to (forward, left). If that holds for
    arbitrary headings then the frames genuinely agree; if it only holds at
    zero, we have coincidence, not correctness.
    """
    print('\n[3] Frame invariant at arbitrary headings')
    # (key, body-frame intent as (forward, left))
    intents = (('w', (1.0, 0.0)), ('d', (0.0, -1.0)), ('a', (0.0, 1.0)))
    for deg in (0, 30, 90, 137, -45, -90, 180):
        th = math.radians(deg)
        for key, body in intents:
            dx, dy, _, pth0 = simulate(key, seconds=2.0, start_theta_int=th)
            mag = math.hypot(dx, dy)
            if mag < 1e-9:
                check('heading %+4d deg, %s' % (deg, key.upper()), False, 'no motion')
                continue
            c, s = math.cos(pth0), math.sin(pth0)
            ex = body[0] * c - body[1] * s
            ey = body[0] * s + body[1] * c
            cos_err = (dx * ex + dy * ey) / mag
            if VERBOSE:
                print('        %+4d deg %s: dmap=(%+.4f,%+.4f) expected dir=(%+.3f,%+.3f)'
                      % (deg, key.upper(), dx, dy, ex, ey))
            check('heading %+4d deg, %s follows Rot(yaw)*(forward,left)' % (deg, key.upper()),
                  cos_err > 0.999, 'alignment %.6f' % cos_err)


def _load_body_to_map(path):
    """The real body_to_map() out of a tool, compiled alone (pure math)."""
    tree = ast.parse(read(path), path)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'body_to_map':
            ns = {'math': math}
            exec(compile(ast.Module(body=[node], type_ignores=[]), path, 'exec'), ns)
            return ns['body_to_map']
    return None


def check_body_to_map_agrees():
    """Every body_to_map() must agree with TF, parsed from the real tools."""
    print('\n[4] body_to_map() in the goal and scan tools agrees with TF')
    found = 0
    for path in BODY_TO_MAP_TOOLS:
        name = os.path.relpath(path, REPO)
        fn = _load_body_to_map(path)
        if fn is None:
            continue
        found += 1
        ok = True
        detail = ''
        for deg in (0, 45, -90, 160):
            yaw = math.radians(deg)
            # 1 m forward = along the nose = (cos, sin). 1 m right = -left.
            fx, fy = fn(0.0, 0.0, yaw, 0.0, 1.0)
            rx, ry = fn(0.0, 0.0, yaw, 1.0, 0.0)
            ex, ey = math.cos(yaw), math.sin(yaw)
            if abs(fx - ex) > 1e-9 or abs(fy - ey) > 1e-9:
                ok, detail = False, 'forward at %d deg: got (%.4f, %.4f) want (%.4f, %.4f)' % (deg, fx, fy, ex, ey)
            lx, ly = -math.sin(yaw), math.cos(yaw)     # left of the nose
            if abs(rx + lx) > 1e-9 or abs(ry + ly) > 1e-9:
                ok, detail = False, 'right at %d deg: got (%.4f, %.4f) want (%.4f, %.4f)' % (deg, rx, ry, -lx, -ly)
        gx, gy = fn(0.0, 0.0, 0.0, 0.0, 1.0)
        if abs(gx - 1.0) > 1e-12 or abs(gy) > 1e-12:
            ok, detail = False, 'at yaw 0, "1 m forward" gave (%.4f, %.4f), want (1, 0)' % (gx, gy)
        check('%s: forward = (cos, sin), right = -left, at yaw 0 forward is map +X' % name, ok, detail)
    check('at least three tools define body_to_map (found %d)' % found, found >= 3)


def check_parameter_defaults():
    """The constants above must match the nodes' real declare_parameter()."""
    print('\n[5] Geometry constants match the nodes source')
    src = read(ODOM_SRC)
    expected = {'wheel_radius': WHEEL_R, 'l1': L1, 'l2': L2, 'd': D,
                'lateral_scale': LATERAL_SCALE}
    for name, want in expected.items():
        m = re.search(r"declare_parameter\(\s*'%s'\s*,\s*([0-9.]+)" % re.escape(name), src)
        if not m:
            check('odometry_publisher %s default found' % name, False, 'not found')
            continue
        got = float(m.group(1))
        check('odometry_publisher %s == %g' % (name, want), abs(got - want) < 1e-12,
              'source says %g' % got)


# ── The files themselves ────────────────────────────────────────────────

def _urdf():
    root = ET.parse(URDF_SRC).getroot()
    joints = {}
    for j in root.iter('joint'):
        o = j.find('origin')
        a = j.find('axis')
        joints[j.get('name')] = {
            'xyz': tuple(float(v) for v in o.get('xyz').split()) if o is not None else None,
            'axis': tuple(float(v) for v in a.get('xyz').split()) if a is not None else None,
        }
    boxes = {}
    for l in root.iter('link'):
        b = l.find('visual/geometry/box')
        if b is not None:
            boxes[l.get('name')] = tuple(float(v) for v in b.get('size').split())
    return joints, boxes


def _footprints():
    """Both costmap footprints from nav2_params.yaml, as lists of (x, y)."""
    src = read(NAV2_SRC)
    out = []
    for m in re.finditer(r'^\s*footprint:\s*"(\[\[.*?\]\])"', src, re.M):
        out.append(ast.literal_eval(m.group(1)))
    return out


def _relay_defaults():
    tree = ast.parse(read(RELAY_SRC), RELAY_SRC)
    out = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and getattr(node.func, 'attr', '') == 'declare_parameter'
                and len(node.args) >= 2 and isinstance(node.args[0], ast.Constant)):
            try:
                out[node.args[0].value] = ast.literal_eval(node.args[1])
            except ValueError:
                pass
    return out


def check_physical_files():
    print('\n[6] The robot as the URDF, the costmaps and the LiDAR relay describe it')
    joints, boxes = _urdf()

    # Chassis 1.0 m long (x) by 0.36 m wide (y); cushion 1.12 by 0.48.
    chassis = boxes.get('chassis')
    check('URDF chassis box is long along X: 1.0 x 0.36',
          chassis is not None and abs(chassis[0] - 1.0) < 1e-9 and abs(chassis[1] - 0.36) < 1e-9,
          'got %r' % (chassis,))
    cushion = boxes.get('safety_cushion')
    check('URDF safety cushion is long along X: 1.12 x 0.48',
          cushion is not None and abs(cushion[0] - 1.12) < 1e-9 and abs(cushion[1] - 0.48) < 1e-9,
          'got %r' % (cushion,))

    # Wheels. Front is +X, left is +Y. Outer wheels (FR, RL) are l1 = 0.403
    # from the centre, inner wheels (FL, RR) l2 = 0.333.
    want = {'wheel_fr_joint': (L1, -D), 'wheel_fl_joint': (L2, D),
            'wheel_rr_joint': (-L2, -D), 'wheel_rl_joint': (-L1, D)}
    for name, (wx, wy) in want.items():
        xyz = joints.get(name, {}).get('xyz')
        check('URDF %s at (%+.5f, %+.5f)' % (name, wx, wy),
              xyz is not None and abs(xyz[0] - wx) < 1e-9 and abs(xyz[1] - wy) < 1e-9,
              'got %r' % (xyz,))
        axis = joints.get(name, {}).get('axis')
        check('URDF %s spins about Y (axle along the robot width)' % name,
              axis == (0.0, 1.0, 0.0), 'got %r' % (axis,))

    laser = joints.get('laser_joint', {}).get('xyz')
    check('URDF laser_joint is 0.27 m ahead of base_link on X: (0.27, 0, 0.275)',
          laser is not None and abs(laser[0] - 0.27) < 1e-9 and abs(laser[1]) < 1e-9
          and abs(laser[2] - 0.275) < 1e-9, 'got %r' % (laser,))

    # Costmap footprints, both, equal to each other and to the cushion.
    fps = _footprints()
    check('nav2_params has the two costmap footprints', len(fps) == 2, 'found %d' % len(fps))
    for i, fp in enumerate(fps):
        xs = sorted({abs(p[0]) for p in fp})
        ys = sorted({abs(p[1]) for p in fp})
        check('costmap footprint %d is long along X (+-0.56) and narrow in Y (+-0.24)' % (i + 1),
              xs == [0.56] and ys == [0.24], 'got x=%r y=%r' % (xs, ys))
    if len(fps) == 2:
        check('both footprints are identical (planner and controller must agree)',
              fps[0] == fps[1], '%r vs %r' % (fps[0], fps[1]))

    # LiDAR relay. theta_out = sign * theta_in + yaw_offset (scan_relay._build_map).
    d = _relay_defaults()
    sign = -1.0 if d.get('mirror') else 1.0
    yaw_off = d.get('yaw_offset_deg')
    check('scan_relay yaw_offset_deg defaults to 180 (was 270 in the old frame)',
          yaw_off == 180.0, 'got %r' % (yaw_off,))
    check('scan_relay mirror stays on (a reflection of the sensor, not an axis choice)',
          d.get('mirror') is True)

    def wrap(a):
        return (a + 180.0) % 360.0 - 180.0

    # The three measured blocks of 11 Aug (LiDAR_Orientation_Calibration.md):
    # what the sensor REPORTED for a block truly front / right / left.
    if yaw_off is not None:
        for label, reported, want_true in (('front', 180.0, 0.0), ('right', 270.0, -90.0),
                                           ('left', 90.0, 90.0)):
            got = wrap(sign * reported + yaw_off)
            check('relay maps the measured %s block (reported %d deg) to %+d deg in base_link'
                  % (label, reported, want_true),
                  abs(wrap(got - want_true)) < 1e-9, 'got %+.1f' % got)

    # The rear-mast mask must sit dead astern (180 deg) and nowhere else.
    lo, hi = d.get('mask_min_deg'), d.get('mask_max_deg')
    if lo is not None and hi is not None:
        span = (hi - lo) % 360.0

        def masked(deg):
            return ((deg - lo) % 360.0) <= span
        check('relay mask covers dead astern (180 deg) and is 90 deg wide',
              masked(180.0) and abs(span - 90.0) < 1e-9, 'lo=%r hi=%r span=%r' % (lo, hi, span))
        check('relay mask does not touch the nose, the left side or the right side',
              not masked(0.0) and not masked(90.0) and not masked(-90.0))


def _dash_const(src, name):
    m = re.search(r'const\s+%s\s*=\s*([^;]+);' % re.escape(name), src)
    return m.group(1).strip() if m else None


def check_dashboard():
    print('\n[7] Dashboard: standard axes in the data, nose-up on the screen')
    dash = read(DASH_SRC)

    # The canvas is rotated by DISPLAY_ROT (canvas y grows DOWN, so a positive
    # angle is clockwise). World +X must point UP the screen and world +Y LEFT.
    expr = _dash_const(dash, 'DISPLAY_ROT')
    rot = None
    if expr is not None:
        try:
            rot = eval(expr.replace('Math.PI', 'math.pi'), {'math': math})
        except Exception:
            rot = None
    check('dashboard DISPLAY_ROT is -PI/2 (forward = +X draws up the screen)',
          rot is not None and abs(rot - (-math.pi / 2)) < 1e-12, 'got %r' % (expr,))
    if rot is not None:
        c, s = math.cos(rot), math.sin(rot)
        # local +X (right) and local +Y (up on screen = (0, -1) in canvas coords)
        x_screen = (c * 1 - s * 0, s * 1 + c * 0)
        y_screen = (c * 0 - s * (-1), s * 0 + c * (-1))
        check('world +X lands screen-up', abs(x_screen[0]) < 1e-9 and x_screen[1] < -0.999,
              'got %r' % (x_screen,))
        check('world +Y lands screen-left', y_screen[0] < -0.999 and abs(y_screen[1]) < 1e-9,
              'got %r' % (y_screen,))

    check('vecToYaw is plain atan2(dy, dx), no 90 deg term',
          re.search(r'function\s+vecToYaw\(dx,\s*dy\)\s*\{\s*return\s+Math\.atan2\(dy,\s*dx\)\s*;\s*\}', dash)
          is not None)
    check('yawToVec is plain (cos, sin)',
          re.search(r'function\s+yawToVec\(yaw\)\s*\{\s*return\s*\{\s*x:\s*Math\.cos\(yaw\),\s*y:\s*Math\.sin\(yaw\)\s*\}\s*;\s*\}', dash)
          is not None)

    fx, fy = _dash_const(dash, 'FOOT_HALF_X'), _dash_const(dash, 'FOOT_HALF_Y')
    check('dashboard footprint half-sizes: X 0.56 (long), Y 0.24',
          fx is not None and fy is not None
          and abs(float(fx.split()[0]) - 0.56) < 1e-9 and abs(float(fy.split()[0]) - 0.24) < 1e-9,
          'got X=%r Y=%r' % (fx, fy))
    m = re.search(r'const\s+LASER_BX\s*=\s*([0-9.]+)\s*,\s*LASER_BY\s*=\s*([0-9.]+)\s*;', dash)
    check('dashboard laser offset is (0.27, 0): ahead on X',
          m is not None and abs(float(m.group(1)) - 0.27) < 1e-9 and abs(float(m.group(2))) < 1e-9,
          'got %r' % ((m.groups() if m else None),))
    check('dashboard sendDrive stays standard (vx = joyY, vy = -joyX)',
          re.search(r'const vx\s*=\s*applyDead\(joyY\)', dash) is not None
          and re.search(r'const vy\s*=\s*applyDead\(-joyX\)', dash) is not None)
    check('dashboard has no dispX/dispY relabel',
          re.search(r'const\s+dispX\s*=', dash) is None and re.search(r'const\s+dispY\s*=', dash) is None)
    check('dashboard NOSE is raw yaw, no offset',
          re.search(r'yaw \* 180 / Math\.PI \+ 90', dash) is None)


def check_source_guards():
    """Fail if the standard frame is edited back out, anywhere in the chain."""
    print('\n[8] Source guards -- the standard frame is still present')

    odom = read(ODOM_SRC)
    for lhs, rhs in (('pub_x', 'self.x'), ('pub_y', 'self.y'), ('pub_vx', 'vx'), ('pub_vy', 'vy'),
                     ('pub_theta', 'self.theta')):
        check('odometry_publisher: %s = %s (no rotation, no sign flip)' % (lhs, rhs),
              re.search(r'^\s*%s\s*=\s*%s\s*(#.*)?$' % (lhs, re.escape(rhs)), odom, re.M) is not None,
              'the published frame is not the internal REP-103 frame')
    check('odom TF and pose use pub_x / pub_y',
          re.search(r'translation\.x\s*=\s*pub_x', odom) is not None
          and re.search(r'translation\.y\s*=\s*pub_y', odom) is not None
          and re.search(r'position\.x\s*=\s*pub_x', odom) is not None
          and re.search(r'position\.y\s*=\s*pub_y', odom) is not None)
    check('odom twist uses pub_vx / pub_vy',
          re.search(r'twist\.twist\.linear\.x\s*=\s*pub_vx', odom) is not None
          and re.search(r'twist\.twist\.linear\.y\s*=\s*pub_vy', odom) is not None)

    goal = read(GOAL_SRC)
    check('goal_pose_adapter yaw_offset_deg defaults to 0.0',
          re.search(r"declare_parameter\('yaw_offset_deg',\s*0\.0\)", goal) is not None,
          'a goal-yaw correction would double-apply')

    launch = '\n'.join(read(f) for f in LAUNCH_SRCS if os.path.exists(f))
    check('ZERO_POINT_YAW is 0.0',
          re.search(r'ZERO_POINT_YAW\s*=\s*0\.0', launch) is not None,
          'the zero marker would sit off base_link')

    teleop = read(TELEOP_SRC)
    check('teleop still speaks REP-103 (vx forward, vy left): wheel kinematics untouched',
          re.search(r'w_fr\s*=\s*self\.inv_r\s*\*\s*\(vx \+ vy', teleop) is not None,
          'the wheel kinematics were changed -- they should not have been')

    # The velocity adapter. Until it is deleted it must be an IDENTITY; after
    # that no launch file may refer to it.
    if os.path.exists(ADAPTER_SRC):
        ad = read(ADAPTER_SRC)
        check('cmd_vel_axis_adapter is an identity (out.x = in.x, out.y = in.y)',
              re.search(r'out\.linear\.x\s*=\s*msg\.linear\.x\b', ad) is not None
              and re.search(r'out\.linear\.y\s*=\s*msg\.linear\.y\b', ad) is not None
              and re.search(r'out\.linear\.x\s*=\s*msg\.linear\.y', ad) is None
              and re.search(r'out\.linear\.y\s*=\s*-msg\.linear\.x', ad) is None,
              'the base_link -> wheel rotation is back; it must not be')
    else:
        stale = [os.path.relpath(f, REPO) for f in NAV_LAUNCHES
                 if os.path.exists(f) and 'cmd_vel_axis_adapter' in read(f)]
        check('cmd_vel_axis_adapter is deleted and no launch file starts it', not stale,
              'still referenced in %r' % (stale,))


def main():
    print('=' * 68)
    print('verify_axis_chain.py -- keypress to map frame, end to end')
    print('=' * 68)

    check_operator_table()
    check_zero_mark_yaw()
    check_general_invariant()
    check_body_to_map_agrees()
    check_parameter_defaults()
    check_physical_files()
    check_dashboard()
    check_source_guards()

    print('\n' + '=' * 68)
    if FAILURES:
        print('FAILED: %d check(s)' % len(FAILURES))
        for f in FAILURES:
            print('   - %s' % f)
        print('=' * 68)
        return 1
    print('ALL CHECKS PASSED')
    print('')
    print('  W -> map +X     S -> map -X     D -> map -Y     A -> map +Y')
    print('  odom, map and base_link all use +X=forward, +Y=left, yaw CCW from +X.')
    print('')
    print('  This is arithmetic, not hardware. Confirm on the robot with:')
    print('    ros2 run tf2_ros tf2_echo odom base_link     # expect 0,0,0 and yaw 0 on the mark')
    print('    drive W: x rises.  drive D: y falls.')
    print('=' * 68)
    return 0


if __name__ == '__main__':
    sys.exit(main())
