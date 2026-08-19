#!/usr/bin/env python3
"""
repeatability_test.py -- send the robot N metres in one direction and back,
repeated several times, pausing each leg for a physical tape measurement.

WHY THIS EXISTS
    Phase 1 of the 18-19 Aug 2026 session (Research_Journal.md sec 17.21-
    17.24) exists to answer one question with real numbers, not eyeballing:
    does the corrected odometry (lateral_scale, sec 17.21) make the robot's
    BELIEVED position match physical reality? A single goal-and-measure
    gives one data point. This automates the repeat, so five trials per
    direction is a few minutes of typing a tape reading into a prompt,
    not five separate hand-built ros2 action send_goal invocations.

    Every commanded distance below was sized against this robot's ACTUAL
    measured clearance at the zero mark, worked out together with the user
    the same session (padded footprint half-width 0.25 m, half-length
    0.57 m -- Research_Journal.md sec 17.7/17.12 -- against clearance of
    4 m right, 2 m front, ~0.75 m left, ~1.07 m rear). SAFE_MAX below is a
    hard ceiling under those figures; --distance cannot exceed it without
    --force. This is not a generic tool for an arbitrary space -- the
    defaults and ceiling are this robot, at this mark, today.

WHAT EACH REPETITION DOES
    1. Measure the current pose (map -> base_link) -- this is "home" for
       the WHOLE run, recorded once, not re-measured each rep. Every
       repetition's outbound goal is computed from this same fixed pose,
       not from wherever the robot happens to be after the previous
       return -- that is what makes five trials a repeatability measure
       rather than five independent one-off drives.
    2. Send the outbound goal (NavigateToPose, heading held). Wait for the
       result. Record the TF pose it actually stopped at.
    3. PAUSE. Print the commanded distance and the TF-measured distance,
       ask for a physical tape reading, press Enter to continue (blank
       skips that reading rather than blocking the run).
    4. Send the return-to-start goal (the exact original pose). Wait.
       Record how close TF says it landed to home.
    5. PAUSE. Press Enter to start the next repetition, or Ctrl-C to stop
       -- which still runs the same guaranteed return-to-start as
       zero_point_scan.py before exiting.

SAFETY, same discipline as zero_point_scan.py
    - Every motion is a NavigateToPose goal on the same validated path
      (MPPI, tightened 2 cm / 0.025 rad goal tolerance, sec 17.23).
    - --distance is capped per side at SAFE_MAX; exceeding it refuses to
      run unless --force is passed explicitly.
    - A lock file stops two copies (or this and zero_point_scan.py, if
      ever run for the same reason) fighting over /navigate_to_pose.
    - The final action on every exit path, including Ctrl-C or an
      exception mid-run, is a goal back to the exact original pose.

Usage (one direction at a time -- small first, same as every new capability
this project has tested):
    python3 repeatability_test.py --side right --reps 5
    python3 repeatability_test.py --side left  --reps 5
    python3 repeatability_test.py --side front --reps 5
    python3 repeatability_test.py --side rear  --reps 5

Logs every rep to ~/aislebot_logs/repeatability_<side>_<timestamp>.csv and
prints a summary table at the end -- both meant to be pasted straight into
a report.
"""

import argparse
import csv
import math
import os
import sys
import time
from datetime import datetime

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener, TransformException
from nav2_msgs.action import NavigateToPose


def yaw_from_quat(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def quat_from_yaw(yaw):
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)


def body_to_map(x, y, yaw, right, forward):
    """Same convention as nav_goal.py / zero_point_scan.py: body +X =
    right, +Y = forward (sec 17.10)."""
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    return (
        x + right * cos_y - forward * sin_y,
        y + right * sin_y + forward * cos_y,
    )


# (right_sign, forward_sign) per side -- distance is always a positive
# magnitude on the command line, these give it the right direction.
SIDE_VECTOR = {
    'right': (1.0, 0.0),
    'left':  (-1.0, 0.0),
    'front': (0.0, 1.0),
    'rear':  (0.0, -1.0),
}

# Metres. Defaults sized against measured clearance at the zero mark,
# 18-19 Aug 2026 (see module docstring). SAFE_MAX is a HARD CEILING, not a
# suggestion -- it exists specifically so a typo in --distance cannot send
# the robot further than this space was actually checked for.
DEFAULT_DISTANCE = {'right': 1.00, 'left': 0.35, 'front': 1.00, 'rear': 0.35}
SAFE_MAX = {'right': 2.00, 'left': 0.45, 'front': 1.20, 'rear': 0.45}


class RepeatabilityTester(Node):

    def __init__(self, args):
        super().__init__('repeatability_tester')
        self.args = args
        self.tf_buffer = Buffer()
        TransformListener(self.tf_buffer, self)
        self.nav_client = ActionClient(self, NavigateToPose, '/navigate_to_pose')

    def measure_pose(self):
        deadline = time.monotonic() + 10.0
        last_error = None
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            try:
                tf = self.tf_buffer.lookup_transform(
                    self.args.map_frame, self.args.base_frame, Time())
                t = tf.transform.translation
                yaw = yaw_from_quat(tf.transform.rotation)
                return t.x, t.y, yaw
            except TransformException as exc:
                last_error = exc
        raise RuntimeError('could not read {} -> {}: {}'.format(
            self.args.map_frame, self.args.base_frame, last_error))

    def send_goal_and_wait(self, x, y, yaw, timeout_sec=20.0):
        """Copied verbatim from zero_point_scan.py -- proven on hardware
        18 Aug 2026, do not diverge without re-validating both."""
        if not self.nav_client.wait_for_server(timeout_sec=5.0):
            raise RuntimeError('/navigate_to_pose action server not available')

        qx, qy, qz, qw = quat_from_yaw(yaw)
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = self.args.map_frame
        goal.pose.pose.position.x = x
        goal.pose.pose.position.y = y
        goal.pose.pose.orientation.x = qx
        goal.pose.pose.orientation.y = qy
        goal.pose.pose.orientation.z = qz
        goal.pose.pose.orientation.w = qw

        send_future = self.nav_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=5.0)
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().warn('goal rejected')
            return False

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=timeout_sec)
        result = result_future.result()
        if result is None:
            self.get_logger().warn('goal timed out waiting for result')
            return False
        return result.status == 4  # STATUS_SUCCEEDED

    def run(self):
        side = self.args.side
        right_sign, forward_sign = SIDE_VECTOR[side]
        distance = self.args.distance
        reps = self.args.reps

        start_x, start_y, start_yaw = self.measure_pose()
        self.get_logger().info(
            'HOME for this run: ({:.4f}, {:.4f}) @ {:.2f} deg'.format(
                start_x, start_y, math.degrees(start_yaw)))

        goal_x, goal_y = body_to_map(
            start_x, start_y, start_yaw,
            right_sign * distance, forward_sign * distance)

        print()
        print('=' * 72)
        print('REPEATABILITY TEST: side={}  distance={:.3f} m  reps={}'.format(
            side, distance, reps))
        print('Outbound goal (fixed for every rep): x={:.4f} y={:.4f}'.format(
            goal_x, goal_y))
        print('Return goal   (fixed for every rep): x={:.4f} y={:.4f}'.format(
            start_x, start_y))
        print('Hand near the E-STOP. Press Ctrl-C at any time to abort --')
        print('the robot will still return to the start pose before exiting.')
        print('=' * 72)
        print()

        rows = []
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_dir = os.path.expanduser('~/aislebot_logs')
        os.makedirs(log_dir, exist_ok=True)
        csv_path = os.path.join(log_dir, 'repeatability_{}_{}.csv'.format(side, ts))

        fieldnames = [
            'side', 'rep', 'distance_commanded_m',
            'out_result', 'out_tf_travelled_m', 'tape_measured_m',
            'tf_minus_tape_m', 'commanded_minus_tape_m',
            'return_result', 'return_home_error_m',
            'timestamp',
        ]

        try:
            with open(csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for rep in range(1, reps + 1):
                    print('--- rep {}/{} ---'.format(rep, reps))

                    out_ok = self.send_goal_and_wait(goal_x, goal_y, start_yaw)
                    ox, oy, oyaw = self.measure_pose()
                    tf_travelled = math.hypot(ox - start_x, oy - start_y)
                    print('  outbound: {}   TF says it travelled {:.3f} m '
                          '(commanded {:.3f} m)'.format(
                              'OK' if out_ok else 'FAILED', tf_travelled, distance))

                    tape_raw = input(
                        '  tape-measure the ACTUAL distance travelled (m), '
                        'Enter to skip: ').strip()
                    tape_val = None
                    if tape_raw:
                        try:
                            tape_val = float(tape_raw)
                        except ValueError:
                            print('  (not a number, recorded as skipped)')

                    return_ok = self.send_goal_and_wait(start_x, start_y, start_yaw)
                    rx, ry, ryaw = self.measure_pose()
                    home_error = math.hypot(rx - start_x, ry - start_y)
                    print('  return:   {}   {:.3f} m from the exact start pose'.format(
                        'OK' if return_ok else 'FAILED', home_error))

                    row = {
                        'side': side,
                        'rep': rep,
                        'distance_commanded_m': '{:.4f}'.format(distance),
                        'out_result': 'OK' if out_ok else 'FAILED',
                        'out_tf_travelled_m': '{:.4f}'.format(tf_travelled),
                        'tape_measured_m': '' if tape_val is None else '{:.4f}'.format(tape_val),
                        'tf_minus_tape_m': '' if tape_val is None
                                           else '{:.4f}'.format(tf_travelled - tape_val),
                        'commanded_minus_tape_m': '' if tape_val is None
                                                  else '{:.4f}'.format(distance - tape_val),
                        'return_result': 'OK' if return_ok else 'FAILED',
                        'return_home_error_m': '{:.4f}'.format(home_error),
                        'timestamp': datetime.now().isoformat(timespec='seconds'),
                    }
                    rows.append(row)
                    writer.writerow(row)
                    f.flush()

                    if rep < reps:
                        input('  press Enter for the next rep (robot should be '
                              'back at the mark) ... ')
                        print()

        finally:
            self.get_logger().info('final return to exact start pose')
            try:
                self.send_goal_and_wait(start_x, start_y, start_yaw)
            except Exception as exc:
                self.get_logger().error('final return-to-start failed: {}'.format(exc))

        self._print_summary(side, distance, rows, csv_path)

    def _print_summary(self, side, distance, rows, csv_path):
        print()
        print('=' * 72)
        print('SUMMARY: side={}  commanded={:.3f} m  n={}'.format(
            side, distance, len(rows)))
        print('{:<5}{:<10}{:<12}{:<10}{:<12}{:<12}'.format(
            'rep', 'out', 'tf_trav_m', 'tape_m', 'tf-tape_m', 'home_err_m'))
        tape_errors = []
        home_errors = []
        for r in rows:
            print('{:<5}{:<10}{:<12}{:<10}{:<12}{:<12}'.format(
                r['rep'], r['out_result'], r['out_tf_travelled_m'],
                r['tape_measured_m'] or '-', r['tf_minus_tape_m'] or '-',
                r['return_home_error_m']))
            if r['tf_minus_tape_m']:
                tape_errors.append(float(r['tf_minus_tape_m']))
            home_errors.append(float(r['return_home_error_m']))

        if tape_errors:
            mean_e = sum(tape_errors) / len(tape_errors)
            max_e = max(abs(e) for e in tape_errors)
            print()
            print('TF-vs-tape error: mean {:+.4f} m, max |e| {:.4f} m, n={}'.format(
                mean_e, max_e, len(tape_errors)))
        if home_errors:
            print('return-to-home error: mean {:.4f} m, max {:.4f} m'.format(
                sum(home_errors) / len(home_errors), max(home_errors)))
        print()
        print('Logged to: {}'.format(csv_path))
        print('=' * 72)


LOCK_PATH = '/tmp/repeatability_test.lock'


def acquire_lock():
    if os.path.exists(LOCK_PATH):
        try:
            with open(LOCK_PATH) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
        except (ValueError, OSError):
            pass
        else:
            print('ERROR: another repeatability_test.py is already running '
                  '(pid {}). Stop it first.'.format(pid), file=sys.stderr)
            return False
    with open(LOCK_PATH, 'w') as f:
        f.write(str(os.getpid()))
    return True


def release_lock():
    try:
        os.unlink(LOCK_PATH)
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser(
        description='Repeated out-and-back goals in one direction, pausing '
                    'each rep for a tape measurement.')
    parser.add_argument('--side', required=True, choices=sorted(SIDE_VECTOR),
                        help='which direction to test, in the ROBOT BODY '
                             'frame (right/left = strafe, front/rear = '
                             'forward/reverse).')
    parser.add_argument('--distance', type=float, default=None,
                        help='metres to travel. Default depends on --side '
                             '(see SAFE_MAX in the module header): right '
                             '1.00, left 0.35, front 1.00, rear 0.35.')
    parser.add_argument('--reps', type=int, default=5,
                        help='number of out-and-back repetitions. Default 5.')
    parser.add_argument('--force', action='store_true',
                        help='allow --distance to exceed the safety ceiling '
                             'for the chosen side. Do not pass this without '
                             're-checking clearance by hand first.')
    parser.add_argument('--map-frame', default='map')
    parser.add_argument('--base-frame', default='base_link')
    args = parser.parse_args()

    if args.distance is None:
        args.distance = DEFAULT_DISTANCE[args.side]

    ceiling = SAFE_MAX[args.side]
    if args.distance > ceiling and not args.force:
        print('ERROR: --distance {:.3f} m exceeds the safety ceiling for '
              '--side {} ({:.3f} m, set from measured clearance at the '
              'zero mark). Re-check clearance by hand before using --force '
              'to override.'.format(args.distance, args.side, ceiling),
              file=sys.stderr)
        return 1

    if not acquire_lock():
        return 1

    rclpy.init()
    node = RepeatabilityTester(args)
    try:
        node.run()
    except KeyboardInterrupt:
        node.get_logger().warn('interrupted -- return-to-start already '
                                'attempted by run()\'s own finally block')
    except RuntimeError as exc:
        print('ERROR: {}'.format(exc), file=sys.stderr)
        node.destroy_node()
        rclpy.shutdown()
        release_lock()
        return 1
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        release_lock()
    return 0


if __name__ == '__main__':
    sys.exit(main())
