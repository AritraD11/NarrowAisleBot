#!/usr/bin/env python3
"""
trajectory_viz.py -- record and publish the robot's ACTUAL path so it can be
seen in Foxglove against the straight line it was supposed to follow.

WHY THIS EXISTS
    19 Aug 2026: a 1.00 m strafe-right goal completed with the robot landing
    on the 1 m floor mark in X but ~5 cm off in Y, and the user's direct
    observation was that it "moved back, moved front" on the way -- i.e. the
    ENDPOINT was fine but the PATH was not a straight line. Nothing in the
    stack could show that. Nav2 publishes /plan and /local_plan (what it
    INTENDS to do) but nothing publishes where the robot actually WENT, and
    pathlog.py prints numbers rather than something you can look at.

    A Foxglove screenshot shows an end state, not a trajectory -- the same
    gap map_watch.py was built for on the mapping side (sec 17.21). This is
    that tool for the driving side.

WHAT IT PUBLISHES (all latched, so Foxglove picks them up on connect)
    /actual_path      nav_msgs/Path   -- where the robot really went, sampled
                                         from TF at --rate Hz
    /reference_path   nav_msgs/Path   -- the ideal straight line from the
                                         start pose to the commanded goal
    /trajectory_markers visualization_msgs/MarkerArray
                                      -- start point (green), goal (blue),
                                         final actual position (red), and
                                         text labels for each

    In Foxglove: 3D panel, Fixed frame = map, then enable those three topics.
    The visual you want is /reference_path (straight) vs /actual_path (what
    really happened) overlaid.

WHAT IT PRINTS ON EXIT (Ctrl-C)
    The numbers that make the picture quantitative, which is what a report
    actually needs:
      - straight-line distance start -> end
      - total path length actually travelled (>> straight-line means it
        wandered or backtracked)
      - path efficiency (straight-line / path length; 1.00 = perfect line)
      - MAX PERPENDICULAR DEVIATION from the reference line, and where it
        happened -- this is the single number for "how not-straight was it"
      - endpoint error against the commanded goal

USAGE -- run this in its own terminal BEFORE starting the drive, Ctrl-C after
    # match whatever repeatability_test.py is about to do
    python3 trajectory_viz.py --side right --distance 1.0

    # or just record, with no reference line to compare against
    python3 trajectory_viz.py --no-reference

    # the "graph plotter" manual-mapping-drive use case (sec 17.27): record
    # against zero_point instead of map, so the recorded trajectory reads
    # against a fixed origin even while /map itself is still being built.
    # Start this BEFORE driving, right after re-zeroing at the physical mark.
    python3 trajectory_viz.py --no-reference --map-frame zero_point

Writes the sampled path to ~/aislebot_logs/trajectory_<timestamp>.csv,
including an epoch_s column (wall-clock, same clock ROS 2's own console
logs use) -- to correlate a jump in the plot against what slam_toolbox was
doing at that moment, capture its terminal too:
    ros2 launch mecanum_robot mapping_full.launch.py 2>&1 | \
        tee ~/aislebot_logs/slam_$(date +%Y%m%d_%H%M%S).log
then grep the log around the epoch_s of interest.

Pure rclpy + stdlib, matching the rest of the on-Pi tooling.
"""

import argparse
import csv
import math
import os
import sys
import time
from datetime import datetime

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
from tf2_ros import Buffer, TransformListener, TransformException
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped
from visualization_msgs.msg import Marker, MarkerArray


def yaw_from_quat(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def body_to_map(x, y, yaw, right, forward):
    """Body +X = right, +Y = forward on this robot (sec 17.10) -- identical
    convention to nav_goal.py, zero_point_scan.py and repeatability_test.py.
    Kept consistent deliberately: four tools disagreeing about which way is
    forward is exactly the class of bug this project keeps finding."""
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    return (
        x + right * cos_y - forward * sin_y,
        y + right * sin_y + forward * cos_y,
    )


SIDE_VECTOR = {
    'right': (1.0, 0.0),
    'left':  (-1.0, 0.0),
    'front': (0.0, 1.0),
    'rear':  (0.0, -1.0),
}


def point_line_distance(px, py, ax, ay, bx, by):
    """Perpendicular distance from point P to the SEGMENT A->B.

    Segment, not infinite line: if the robot overshoots past the goal, the
    honest 'how far off the intended path' answer is the distance to the
    segment's end, not to an imaginary continuation of it.
    """
    dx, dy = bx - ax, by - ay
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / seg_len_sq
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


class TrajectoryViz(Node):

    def __init__(self, args):
        super().__init__('trajectory_viz')
        self.args = args

        self.tf_buffer = Buffer()
        TransformListener(self.tf_buffer, self)

        # TRANSIENT_LOCAL so a Foxglove client that connects (or reconnects)
        # mid-run still receives the path already accumulated, rather than
        # only whatever arrives after it happens to subscribe.
        latched = QoSProfile(
            depth=1,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            reliability=QoSReliabilityPolicy.RELIABLE,
        )
        self.actual_pub = self.create_publisher(Path, '/actual_path', latched)
        self.ref_pub = self.create_publisher(Path, '/reference_path', latched)
        self.marker_pub = self.create_publisher(
            MarkerArray, '/trajectory_markers', latched)

        self.samples = []      # (t, x, y, yaw, epoch_s)
        self.start = None      # (x, y, yaw)
        self.goal = None       # (x, y) or None

    def measure_pose(self, timeout=10.0):
        deadline = time.monotonic() + timeout
        last_error = None
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            try:
                tf = self.tf_buffer.lookup_transform(
                    self.args.map_frame, self.args.base_frame, Time())
                t = tf.transform.translation
                return t.x, t.y, yaw_from_quat(tf.transform.rotation)
            except TransformException as exc:
                last_error = exc
        raise RuntimeError('could not read {} -> {}: {}'.format(
            self.args.map_frame, self.args.base_frame, last_error))

    def _path_msg(self, points):
        msg = Path()
        msg.header.frame_id = self.args.map_frame
        msg.header.stamp = self.get_clock().now().to_msg()
        for (x, y) in points:
            ps = PoseStamped()
            ps.header = msg.header
            ps.pose.position.x = x
            ps.pose.position.y = y
            ps.pose.orientation.w = 1.0
            msg.poses.append(ps)
        return msg

    def _marker(self, mid, x, y, r, g, b, label):
        m = Marker()
        m.header.frame_id = self.args.map_frame
        m.header.stamp = self.get_clock().now().to_msg()
        m.ns = 'trajectory'
        m.id = mid
        m.type = Marker.SPHERE
        m.action = Marker.ADD
        m.pose.position.x = x
        m.pose.position.y = y
        m.pose.position.z = 0.05
        m.pose.orientation.w = 1.0
        m.scale.x = m.scale.y = m.scale.z = 0.08
        m.color.r, m.color.g, m.color.b, m.color.a = r, g, b, 1.0

        t = Marker()
        t.header = m.header
        t.ns = 'trajectory_labels'
        t.id = mid + 100
        t.type = Marker.TEXT_VIEW_FACING
        t.action = Marker.ADD
        t.pose.position.x = x
        t.pose.position.y = y
        t.pose.position.z = 0.25
        t.pose.orientation.w = 1.0
        t.scale.z = 0.12
        t.color.r, t.color.g, t.color.b, t.color.a = r, g, b, 1.0
        t.text = label
        return [m, t]

    def publish_all(self):
        pts = [(s[1], s[2]) for s in self.samples]
        if pts:
            self.actual_pub.publish(self._path_msg(pts))

        markers = []
        if self.start:
            markers += self._marker(0, self.start[0], self.start[1],
                                    0.0, 1.0, 0.0, 'START')
        if self.goal:
            markers += self._marker(1, self.goal[0], self.goal[1],
                                    0.0, 0.4, 1.0, 'GOAL')
            self.ref_pub.publish(self._path_msg(
                [(self.start[0], self.start[1]), self.goal]))
        if pts:
            markers += self._marker(2, pts[-1][0], pts[-1][1],
                                    1.0, 0.0, 0.0, 'ACTUAL END')
        if markers:
            arr = MarkerArray()
            arr.markers = markers
            self.marker_pub.publish(arr)

    def run(self):
        self.start = self.measure_pose()
        sx, sy, syaw = self.start
        self.get_logger().info(
            'START pose ({:.4f}, {:.4f}) @ {:.2f} deg'.format(
                sx, sy, math.degrees(syaw)))

        if not self.args.no_reference:
            right_sign, fwd_sign = SIDE_VECTOR[self.args.side]
            d = self.args.distance
            self.goal = body_to_map(sx, sy, syaw,
                                    right_sign * d, fwd_sign * d)
            self.get_logger().info(
                'REFERENCE line -> ({:.4f}, {:.4f})  [{} {:.3f} m]'.format(
                    self.goal[0], self.goal[1], self.args.side, d))

        print()
        print('Recording. Foxglove: 3D panel, Fixed frame = {}, enable'.format(
            self.args.map_frame))
        if not self.args.no_reference:
            print('  /reference_path      (the straight line it SHOULD follow)')
        print('  /actual_path         (where it really goes)')
        print('  /trajectory_markers  (start / goal / actual-end labels)')
        if self.args.map_frame == 'zero_point':
            print('Add a Grid display too (default XY plane through the '
                  "origin) -- with Fixed frame = zero_point that grid IS the "
                  "fixed x/y axes this drive is being plotted against.")
        print('Ctrl-C when the run is finished to get the summary.')
        print()

        period = 1.0 / self.args.rate
        t0 = time.monotonic()
        print('Recording started at epoch {:.2f} ({}) -- use this to line up '
              'CSV rows against slam_toolbox / ros2 log timestamps.'.format(
                  time.time(), datetime.now().strftime('%H:%M:%S')))
        next_sample = t0
        try:
            while rclpy.ok():
                rclpy.spin_once(self, timeout_sec=0.02)
                now = time.monotonic()
                if now < next_sample:
                    continue
                next_sample = now + period
                try:
                    x, y, yaw = self.measure_pose(timeout=0.5)
                except RuntimeError:
                    continue
                self.samples.append((now - t0, x, y, yaw, time.time()))
                self.publish_all()
        except KeyboardInterrupt:
            pass

        self._summarize()

    @staticmethod
    def _leg_stats(samples, ax, ay, bx, by):
        """Path length, straight-line, efficiency, endpoint error, and max
        perpendicular deviation for ONE leg (samples[0] -> samples[-1]),
        against the reference segment A->B."""
        path_len = 0.0
        for p, q in zip(samples, samples[1:]):
            path_len += math.hypot(q[1] - p[1], q[2] - p[2])
        ex, ey = samples[-1][1], samples[-1][2]
        endpoint_err = math.hypot(ex - bx, ey - by)
        worst, worst_t = 0.0, 0.0
        for (t, x, y, _yaw, _epoch) in samples:
            dev = point_line_distance(x, y, ax, ay, bx, by)
            if dev > worst:
                worst, worst_t = dev, t
        straight = math.hypot(bx - ax, by - ay)
        eff = (straight / path_len) if path_len > 1e-6 else 0.0
        return path_len, endpoint_err, worst, worst_t, eff

    def _print_leg(self, label, samples, ax, ay, bx, by):
        if len(samples) < 2:
            print('  {}: too few samples'.format(label))
            return
        path_len, endpoint_err, worst, worst_t, eff = self._leg_stats(
            samples, ax, ay, bx, by)
        print('  {} ({} samples, {:.1f}s -> {:.1f}s)'.format(
            label, len(samples), samples[0][0], samples[-1][0]))
        print('    path travelled   {:.4f} m'.format(path_len))
        print('    path efficiency  {:.3f}   (1.000 = a perfect straight line)'
              .format(eff))
        print('    endpoint error   {:.4f} m  (vs. this leg\'s target)'
              .format(endpoint_err))
        print('    MAX DEVIATION    {:.4f} m from this leg\'s line '
              '(at t={:.1f}s)'.format(worst, worst_t))

    def _summarize(self):
        if len(self.samples) < 2:
            print('\nToo few samples to summarize ({}).'.format(len(self.samples)))
            return

        sx, sy, _ = self.start
        ex, ey = self.samples[-1][1], self.samples[-1][2]

        print()
        print('=' * 68)
        print('TRAJECTORY SUMMARY   ({} samples over {:.1f} s)'.format(
            len(self.samples), self.samples[-1][0]))
        print('  overall start    ({:+.4f}, {:+.4f})'.format(sx, sy))
        print('  overall end      ({:+.4f}, {:+.4f})'.format(ex, ey))

        if not self.goal:
            path_len, _, _, _, eff = self._leg_stats(
                self.samples, sx, sy, ex, ey)
            print('  path travelled   {:.4f} m'.format(path_len))
            print('  straight-line    {:.4f} m'.format(
                math.hypot(ex - sx, ey - sy)))
        else:
            # repeatability_test.py and every driving script here always
            # do an OUT-AND-BACK -- reporting one straight-line/endpoint
            # number across the whole recording is meaningless once start
            # and end are (nearly) the same point, sec 17.24's discussion.
            # Split at the sample closest to the goal instead, so each leg
            # gets judged against what it was actually trying to reach.
            gx, gy = self.goal
            turn_i = min(range(len(self.samples)),
                        key=lambda i: math.hypot(
                            self.samples[i][1] - gx, self.samples[i][2] - gy))
            outbound = self.samples[:turn_i + 1]
            inbound = self.samples[turn_i:]
            print('  goal             ({:+.4f}, {:+.4f})'.format(gx, gy))
            print('  closest approach to goal at t={:.1f}s -- treated as '
                  'the turnaround point'.format(self.samples[turn_i][0]))
            print()
            self._print_leg('OUTBOUND leg', outbound, sx, sy, gx, gy)
            if len(inbound) >= 2:
                print()
                self._print_leg('RETURN leg  ', inbound, gx, gy, sx, sy)

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_dir = os.path.expanduser('~/aislebot_logs')
        os.makedirs(log_dir, exist_ok=True)
        csv_path = os.path.join(log_dir, 'trajectory_{}.csv'.format(ts))
        with open(csv_path, 'w', newline='') as f:
            w = csv.writer(f)
            # epoch_s is wall-clock (time.time()), the same clock ROS 2's own
            # console logs and `ros2 topic echo`/`tf2_echo` timestamps use --
            # line this column up against a terminal log to find out what
            # slam_toolbox was doing at the moment of any jump in x/y/yaw.
            w.writerow(['t_s', 'epoch_s', 'map_x', 'map_y', 'yaw_deg', 'dev_from_ref_m'])
            for (t, x, y, yaw, epoch) in self.samples:
                dev = ('' if not self.goal else '{:.4f}'.format(
                    point_line_distance(x, y, sx, sy, self.goal[0], self.goal[1])))
                w.writerow(['{:.2f}'.format(t), '{:.3f}'.format(epoch),
                            '{:.4f}'.format(x), '{:.4f}'.format(y),
                            '{:.2f}'.format(math.degrees(yaw)), dev])
        print()
        print('  CSV: {}'.format(csv_path))
        print('=' * 68)


def main():
    parser = argparse.ArgumentParser(
        description="Record the robot's actual path and publish it for "
                    "Foxglove alongside the straight line it should follow.")
    parser.add_argument('--side', choices=sorted(SIDE_VECTOR), default='right',
                        help='direction of the reference line, robot body '
                             'frame. Default right.')
    parser.add_argument('--distance', type=float, default=1.0,
                        help='length of the reference line in metres. '
                             'Default 1.0. Match whatever goal you are '
                             'about to send.')
    parser.add_argument('--no-reference', action='store_true',
                        help='just record the actual path, no reference '
                             'line and no deviation stats.')
    parser.add_argument('--rate', type=float, default=10.0,
                        help='TF sampling rate in Hz. Default 10.')
    parser.add_argument('--map-frame', default='map')
    parser.add_argument('--base-frame', default='base_link')
    args = parser.parse_args()

    rclpy.init()
    node = TrajectoryViz(args)
    try:
        node.run()
    except RuntimeError as exc:
        print('ERROR: {}'.format(exc), file=sys.stderr)
        return 1
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
