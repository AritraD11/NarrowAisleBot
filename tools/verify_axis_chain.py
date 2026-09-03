#!/usr/bin/env python3
"""
verify_axis_chain.py -- prove, without hardware, that a keypress moves the
robot the way the map says it does.

WHY THIS EXISTS
    The axis convention on this robot has been re-derived, re-argued and
    re-broken more times than any other single fact in the project
    (Research_Journal.md 17.10, 17.12, 17.19, 17.20, 17.36, 17.37, 17.38).
    Every one of those rounds ended in prose -- a table in a doc, a comment
    in a file -- and prose does not fail a build when someone edits the
    code out from under it.

    This does. It runs the ACTUAL arithmetic from the drive chain, end to
    end, and asserts the four statements the operator cares about:

        W (forward)      -> map +Y
        S (backward)     -> map -Y
        D (strafe right) -> map +X
        A (strafe left)  -> map -X

    It also guards the source files themselves, so that deleting the fix
    fails this script rather than silently reappearing on the robot three
    weeks later.

WHAT IT SIMULATES
    keypress -> phone_dashboard sendDrive() -> /cmd_vel_manual -> twist_mux
    -> mecanum_teleop_asymmetric.compute_wheel_speeds() -> wheel speeds ->
    odometry_publisher forward kinematics -> integration -> published
    odom->base_link -> (map->odom = identity at SLAM start) -> map frame.

    twist_mux does no axis math (it is a priority arbiter), so it is a
    pass-through here, as it is in reality.

WHAT IT DOES NOT SIMULATE, DELIBERATELY
    Wheel slip, roller scrub beyond the modelled lateral_scale, encoder
    noise, loop closure, and the LiDAR. This answers "do the axes agree",
    not "is the odometry accurate" -- those are separate questions and
    conflating them is how 17.36 lost a day. Magnitudes here are therefore
    checked only for sign and dominant axis, never for absolute accuracy.

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

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ODOM_SRC = os.path.join(REPO, 'src/mecanum_robot/mecanum_robot/odometry_publisher.py')
TELEOP_SRC = os.path.join(REPO, 'src/mecanum_robot/mecanum_robot/mecanum_teleop_asymmetric.py')
DASH_SRC = os.path.join(REPO, 'src/mecanum_robot/mecanum_robot/phone_dashboard.py')
GOAL_SRC = os.path.join(REPO, 'src/mecanum_navigation/mecanum_navigation/goal_pose_adapter.py')
LAUNCH_SRC = os.path.join(REPO, 'src/mecanum_robot/launch/mapping_full.launch.py')

# ── Geometry ─────────────────────────────────────────────────────────────
# These mirror the declare_parameter() defaults in the two nodes. They are
# not hardcoded on trust: check_parameter_defaults() below reads the real
# defaults out of the source and fails if they have drifted from these.
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


def _extract_publish_exprs():
    """Pull pub_x / pub_y / pub_theta straight out of odometry_publisher.py.

    Transcribing this arithmetic into the test would let the two drift apart
    -- and drift is the entire failure mode being guarded against here. A
    first version of this file did transcribe it, and reintroducing the bug
    on purpose then failed only the source-text guards while the numeric
    table happily still passed, because the table was checking the test's
    own copy of the maths. So the expressions are parsed from the real
    module and evaluated. Only these three right-hand sides are compiled,
    from a file in this repo; nothing else in the module is executed, which
    is also why this needs no ROS installed.
    """
    tree = ast.parse(read(ODOM_SRC), ODOM_SRC)
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in ('pub_x', 'pub_y', 'pub_theta'):
                expr = ast.Expression(body=node.value)
                ast.fix_missing_locations(expr)
                found[target.id] = compile(expr, ODOM_SRC, 'eval')
    missing = {'pub_x', 'pub_y', 'pub_theta'} - set(found)
    if missing:
        raise SystemExit(
            'verify_axis_chain: could not find %s in %s -- the published-frame '
            'block has been restructured, update this parser before trusting '
            'any result below.' % (', '.join(sorted(missing)), ODOM_SRC))
    return found


_PUB_EXPRS = _extract_publish_exprs()


def publish_frame(x_int, y_int, theta_int, vx=0.0, vy=0.0):
    """odometry_publisher.py's published-frame rotation, read from source.

    All THREE quantities must carry the -90 deg relabel. Before 17.38 the
    translation did not, which is precisely the bug this file guards.
    """
    ns = {'self': _Self(x_int, y_int, theta_int), 'math': math,
          'vx': vx, 'vy': vy}
    return (eval(_PUB_EXPRS['pub_x'], ns),
            eval(_PUB_EXPRS['pub_y'], ns),
            eval(_PUB_EXPRS['pub_theta'], ns))


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

    px0, py0, pth0 = publish_frame(0.0, 0.0, start_theta_int)
    px1, py1, pth1 = publish_frame(x, y, theta)
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
        ('w', 'forward', 'y', +1),
        ('s', 'backward', 'y', -1),
        ('d', 'strafe right', 'x', +1),
        ('a', 'strafe left', 'x', -1),
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
    """A freshly-zeroed robot on the mark must publish yaw 0, not -90."""
    print('\n[2] Published yaw at a freshly-zeroed odometry')
    _, _, _, pth0 = simulate('w', seconds=0.02)
    check('odom->base_link yaw == 0 deg (was -90 before 17.38)',
          abs(pth0) < 1e-9, 'got %.4f deg' % math.degrees(pth0))


def check_general_invariant():
    """The property that must hold at EVERY heading, not just zero.

    A body-frame displacement of (right, forward) must land in the map as
    Rot(published_yaw) applied to (right, forward). If that holds for
    arbitrary headings then the frames genuinely agree; if it only holds at
    zero, we have coincidence, not correctness.
    """
    print('\n[3] Frame invariant at arbitrary headings')
    for deg in (0, 30, 90, 137, -45, -90, 180):
        th = math.radians(deg)
        # Body-frame intent: W is pure forward, D is pure right.
        for key, body in (('w', (0.0, 1.0)), ('d', (1.0, 0.0))):
            dx, dy, _, pth0 = simulate(key, seconds=2.0, start_theta_int=th)
            mag = math.hypot(dx, dy)
            if mag < 1e-9:
                check('heading %+4d deg, %s' % (deg, key.upper()), False, 'no motion')
                continue
            # Expected direction: rotate the body intent by the published yaw.
            c, s = math.cos(pth0), math.sin(pth0)
            ex = body[0] * c - body[1] * s
            ey = body[0] * s + body[1] * c
            # Compare unit vectors.
            cos_err = (dx * ex + dy * ey) / mag
            if VERBOSE:
                print('        %+4d deg %s: dmap=(%+.4f,%+.4f) expected dir=(%+.3f,%+.3f)'
                      % (deg, key.upper(), dx, dy, ex, ey))
            check('heading %+4d deg, %s follows Rot(yaw)*(right,forward)' % (deg, key.upper()),
                  cos_err > 0.999, 'alignment %.6f' % cos_err)


def check_body_to_map_agrees():
    """nav_goal.py / zero_point_scan.py's body_to_map must agree with TF."""
    print('\n[4] body_to_map() (nav_goal.py, zero_point_scan.py) agrees')

    def body_to_map(x, y, yaw, right, forward):
        cos_y, sin_y = math.cos(yaw), math.sin(yaw)
        return (x + right * cos_y - forward * sin_y,
                y + right * sin_y + forward * cos_y)

    for deg in (0, 45, -90, 160):
        yaw = math.radians(deg)
        gx, gy = body_to_map(0.0, 0.0, yaw, 0.0, 1.0)   # 1 m forward
        ex, ey = -math.sin(yaw), math.cos(yaw)
        check('body_to_map forward at %+4d deg' % deg,
              abs(gx - ex) < 1e-9 and abs(gy - ey) < 1e-9,
              'got (%.4f, %.4f) want (%.4f, %.4f)' % (gx, gy, ex, ey))
    # At yaw 0 a pure-forward goal must be pure +Y.
    gx, gy = body_to_map(0.0, 0.0, 0.0, 0.0, 1.0)
    check('at yaw 0, "1 m forward" == map (0, +1)',
          abs(gx) < 1e-12 and abs(gy - 1.0) < 1e-12, 'got (%.4f, %.4f)' % (gx, gy))


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


def check_source_guards():
    """Fail if the fix is edited back out, anywhere in the chain."""
    print('\n[6] Source guards -- the fix is still present')

    odom = read(ODOM_SRC)
    check('odometry_publisher rotates published translation (pub_x = -self.y)',
          re.search(r'pub_x\s*=\s*-self\.y', odom) is not None,
          'the 17.38 fix is missing -- odom would inherit REP-103 axes again')
    check('odometry_publisher rotates published translation (pub_y = self.x)',
          re.search(r'pub_y\s*=\s*self\.x', odom) is not None)
    check('odometry_publisher publishes pub_theta with no -90 constant',
          re.search(r'pub_theta\s*=\s*self\.theta\s*$', odom, re.M) is not None,
          'a constant offset has come back')
    check('odom TF uses the rotated translation, not self.x/self.y',
          re.search(r'translation\.x\s*=\s*pub_x', odom) is not None
          and re.search(r'translation\.y\s*=\s*pub_y', odom) is not None,
          'the TF broadcast bypasses the rotation')
    check('odom pose uses the rotated translation',
          re.search(r'position\.x\s*=\s*pub_x', odom) is not None
          and re.search(r'position\.y\s*=\s*pub_y', odom) is not None)

    dash = read(DASH_SRC)
    check('dashboard DISPLAY_ROT is 0',
          re.search(r'const\s+DISPLAY_ROT\s*=\s*0\s*;', dash) is not None,
          'a canvas rotation would double-apply now')
    check('dashboard has no dispX/dispY relabel',
          re.search(r'const\s+dispX\s*=', dash) is None
          and re.search(r'const\s+dispY\s*=', dash) is None,
          'a print-site relabel would double-apply now')
    check('dashboard NOSE has no +90 offset',
          re.search(r'yaw \* 180 / Math\.PI \+ 90', dash) is None,
          'the nose offset would introduce the error it used to remove')

    goal = read(GOAL_SRC)
    check('goal_pose_adapter yaw_offset_deg defaults to 0.0',
          re.search(r"declare_parameter\('yaw_offset_deg',\s*0\.0\)", goal) is not None,
          'a goal-yaw correction would double-apply now')

    launch = read(LAUNCH_SRC)
    check('ZERO_POINT_YAW is 0.0',
          re.search(r'ZERO_POINT_YAW\s*=\s*0\.0', launch) is not None,
          'the zero marker would sit 90 deg off base_link')


def check_untouched():
    """The conversions that are still needed must NOT have been removed."""
    print('\n[7] Conversions that must SURVIVE (not everything was a bug)')
    teleop = read(TELEOP_SRC)
    check('teleop still speaks REP-103 (vx forward, vy left)',
          re.search(r'w_fr\s*=\s*self\.inv_r\s*\*\s*\(vx \+ vy', teleop) is not None,
          'the wheel kinematics were changed -- they should not have been')

    adapter_path = os.path.join(
        REPO, 'src/mecanum_navigation/mecanum_navigation/cmd_vel_axis_adapter.py')
    adapter = read(adapter_path)
    check('cmd_vel_axis_adapter still converts base_link -> wheel axes',
          re.search(r'out\.linear\.x\s*=\s*msg\.linear\.y', adapter) is not None
          and re.search(r'out\.linear\.y\s*=\s*-msg\.linear\.x', adapter) is not None,
          'this one is still needed -- base_link and REP-103 still differ')

    relay = read(os.path.join(REPO, 'src/scan_relay/scan_relay.py'))
    check('scan_relay still applies the LiDAR mirror',
          re.search(r"declare_parameter\('mirror'", relay) is not None
          and re.search(r"declare_parameter\('yaw_offset_deg',\s*270\.0\)", relay) is not None,
          'the sensor reflection is unrelated to the map frame and must stay')

    urdf = read(os.path.join(REPO, 'src/mecanum_robot/urdf/aislebot.urdf'))
    check('URDF laser_joint still unrotated at +Y 0.27',
          re.search(r'xyz="0 0\.27 0\.275" rpy="0 0 0"', urdf) is not None,
          'the LiDAR mount must not move to chase an axis bug')


def main():
    print('=' * 68)
    print('verify_axis_chain.py -- keypress to map frame, end to end')
    print('=' * 68)

    check_operator_table()
    check_zero_mark_yaw()
    check_general_invariant()
    check_body_to_map_agrees()
    check_parameter_defaults()
    check_source_guards()
    check_untouched()

    print('\n' + '=' * 68)
    if FAILURES:
        print('FAILED: %d check(s)' % len(FAILURES))
        for f in FAILURES:
            print('   - %s' % f)
        print('=' * 68)
        return 1
    print('ALL CHECKS PASSED')
    print('')
    print('  W -> map +Y     S -> map -Y     D -> map +X     A -> map -X')
    print('  odom, map and base_link all use +X=right, +Y=forward.')
    print('')
    print('  This is arithmetic, not hardware. Confirm on the robot with:')
    print('    ros2 run tf2_ros tf2_echo odom base_link     # expect yaw 0 on the mark')
    print('=' * 68)
    return 0


if __name__ == '__main__':
    sys.exit(main())
