#!/usr/bin/env python3
"""
cmd_vel_axis_adapter.py -- an IDENTITY pass-through since 5 Oct 2026.

WHAT IT USED TO DO
    Until 5 Oct 2026 base_link was +X = right, +Y = nose while the wheel
    kinematics (mecanum_teleop_asymmetric.py, the dashboard, the joy node)
    read /cmd_vel as standard REP-103 (linear.x = forward, linear.y = left).
    Nav2 writes velocity in base_link's axes, so this node rotated it:

        out.x = in.y        out.y = -in.x

    The first autonomous goal (Research_Journal.md 17.19) travelled 0.956 m
    at 88.4 deg to the commanded direction before the E-STOP, which is why
    it existed.

WHY IT IS AN IDENTITY NOW
    base_link, odom and map are standard REP-103 (+X nose, +Y left), the same
    convention the wheel kinematics always used. Nav2's velocity and the
    wheel code now agree, so there is nothing to rotate:

        out.x = in.x        out.y = in.y

    It is kept as a pass-through, not deleted, for one reason: the first
    drive after a frame change must not also change the command topology.
    Same nodes, same topics, one variable moved. Once the standard frame has
    driven the regression goals (docs/Axis_Refactor_Plan.md, stage 6) this
    node, its launch entries and its setup.py entry point are deleted and
    collision_monitor writes cmd_vel_nav_out directly.

    tools/verify_axis_chain.py fails if the rotation comes back, and fails
    if the node is deleted but a launch file still starts it.

WHERE IT SITS IN THE CHAIN (unchanged)
    controller_server -> /cmd_vel_nav
      -> velocity_smoother -> /cmd_vel_smoothed
        -> collision_monitor -> /cmd_vel_baselink
          -> THIS NODE -> /cmd_vel_nav_out
            -> twist_mux -> /cmd_vel -> teleop_asym -> wheels

    Still LAST, after collision_monitor, and still publishes one zero Twist on
    shutdown so a Ctrl-C on Nav2 stops the robot at once, not 500 ms later.

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
            'cmd_vel axis adapter: {} -> {} (identity: base_link and the '
            'wheel kinematics are both +X=forward, +Y=left)'.format(
                in_topic, out_topic))

    def cb(self, msg):
        out = Twist()
        out.linear.x = msg.linear.x        # forward, both sides
        out.linear.y = msg.linear.y        # left, both sides
        # z and the angular fields pass through untouched.
        out.linear.z = msg.linear.z
        out.angular.x = msg.angular.x
        out.angular.y = msg.angular.y
        out.angular.z = msg.angular.z
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
