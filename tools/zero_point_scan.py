#!/usr/bin/env python3
"""
zero_point_scan.py -- autonomously build a full 360 degree base map from the
robot's current position, self-detecting how much motion each heading needs,
and always ending back at the exact starting pose.

WHY THIS EXISTS
    Manual testing on 14 Aug 2026 found that this robot's SLAM config
    (slam_nodom.yaml -- deliberately "no external odometry, scan-matching
    only", see that file's own header) does NOT reliably add new map area
    from pure rotation alone, even well past slam_toolbox's own
    minimum_travel_heading threshold. Checked directly against slam_toolbox's
    source (shouldProcessScan in slam_toolbox_common.cpp): the early-stage
    gate lets a rotation-only scan through fine, so that is not the cause.
    The likely real cause, matching a well-known weak point of scan-matching
    SLAM run with no motion prior: a 360-degree lidar's rotation-only scan is
    near-identical to the previous one just re-indexed by angle, giving the
    matcher very little unambiguous signal to confidently commit a pose
    update. The smallest translation immediately introduces parallax --
    near things shift more than far things -- and reliably unlocks it.
    Confirmed by hand, four times in a row, same result every time: rotate
    alone -> nothing; nudge forward or sideways -> the map updates
    immediately.

    This script automates exactly that hand-discovered procedure: rotate to
    the next heading, check whether the map actually grew, and ONLY nudge if
    it didn't -- never a blind fixed nudge every step.

WHY NavigateToPose FOR EVERYTHING, NOT Nav2's Spin/BackUp BEHAVIORS
    Spin and BackUp would be the obvious tool for this, and this script
    still deliberately does not call them: every motion here, rotation and
    nudge alike, goes through NavigateToPose, the one path already proven
    correct on hardware.

    CORRECTION to this script's original reasoning, before it ever ran.
    That reasoning said choosing NavigateToPose "sidesteps the whole
    question" of behavior_server's missing cmd_vel remap. It does not, and
    could not: bt_navigator's default tree
    (navigate_to_pose_w_replanning_and_recovery.xml) invokes Spin and
    BackUp AUTOMATICALLY as recovery whenever a goal fails. Not calling
    them directly buys nothing -- any failed goal here reaches them anyway.
    Worse, this script's rotate-in-place goals were the most likely thing
    yet built to fail, because SimpleProgressChecker scored a pure rotation
    as zero progress (see nav2_params.yaml's progress_checker comment).
    Unremapped, BackUp's 0.30 m reverse skips both collision_monitor and
    cmd_vel_axis_adapter and aims into the measured 90 degree rear blind
    sector (sec 17.15) -- the one direction the LiDAR cannot see.

    Both halves are now fixed, together, before this script's first
    hardware run: behavior_server is remapped to cmd_vel_nav in
    nav2_slam.launch.py, and the progress checker counts rotation as
    progress. Spin/BackUp are still not called from here, but they are now
    safe if the behaviour tree reaches for them on its own.

HOW "DID THE MAP GROW" IS DETECTED
    Subscribes to /map (transient-local, matching how slam_toolbox
    publishes it) and counts cells that are not -1 (unknown). A meaningful
    increase in that count since the last checkpoint means new area was
    actually written to the map, not just seen live -- the same distinction
    covered in Research_Journal.md sec 17.19's live-scan-vs-committed-map
    discussion. A small minimum-growth threshold filters out map noise so a
    handful of flickering cells doesn't count as "it worked."

SAFETY
    - Every motion is a NavigateToPose goal on the already-validated,
      already-slow (0.08 m/s cap) path -- nothing here moves faster or
      differently than tonight's proven-safe test goals.
    - Nudges are small and bounded (default 0.15 m) and capped at a small
      number of attempts per heading (default 3) -- a heading that
      genuinely can't be unlocked (most likely real geometry blocking that
      direction, not a bug -- see the two-kinds-of-blind-spot discussion
      the same session) is skipped rather than chased indefinitely.
    - After every successful nudge, the robot returns to the anchor point
      at that heading before continuing, keeping net drift from the start
      pose small throughout the run, not just at the end.
    - A time budget (default 150 s) stops the run early rather than letting
      it run unbounded; the final return-to-start step below runs
      regardless of whether the budget was hit.
    - The VERY LAST action, unconditionally, is a goal back to the exact
      original pose (position AND heading) -- this is what guarantees the
      robot ends at zero even if some headings were skipped along the way.
    - Ctrl-C attempts the same final return-to-start before exiting, rather
      than leaving the robot wherever it happened to be mid-sequence.

THIS IS A NEW, NEVER-TESTED-ON-HARDWARE BEHAVIOR.
    Treat the first run like every other new capability tonight was
    treated: small first, hand near the E-stop, watch it. Suggested first
    test, not the full run:
        python3 zero_point_scan.py --step-deg 90 --max-duration 40
    Only four headings, ~40s ceiling -- enough to see the self-detect
    logic actually work before trusting the full 2-3 minute version:
        python3 zero_point_scan.py

Usage:
    python3 zero_point_scan.py                        # full 360, ~2.5 min cap
    python3 zero_point_scan.py --step-deg 90 --max-duration 40   # quick smoke test
    python3 zero_point_scan.py --step-deg 20 --nudge-dist 0.10   # finer, gentler

Pure rclpy + stdlib, matching the rest of the on-Pi tooling. Requires the
mapping stack and Nav2 both already up (same prerequisites as nav_goal.py's
GO/RETURN commands).
"""

import argparse
import math
import os
import sys
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.time import Time
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
from tf2_ros import Buffer, TransformListener, TransformException
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import OccupancyGrid


def yaw_from_quat(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def quat_from_yaw(yaw):
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)


def normalize_angle(a):
    return math.atan2(math.sin(a), math.cos(a))


def body_to_map(x, y, yaw, right, forward):
    """Same convention as nav_goal.py: body +X = right, +Y = forward
    (sec 17.10) -- this is the one place that matters here."""
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    return (
        x + right * cos_y - forward * sin_y,
        y + right * sin_y + forward * cos_y,
    )


class ZeroPointScanner(Node):

    def __init__(self, args):
        super().__init__('zero_point_scanner')
        self.args = args

        self.tf_buffer = Buffer()
        TransformListener(self.tf_buffer, self)

        map_qos = QoSProfile(
            depth=1,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            reliability=QoSReliabilityPolicy.RELIABLE,
        )
        self.latest_map = None
        self.create_subscription(OccupancyGrid, '/map', self._map_cb, map_qos)

        self.nav_client = ActionClient(self, NavigateToPose, '/navigate_to_pose')

    def _map_cb(self, msg):
        self.latest_map = msg

    def spin_until(self, predicate, timeout_sec):
        deadline = time.monotonic() + timeout_sec
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.2)
            if predicate():
                return True
        return False

    def known_cell_count(self):
        if self.latest_map is None:
            return None
        return sum(1 for c in self.latest_map.data if c != -1)

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
        # status 4 == STATUS_SUCCEEDED (action_msgs/msg/GoalStatus)
        return result.status == 4

    def map_grew_since(self, baseline_count):
        # Give slam_toolbox a chance to publish a fresh map after settling
        # (map_update_interval: 1.0 in slam_nodom.yaml), and SPIN for that
        # whole window rather than sleeping through it. /map only reaches
        # latest_map via a callback, and a blind sleep followed by a single
        # spin_once may service the TF listener instead -- leaving the count
        # a cycle stale and reporting "no growth" for a heading that actually
        # worked, which would then trigger a nudge that was never needed.
        deadline = time.monotonic() + self.args.map_settle
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        current = self.known_cell_count()
        if current is None or baseline_count is None:
            # Loud, because the two failure modes look identical from the
            # outside: "the nudge did not reveal anything" and "/map never
            # arrived so nothing could ever be counted".
            self.get_logger().warn(
                '    no /map to measure (baseline={}, current={}) -- '
                'is slam_toolbox running?'.format(baseline_count, current))
            return False, current

        delta = current - baseline_count
        grew = delta >= self.args.min_growth_cells
        # Print the actual numbers, not just the verdict. The 15 Aug 2026
        # run reported "no growth" 6 times and there was no way to tell from
        # the log whether the map was static, growing slightly under
        # threshold, or absent entirely -- three very different problems.
        self.get_logger().info(
            '    map cells {} -> {} ({:+d}, need +{}) => {}'.format(
                baseline_count, current, delta,
                self.args.min_growth_cells, 'GREW' if grew else 'no change'))
        return grew, current

    def run(self):
        start_x, start_y, start_yaw = self.measure_pose()
        self.get_logger().info(
            'zero-point scan starting from ({:.3f}, {:.3f}) @ {:.1f} deg'.format(
                start_x, start_y, math.degrees(start_yaw)))

        # Let one map message arrive before taking the first baseline.
        self.spin_until(lambda: self.latest_map is not None, 3.0)
        baseline = self.known_cell_count()

        n_steps = max(1, round(360.0 / self.args.step_deg))
        step_rad = math.radians(self.args.step_deg)
        deadline = time.monotonic() + self.args.max_duration

        nudge_pattern = [
            (self.args.nudge_dist, 0.0),    # strafe right
            (-self.args.nudge_dist, 0.0),   # strafe left
            (0.0, self.args.nudge_dist),    # forward, last resort
        ]

        completed, skipped = 0, 0

        try:
            for i in range(n_steps):
                if time.monotonic() > deadline:
                    self.get_logger().warn(
                        'time budget ({:.0f}s) exhausted at heading {}/{} '
                        '-- stopping early, still returning to start'.format(
                            self.args.max_duration, i, n_steps))
                    break

                target_yaw = normalize_angle(start_yaw + i * step_rad)
                self.get_logger().info('heading {}/{}: rotating to {:.1f} deg'.format(
                    i + 1, n_steps, math.degrees(target_yaw)))

                if not self.send_goal_and_wait(start_x, start_y, target_yaw):
                    self.get_logger().warn('rotation goal did not succeed, skipping heading')
                    skipped += 1
                    continue

                grew, baseline = self.map_grew_since(baseline)
                if grew:
                    self.get_logger().info('  map grew from rotation alone -- next heading')
                    completed += 1
                    continue

                self.get_logger().info('  no growth from rotation -- trying a nudge')
                unlocked = False
                for attempt, (right, forward) in enumerate(nudge_pattern):
                    if attempt >= self.args.max_nudge_attempts:
                        break
                    nx, ny = body_to_map(start_x, start_y, target_yaw, right, forward)
                    self.get_logger().info(
                        '    nudge attempt {}: right={:.2f} forward={:.2f}'.format(
                            attempt + 1, right, forward))
                    if not self.send_goal_and_wait(nx, ny, target_yaw):
                        continue
                    grew, baseline = self.map_grew_since(baseline)
                    if grew:
                        self.get_logger().info('    unlocked it -- returning to anchor')
                        self.send_goal_and_wait(start_x, start_y, target_yaw)
                        unlocked = True
                        break

                if unlocked:
                    completed += 1
                else:
                    self.get_logger().warn(
                        '  heading {:.1f} deg would not unlock after {} nudges -- '
                        'likely real geometry blocking this direction, moving on'.format(
                            math.degrees(target_yaw), self.args.max_nudge_attempts))
                    skipped += 1
                    # Make sure we are still at the anchor before continuing.
                    self.send_goal_and_wait(start_x, start_y, target_yaw)

        finally:
            # Runs on normal completion, on a time-budget break, AND on
            # Ctrl-C (KeyboardInterrupt propagates through this finally too)
            # -- this is the one guaranteed return-to-start, not the
            # try/except in main(). Guarded so a failure here during
            # shutdown doesn't hide whatever originally interrupted the run.
            self.get_logger().info(
                'returning to exact start pose ({:.3f}, {:.3f}) @ {:.1f} deg'.format(
                    start_x, start_y, math.degrees(start_yaw)))
            try:
                self.send_goal_and_wait(start_x, start_y, start_yaw)
            except Exception as exc:
                self.get_logger().error('return-to-start failed: {}'.format(exc))

        self.get_logger().info(
            'zero-point scan done: {} headings completed, {} skipped, out of {}'.format(
                completed, skipped, n_steps))


LOCK_PATH = '/tmp/zero_point_scan.lock'


def acquire_lock():
    """Refuse to start if another scan is already driving the robot.

    The dashboard's CALIBRATE button runs this same script as a subprocess.
    Its own guard only stops a second BUTTON press -- it cannot see a copy
    started by hand in a terminal. Two instances both issuing NavigateToPose
    goals preempt each other continuously, which looks exactly like the
    robot moving at random. Cheap to prevent, confusing and unsafe to debug.
    """
    if os.path.exists(LOCK_PATH):
        try:
            with open(LOCK_PATH) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)          # signal 0 = liveness test, no signal sent
        except (ValueError, OSError):
            pass                     # stale lock from a killed run; take it
        else:
            print('ERROR: another zero_point_scan.py is already running '
                  '(pid {}). Stop it first -- two of them fight over '
                  '/navigate_to_pose.'.format(pid), file=sys.stderr)
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
        description='Autonomous 360 degree base-map scan, self-detecting '
                    'when a nudge is needed, always ending at the start pose.')
    parser.add_argument('--step-deg', type=float, default=20.0,
                        help='degrees per heading step. Default 20 (~18 steps).')
    parser.add_argument('--max-duration', type=float, default=150.0,
                        help='overall time budget in seconds. Default 150 (2.5 min).')
    # MUST stay above slam_nodom.yaml's minimum_travel_distance (0.2 m).
    # slam_toolbox refuses to even PROCESS a scan taken closer than that to
    # the last processed one (with 10% slack, so ~0.179 m effective), so a
    # nudge below it cannot grow the map no matter how good the parallax is
    # -- and because this script returns to the anchor after every attempt,
    # short nudges never accumulate past the gate either. The original 0.15
    # default was below the gate and produced exactly that: hardware run
    # 15 Aug 2026, 0 headings completed, every single growth check negative.
    # Raise minimum_travel_distance's counterpart in slam_nodom.yaml if this
    # is ever lowered; the two are coupled and only one of them is obvious.
    parser.add_argument('--nudge-dist', type=float, default=0.25,
                        help='metres per nudge attempt. Default 0.25. Must '
                             "exceed slam_nodom.yaml's minimum_travel_distance "
                             '(0.2) or the map can never register the nudge.')
    parser.add_argument('--max-nudge-attempts', type=int, default=3,
                        help='give up on a heading after this many failed nudges.')
    parser.add_argument('--min-growth-cells', type=int, default=30,
                        help='minimum newly-known cells to count as "the map grew". '
                             'Filters out noise. Default 30.')
    parser.add_argument('--map-settle', type=float, default=1.5,
                        help='seconds to wait (while spinning) for a fresh /map '
                             'before deciding whether it grew. Must exceed '
                             "slam_nodom.yaml's map_update_interval (1.0). "
                             'Default 1.5.')
    parser.add_argument('--map-frame', default='map')
    parser.add_argument('--base-frame', default='base_link')
    args = parser.parse_args()

    if not acquire_lock():
        return 1

    rclpy.init()
    node = ZeroPointScanner(args)
    try:
        node.run()
    except KeyboardInterrupt:
        # run()'s own try/finally already attempted the return-to-start
        # above by the time this is reached -- nothing further to do here.
        node.get_logger().warn('interrupted')
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
