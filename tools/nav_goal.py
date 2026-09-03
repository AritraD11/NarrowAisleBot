#!/usr/bin/env python3
"""
nav_goal.py -- build a Nav2 goal from where the robot ACTUALLY is, not from
an assumed map origin.

WHY THIS EXISTS
    Until 14 Aug 2026 this project assumed a fresh slam_toolbox session put
    the map's origin on the robot, so "1.5 m forward from the zero mark"
    could be written straight down as a map-frame coordinate. That
    assumption is wrong (Research_Journal.md section 17.18): slam_toolbox
    takes the robot's current ODOM pose as the first scan's pose, which
    makes map->odom identity and plants the map frame on the odom frame,
    not on the robot. map->base_link at session start is therefore whatever
    odometry had accumulated since odometry_publisher last started. (Before
    section 17.38 there was also a constant -90 deg on top of that; it is
    gone, and map now shares base_link's +X=right/+Y=forward convention.)

    Goals do not need that mystery solved. A goal only needs to be correct
    in the map frame, and the robot's real pose in the map frame is
    something TF will state directly. This reads it and does the rotation
    arithmetic, so "N metres forward" means N metres forward of the robot
    as it is standing right now, whatever the map origin happens to be.

AXES -- READ THIS BEFORE CHANGING ANY ARITHMETIC BELOW
    base_link on this robot is NOT REP-103. +X is the robot's RIGHT and +Y
    is the robot's FORWARD (section 17.10, and the AXES note at the top of
    nav2_params.yaml). So "forward" is the body +Y axis, which is why
    --forward feeds the y component of the body-frame offset and --right
    feeds x. This is the single place in this script where the convention
    matters; everything else is frame-agnostic vector algebra.

    Since section 17.38 the MAP frame uses that same convention, so the
    two agree and a robot standing on a freshly-zeroed mark reads a yaw of
    0 deg, not -90. If you see -90 deg there, you are running against a
    pre-17.38 odometry_publisher.py or a map recorded by one -- check with
    `ros2 run tf2_ros tf2_echo odom base_link` before trusting the output.

WHAT IT PRINTS
    Two ready-to-paste commands:
      1. GO      -- the requested offset, in map coordinates.
      2. RETURN  -- the robot's pose right now, verbatim, as a goal.
    Copy BOTH somewhere before you send the first one. The return goal is
    only knowable while the robot is still standing at the start point;
    once it has driven off, recovering it means trusting an origin this
    project has just finished establishing it cannot trust.

    Goal orientation defaults to the robot's current orientation -- "drive
    forward without turning." Override with --goal-yaw-deg if you want it
    to face somewhere specific on arrival.

Usage (on the Pi, with the mapping stack and Nav2 both up):

    python3 nav_goal.py                      # 1.5 m forward, default
    python3 nav_goal.py --forward 1.0
    python3 nav_goal.py --forward 0.0 --right 0.5      # pure strafe
    python3 nav_goal.py --forward 2.0 --goal-yaw-deg -90

This script only READS TF and prints text. It never sends a goal and never
publishes anything -- sending stays a deliberate act you perform yourself,
with a hand near the E-stop.

Pure rclpy + stdlib, no numpy, matching the rest of the on-Pi tooling
(scan_bearing.py, run_report.py, scan_relay.py).
"""

import argparse
import math
import sys

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener, TransformException


def yaw_from_quat(q):
    """Yaw only -- the robot is planar, roll and pitch are always zero here."""
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def quat_from_yaw(yaw):
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)


def body_to_map(x, y, yaw, right, forward):
    """Rotate a body-frame offset into the map frame and add it to the pose.

    The body-frame offset is (right, forward) = (+X, +Y) on this robot --
    see the AXES note in the module docstring.
    """
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    return (
        x + right * cos_y - forward * sin_y,
        y + right * sin_y + forward * cos_y,
    )


def send_goal_command(frame, x, y, yaw):
    qx, qy, qz, qw = quat_from_yaw(yaw)
    pose = (
        "{{pose: {{header: {{frame_id: {frame}}}, pose: {{"
        "position: {{x: {x:.4f}, y: {y:.4f}, z: 0.0}}, "
        "orientation: {{x: {qx:.6f}, y: {qy:.6f}, z: {qz:.6f}, w: {qw:.6f}}}"
        "}}}}}}"
    ).format(frame=frame, x=x, y=y, qx=qx, qy=qy, qz=qz, qw=qw)
    return (
        "ros2 action send_goal --feedback /navigate_to_pose "
        'nav2_msgs/action/NavigateToPose "{pose}"'.format(pose=pose)
    )


def lookup(node, tf_buffer, target, source, timeout):
    """Spin until the transform is available, or give up with a clear reason."""
    deadline = node.get_clock().now().nanoseconds + int(timeout * 1e9)
    last_error = None
    while rclpy.ok() and node.get_clock().now().nanoseconds < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
        try:
            return tf_buffer.lookup_transform(target, source, Time())
        except TransformException as exc:
            last_error = exc
    raise RuntimeError(
        "could not read {} -> {} within {:.0f} s.\n"
        "  Last TF error: {}\n"
        "  Is the mapping stack running? map is published by slam_toolbox "
        "(mapping_full.launch.py) and odom->base_link by odometry_publisher "
        "(aislebot.service). Check with: ros2 run tf2_ros tf2_echo {} {}"
        .format(target, source, timeout, last_error, target, source)
    )


def main():
    parser = argparse.ArgumentParser(
        description="Build a Nav2 goal from the robot's measured map pose.",
    )
    parser.add_argument('--forward', type=float, default=1.5,
                        help="metres forward in the robot's own frame "
                             "(body +Y on this robot). Negative = reverse. "
                             "Default 1.5.")
    parser.add_argument('--right', type=float, default=0.0,
                        help="metres to the robot's right (body +X). "
                             "Negative = left. Default 0 (no strafe).")
    parser.add_argument('--goal-yaw-deg', type=float, default=None,
                        help="map-frame yaw to arrive facing, degrees. "
                             "Default: keep the robot's current orientation.")
    parser.add_argument('--map-frame', default='map')
    parser.add_argument('--base-frame', default='base_link')
    parser.add_argument('--timeout', type=float, default=10.0,
                        help='seconds to wait for TF. Default 10.')
    args = parser.parse_args()

    rclpy.init()
    node = Node('nav_goal')
    tf_buffer = Buffer()
    TransformListener(tf_buffer, node)

    try:
        tf = lookup(node, tf_buffer, args.map_frame, args.base_frame,
                    args.timeout)
    except RuntimeError as exc:
        print('ERROR: {}'.format(exc), file=sys.stderr)
        node.destroy_node()
        rclpy.shutdown()
        return 1

    t = tf.transform.translation
    cur_yaw = yaw_from_quat(tf.transform.rotation)
    goal_x, goal_y = body_to_map(t.x, t.y, cur_yaw, args.right, args.forward)
    goal_yaw = (math.radians(args.goal_yaw_deg)
                if args.goal_yaw_deg is not None else cur_yaw)

    print()
    print('MEASURED NOW  {} -> {}'.format(args.map_frame, args.base_frame))
    print('  position   x = {:+.4f}   y = {:+.4f}'.format(t.x, t.y))
    print('  yaw        {:+.2f} deg   ({:+.4f} rad)'
          .format(math.degrees(cur_yaw), cur_yaw))
    print('  reminder   yaw near -90 deg is EXPECTED on this robot: base_link')
    print('             +X is the robot\'s RIGHT, not its front (sec 17.10).')
    print()
    print('REQUESTED OFFSET, in the robot\'s own frame')
    print('  forward {:+.3f} m   right {:+.3f} m'
          .format(args.forward, args.right))
    print('  -> map   x = {:+.4f}   y = {:+.4f}   yaw {:+.2f} deg'
          .format(goal_x, goal_y, math.degrees(goal_yaw)))
    print()
    print('=' * 72)
    print('GO -- send this one:')
    print()
    print(send_goal_command(args.map_frame, goal_x, goal_y, goal_yaw))
    print()
    print('=' * 72)
    print('RETURN -- the pose the robot is in RIGHT NOW. Copy this BEFORE')
    print('sending the GO command; it is not recoverable afterwards.')
    print()
    print(send_goal_command(args.map_frame, t.x, t.y, cur_yaw))
    print()
    print('=' * 72)

    node.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
