#!/usr/bin/env python3
"""
goal_pose_adapter.py -- let a Foxglove drag-arrow mean "point the NOSE this
way", instead of "point the RIGHT SIDE this way".

THE PROBLEM
    Foxglove's 3D panel "Publish Pose" tool sends a PoseStamped whose yaw is
    simply the direction you dragged, in the map frame. bt_navigator takes
    that yaw as base_link's target orientation, verbatim.

    On this robot base_link's +X is the robot's RIGHT, not its front. Until
    27 Aug 2026 the MAP frame did not share that convention -- map +X was
    whichever way the robot faced when odometry was zeroed -- so a goal yaw
    of theta parked the robot with its SIDE facing theta and its nose facing
    theta + 90 deg, and this node subtracted the difference.

    Recorded in sec 17.20 as a live workaround: "drag 90 degrees clockwise
    of the intended heading until a correction node exists." This is that
    node. Doing the subtraction in your head, correctly, every time, while
    watching a 45 kg robot, is not a good long-term plan -- and in a narrow
    aisle a 90 deg error in FINAL heading is not cosmetic: a 1.12 x 0.48 m
    chassis rotating to the wrong heading at the goal can put a corner into
    a wall the planner never intended to approach.

STATUS AFTER sec 17.38 -- THE OFFSET IS NOW ZERO
    odometry_publisher.py was publishing a rotated orientation with an
    UNrotated translation, which gave odom (and so map) REP-103's axes while
    base_link had +X=right/+Y=forward. That seam was the 90 deg this node
    existed to cancel. It is fixed at the source: map and base_link now
    share one convention, a dragged yaw already means "point the nose this
    way", and the default offset is 0.0.

    The node is deliberately KEPT rather than deleted. It is a one-line
    parameterised pass-through now, it remains the single named place where
    a goal-orientation convention could ever be re-applied, and removing it
    would mean re-plumbing /goal_pose_click -> /goal_pose everywhere it is
    referenced (phone_dashboard.py, nav_goal.py, the launch files) for no
    behavioural gain. Set yaw_offset_deg if a future change ever needs it;
    do not re-add a hardcoded constant.

THE CONVERSION
    published_yaw = dragged_yaw + yaw_offset_deg   (default 0.0)

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

        # 0.0 since sec 17.38: map and base_link share one axis convention,
        # so a dragged yaw already means "point the nose this way" and no
        # correction is needed. Kept as a parameter rather than deleted so
        # that any future convention change is a launch argument instead of
        # an edit to several files that have to agree. See this module's
        # docstring before setting it to anything else.
        self.declare_parameter('yaw_offset_deg', 0.0)
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
