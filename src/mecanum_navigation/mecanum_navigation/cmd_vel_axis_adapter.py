#!/usr/bin/env python3
"""
cmd_vel_axis_adapter.py -- rotate Nav2's velocity commands out of base_link's
TF axes and into the axes the wheel kinematics actually expect.

WHY THIS NODE EXISTS
    This robot has TWO different, individually-correct answers to "which way
    is +X on this robot," and until 14 Aug 2026 nothing reconciled them on
    the command path (Research_Journal.md §17.19):

      * base_link's TF frame (what Nav2, the costmaps, and every planner
        read) has +X = the robot's RIGHT and +Y = the robot's FORWARD. That
        is odometry_publisher.py's deliberate constant -90 deg published
        rotation, adopted in §17.10 to match the LiDAR's already-validated
        scan calibration. It is settled and correct.

      * mecanum_teleop_asymmetric.py's wheel kinematics (what actually
        drives the motors) take standard REP-103: linear.x = FORWARD,
        linear.y = LEFT. The phone dashboard, the joy node, and the PID
        calibration all speak this convention, and all of it is validated.

    §17.10 rotated odometry's PUBLISHED pose and twist -- the output side.
    The input side, /cmd_vel, was never rotated to match. Manual driving
    never noticed, because the dashboard and joy_to_aislebot were written
    against teleop_asym's convention, so producer and consumer agreed.

    Nav2 broke the tie the first time it drove: it reads the pose in TF
    axes and writes velocity in TF axes, so asking it to drive forward
    produced linear.y, which teleop_asym executed as a left strafe. The
    first-ever autonomous goal (§17.19) travelled 0.956 m at 88.4 deg to
    the commanded direction before being E-stopped -- a clean 90 deg error,
    not drift.

    Worse than a one-off wrong turn: with a constant 90 deg rotation inside
    a closed loop, Nav2 sees the cross-track error and corrects, and the
    correction is rotated 90 deg as well. That does not converge, it
    spirals. Hence "moved randomly."

WHY AN ADAPTER, RATHER THAN CHANGING EITHER SIDE
    Both conventions have strong, independent hardware validation behind
    them, which is exactly the situation §17.10 laid down a rule for: change
    the side with the weaker confirmation. Here neither side is weak. The
    LiDAR/TF convention is confirmed by the mirror calibration, the
    footprint, the safety cushion, and the tape-measured 7 cm wall gap; the
    teleop convention is confirmed by every metre the robot has ever driven
    under manual control, including the dashboard E-STOP path.

    So this converts between them explicitly at the one place they meet,
    instead of quietly editing a validated file. The manual drive path is
    untouched -- this node is started by nav2_slam.launch.py and exists only
    while Nav2 is running.

WHERE IT SITS IN THE CHAIN
    controller_server -> /cmd_vel_nav
      -> velocity_smoother -> /cmd_vel_smoothed
        -> collision_monitor -> /cmd_vel_baselink     (TF axes)
          -> THIS NODE -> /cmd_vel                    (teleop_asym axes)
            -> teleop_asym -> wheels

    Deliberately LAST, after collision_monitor. That node forward-simulates
    the footprint polygon along the commanded velocity, and both the
    polygon and the velocity it reads are in TF axes -- self-consistent, and
    it must stay that way. Only the final hand-off to the wheel code needs
    rotating. Putting this adapter earlier would feed collision_monitor a
    velocity in the wrong frame and make the safety layer forward-simulate
    the wrong direction, which is the one thing on this robot that must not
    be subtly wrong.

THE CONVERSION
    Let F be the desired forward component and L the desired left component
    of the same physical motion. Then:

        Nav2 (TF axes):     in.x  = -L   (its +X is the robot's right)
                            in.y  =  F   (its +Y is the robot's forward)

        teleop (REP-103):   out.x =  F
                            out.y =  L

    Solving:  out.x = in.y      and      out.y = -in.x

    angular.z passes through unchanged: both frames share +Z = counter-
    clockwise, and rotating a frame about Z does not change a rotation
    rate about Z.

    Sanity check against the actual §17.19 failure: Nav2 wanted forward, so
    in.y = +0.15, in.x = 0. Unadapted, teleop read that as L = +0.15 and
    strafed left -- which is exactly what the robot did. Adapted,
    out.x = +0.15 = forward. Correct.

Usage: started automatically by nav2_slam.launch.py. Standalone:
    ros2 run mecanum_navigation cmd_vel_axis_adapter

Pure rclpy + stdlib, matching the rest of the on-Pi tooling.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class CmdVelAxisAdapter(Node):

    def __init__(self):
        super().__init__('cmd_vel_axis_adapter')

        # Topic names are parameters so the chain can be rewired without
        # editing code -- but the DEFAULTS are the wiring nav2_slam.launch.py
        # and nav2_params.yaml actually use. Changing one end means changing
        # collision_monitor's cmd_vel_out_topic to match.
        self.declare_parameter('input_topic', 'cmd_vel_baselink')
        self.declare_parameter('output_topic', 'cmd_vel')

        in_topic = self.get_parameter('input_topic').value
        out_topic = self.get_parameter('output_topic').value

        # Queue depth 1, not 10: a stale velocity command is worse than a
        # dropped one. If this node ever falls behind, the right behaviour
        # is to act on the newest command and discard the backlog, never to
        # replay a queue of old motion into a moving 45 kg robot.
        self.pub = self.create_publisher(Twist, out_topic, 1)
        self.create_subscription(Twist, in_topic, self.cb, 1)

        self.get_logger().info(
            'cmd_vel axis adapter: {} (base_link TF axes, +X=right, '
            '+Y=forward) -> {} (wheel-kinematics axes, +X=forward, '
            '+Y=left)'.format(in_topic, out_topic))

    def cb(self, msg):
        out = Twist()
        out.linear.x = msg.linear.y        # forward
        out.linear.y = -msg.linear.x       # left = -right
        # z is passed through rather than dropped: it is always 0.0 on a
        # planar base, but silently zeroing a field this node does not
        # understand would be a lie about what it does.
        out.linear.z = msg.linear.z
        out.angular.x = msg.angular.x
        out.angular.y = msg.angular.y
        out.angular.z = msg.angular.z      # yaw rate is frame-invariant here
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelAxisAdapter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Publish a single zero command on the way out. Without this, the
        # last non-zero command this node ever sent is what teleop_asym
        # holds until its own watchdog fires -- a Ctrl-C on Nav2 should stop
        # the robot immediately, not 500 ms later.
        try:
            node.pub.publish(Twist())
        except Exception:
            pass
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
