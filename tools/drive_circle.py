#!/usr/bin/env python3
"""
drive_circle.py -- drive an exact circle of a chosen radius, for a chosen
number of laps, then stop.

WHY THIS EXISTS
    The commissioning space only fits a small circle (15 Sep 2026), so the
    plan for G4 coverage is repeated laps of the same circle rather than a
    longer route. That plan needs the laps to be the SAME lap: a hand-driven
    circle varies between runs, and a coverage A/B is worthless if the
    trajectory moved between the A and the B.

    It also removes two ways to get the geometry wrong by hand: holding a
    constant radius (radius = speed / yaw rate, and a wandering yaw rate
    wanders the radius), and counting laps.

AXES -- READ THIS BEFORE EDITING
    /cmd_vel_manual carries a REP-103 Twist: linear.x is FORWARD, linear.y
    is LEFT, angular.z is CCW. This is NOT the same convention as the
    base_link/odom/map FRAMES on this robot, which are +X right, +Y forward
    (Research_Journal.md 17.10, 17.38). mecanum_teleop_asymmetric does the
    conversion downstream. tools/verify_axis_chain.py is the guard, and
    line 96 of it states the dashboard's own mapping.

    So: forward is linear.x HERE, and +Y in the map. Both are true and they
    are not in conflict.

SAFETY
    - /cmd_vel_manual has twist_mux priority 100, ABOVE navigation's 10, and
      collision_monitor sits only in the navigation branch. This script
      therefore drives with no automatic obstacle stop, exactly as manual
      joystick driving already does. Keep a hand on E-STOP.
    - It will not move without --go. Without it you get the plan and the
      clearance arithmetic only.
    - Zeros are published on normal exit, on Ctrl-C, and on any exception.
    - A hard time limit (--timeout, default 1.3x the planned duration) stops
      it even if something upstream stalls.

USAGE
    python3 tools/drive_circle.py --radius 0.75 --laps 3            # plan only
    python3 tools/drive_circle.py --radius 0.75 --laps 3 --go       # drive it
    python3 tools/drive_circle.py --radius 0.5 --laps 5 --speed 0.10 --go
"""

import argparse
import math
import sys
import time

# Robot footprint, from nav2_params.yaml's footprint polygon
# [[0.24, 0.56], [0.24, -0.56], [-0.24, -0.56], [-0.24, 0.56]] where the
# long axis runs along +Y (the nose). See phone_dashboard.py's FOOT_HALF_*.
HALF_WIDTH_M = 0.24     # left..right
HALF_LENGTH_M = 0.56    # tail..nose
TILE_M = 0.62           # lab floor tile pitch, tape-measured (17.47)


def swept_diameter(radius_m):
    """Clear floor diameter needed for the BODY, not just the path.

    The robot drives nose-tangent, so its centre sits at `radius_m` while
    its corners reach further out: radially by the half width, and along
    the tangent by the half length. The outermost corner is therefore at
    hypot(radius + half_width, half_length) from the circle's centre.
    """
    outer = math.hypot(radius_m + HALF_WIDTH_M, HALF_LENGTH_M)
    return 2.0 * outer


def plan(radius_m, speed_ms, laps):
    omega = speed_ms / radius_m
    lap_s = 2.0 * math.pi * radius_m / speed_ms
    return {
        'omega_rads': omega,
        'omega_degs': math.degrees(omega),
        'lap_s': lap_s,
        'total_s': lap_s * laps,
        'lap_m': 2.0 * math.pi * radius_m,
        'total_m': 2.0 * math.pi * radius_m * laps,
        'swept_d': swept_diameter(radius_m),
    }


def print_plan(a, p):
    print()
    print('  CIRCLE PLAN')
    print('  ' + '-' * 52)
    print('  radius              %.2f m   (%.2f m across)' % (a.radius, 2 * a.radius))
    print('  speed               %.3f m/s' % a.speed)
    print('  yaw rate needed     %.3f rad/s  (%.1f deg/s)  %s'
          % (p['omega_rads'], p['omega_degs'], 'CCW' if a.ccw else 'CW'))
    print('  laps                %d' % a.laps)
    print('  path per lap        %.2f m' % p['lap_m'])
    print('  total path          %.2f m' % p['total_m'])
    print('  time per lap        %.1f s' % p['lap_s'])
    print('  total time          %.1f s' % p['total_s'])
    print()
    print('  CLEARANCE (body, not path)')
    print('  ' + '-' * 52)
    print('  clear floor needed  %.2f m across  (%.1f tiles at %.2f m)'
          % (p['swept_d'], p['swept_d'] / TILE_M, TILE_M))
    print('  the robot is 1.12 m long, so its corners swing wider than the')
    print('  circle its centre follows. Measure the floor, not the path.')
    print()
    print('  DRIFT EXPECTATION')
    print('  ' + '-' * 52)
    # Measured 0.20% on run_20260915_131800; historical band 1.1-1.5%.
    for label, rate in (('measured 15 Sep (0.20%)', 0.0020),
                        ('historical band low (1.1%)', 0.011),
                        ('historical band high (1.5%)', 0.015)):
        err = p['total_m'] * rate
        flag = '' if err < 0.15 else '   <-- FAILS the 0.15 m G4 return gate'
        print('  %-28s %.3f m%s' % (label, err, flag))
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--radius', type=float, default=0.75,
                    help='circle radius in metres, robot centre (default 0.75, i.e. 1.5 m across)')
    ap.add_argument('--speed', type=float, default=0.10,
                    help='forward speed m/s (default 0.10, the dashboard MED limit)')
    ap.add_argument('--laps', type=float, default=3.0, help='number of laps (default 3)')
    ap.add_argument('--cw', action='store_true', help='clockwise instead of counter-clockwise')
    ap.add_argument('--rate', type=float, default=20.0, help='publish rate Hz (default 20)')
    ap.add_argument('--timeout', type=float, default=None,
                    help='hard stop in seconds (default 1.3x planned duration)')
    ap.add_argument('--go', action='store_true', help='actually drive; without it, plan only')
    a = ap.parse_args()
    a.ccw = not a.cw

    if a.radius <= 0 or a.speed <= 0 or a.laps <= 0:
        sys.exit('radius, speed and laps must all be positive')

    p = plan(a.radius, a.speed, a.laps)
    print_plan(a, p)

    if not a.go:
        print('  Plan only. Re-run with --go to drive it.')
        print()
        return

    hard_limit = a.timeout if a.timeout else p['total_s'] * 1.3

    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import Twist

    rclpy.init()
    node = Node('drive_circle')
    pub = node.create_publisher(Twist, '/cmd_vel_manual', 10)

    # REP-103 on this topic: linear.x forward, angular.z CCW positive.
    cmd = Twist()
    cmd.linear.x = a.speed
    cmd.linear.y = 0.0
    cmd.angular.z = p['omega_rads'] if a.ccw else -p['omega_rads']

    stop = Twist()

    def send_stop(times=10):
        for _ in range(times):
            pub.publish(stop)
            time.sleep(0.02)

    print('  Driving. Ctrl-C stops and zeroes. Hand on E-STOP.')
    print()
    t0 = time.time()
    period = 1.0 / a.rate
    try:
        while rclpy.ok():
            el = time.time() - t0
            if el >= p['total_s'] or el >= hard_limit:
                break
            pub.publish(cmd)
            rclpy.spin_once(node, timeout_sec=0.0)
            done_laps = el / p['lap_s']
            print('\r  %5.1f s / %5.1f s   lap %.2f / %.2f   %.2f m'
                  % (el, p['total_s'], done_laps, a.laps, el * a.speed), end='')
            sys.stdout.flush()
            time.sleep(period)
    except KeyboardInterrupt:
        print('\n  Interrupted.')
    finally:
        send_stop()
        el = time.time() - t0
        print('\n  Stopped after %.1f s, about %.2f m, %.2f laps.'
              % (el, el * a.speed, el / p['lap_s']))
        print('  Zeros published. Now tape-measure the offset from the mark.')
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
