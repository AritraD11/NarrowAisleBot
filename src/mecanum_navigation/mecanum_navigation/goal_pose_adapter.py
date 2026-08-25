#!/usr/bin/env python3
"""
goal_pose_adapter.py -- let a Foxglove drag-arrow mean "point the NOSE this
way", instead of "point the RIGHT SIDE this way".

THE PROBLEM
    Foxglove's 3D panel "Publish Pose" tool sends a PoseStamped whose yaw is
    simply the direction you dragged, in the map frame. bt_navigator takes
    that yaw as base_link's target orientation, verbatim.

    On this robot base_link's +X is the robot's RIGHT, not its front
    (odometry_publisher.py's deliberate constant -90 deg rotation, matching
    the validated LiDAR calibration -- Research_Journal.md sec 17.10). So a
    goal yaw of theta parks the robot with its SIDE facing theta and its
    nose facing theta + 90 deg.

    Recorded in sec 17.20 as a live workaround: "drag 90 degrees clockwise
    of the intended heading until a correction node exists." This is that
    node. Doing the subtraction in your head, correctly, every time, while
    watching a 45 kg robot, is not a good long-term plan -- and in a narrow
    aisle a 90 deg error in FINAL heading is not cosmetic: a 1.12 x 0.48 m
    chassis rotating to the wrong heading at the goal can put a corner into
    a wall the planner never intended to approach.

THE CONVERSION
    published_yaw = dragged_yaw - 90 deg

    which is exactly the manual "drag 90 deg clockwise" rule, applied by
    software instead of by the operator. Position passes through untouched
    -- only the goal's ORIENTATION was ever wrong. That is also why the old
    workaround was survivable: a mis-dragged arrow sent the robot to the
    right PLACE facing the wrong way, never to the wrong place.

WHY A SEPARATE TOPIC, AND WHY THIS CHANGES NOTHING UNTIL YOU OPT IN
    bt_navigator subscribes to a hardcoded /goal_pose (verified in
    nav2_bt_navigator's navigate_to_pose.cpp, sec 17.20). This node listens
    on /goal_pose_click and republishes to /goal_pose, so:

      - Leave Foxglove pointed at /goal_pose  -> this node is inert, the
        old 90-deg-clockwise rule still applies, nothing changes.
      - Point Foxglove at /goal_pose_click    -> drag where you want the
        NOSE to end up.

    Deliberately opt-in rather than intercepting /goal_pose, because a node
    that silently rotates every goal on the system is exactly the kind of
    invisible transform that produced the sec 17.19 axis bug in the first
    place. One topic name is the whole switch, and it is visible in the
    Foxglove panel settings where the operator can see it.

    Do NOT also leave a second publisher on /goal_pose expecting both to
    work; pick one topic in the panel settings and stay with it.

Usage (started automatically by nav2_slam.launch.py):
    ros2 run mecanum_navigation goal_pose_adapter
"""

import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped


def yaw_from_quat(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class GoalPoseAdapter(Node):

    def __init__(self):
        super().__init__('goal_pose_adapter')

        # Same coupling rule as odometry_publisher.py and
        # cmd_vel_axis_adapter.py: if scan_relay's yaw_offset is ever
        # re-derived, this constant must be re-derived with it. Exposed as a
        # parameter so that re-derivation is a launch argument rather than
        # an edit to three files that must agree.
        self.declare_parameter('yaw_offset_deg', -90.0)
        self.declare_parameter('input_topic',  '/goal_pose_click')
        self.declare_parameter('output_topic', '/goal_pose')

        self.offset = math.radians(
            self.get_parameter('yaw_offset_deg').value)
        in_topic  = self.get_parameter('input_topic').get_parameter_value().string_value
        out_topic = self.get_parameter('output_topic').get_parameter_value().string_value

        self.pub = self.create_publisher(PoseStamped, out_topic, 10)
        self.create_subscription(PoseStamped, in_topic, self._cb, 10)

        self.get_logger().info(
            'goal_pose_adapter: {} -> {}, yaw {:+.1f} deg. Drag the arrow '
            'where the NOSE should point.'.format(
                in_topic, out_topic,
                math.degrees(self.offset)))

    def _cb(self, msg: PoseStamped):
        dragged = yaw_from_quat(msg.pose.orientation)
        corrected = math.atan2(math.sin(dragged + self.offset),
                               math.cos(dragged + self.offset))

        out = PoseStamped()
        out.header = msg.header
        out.pose.position = msg.pose.position          # position is untouched
        out.pose.orientation.x = 0.0
        out.pose.orientation.y = 0.0
        out.pose.orientation.z = math.sin(corrected / 2.0)
        out.pose.orientation.w = math.cos(corrected / 2.0)
        self.pub.publish(out)

        self.get_logger().info(
            'goal ({:.2f}, {:.2f}) nose {:.1f} deg -> base_link yaw {:.1f} deg'.format(
                msg.pose.position.x, msg.pose.position.y,
                math.degrees(dragged), math.degrees(corrected)))


def main(args=None):
    rclpy.init(args=args)
    node = GoalPoseAdapter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
