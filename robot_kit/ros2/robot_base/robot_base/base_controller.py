#!/usr/bin/env python3
"""
base_controller - body velocity in, wheel velocities out.

  subscribes  /cmd_vel     Twist              REP-103: linear.x forward, linear.y left,
                                              angular.z counter-clockwise
  publishes   /wheel_cmd   Float64MultiArray  rad/s per wheel, in wheel order

The geometry comes from config/robot.yaml (generate.py). linear.y is used
only on a holonomic base (mecanum, omni) and ignored otherwise. If any wheel
would exceed max_wheel_speed, all wheels are scaled down together, so a
curve stays the same curve, just slower.

No /cmd_vel for cmd_timeout seconds: publish zeros once. twist_mux has its
own 0.5 s timeouts upstream and mcu_bridge another downstream; three layers
on purpose.
"""

import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

from robot_base.kinematics import DriveModel, model_from_params


class BaseController(Node):

    def __init__(self):
        super().__init__("base_controller")
        p = self.declare_parameter
        p("drive_type", "differential")
        p("wheel_radius", 0.05)
        p("wheel_names", ["left", "right"])
        p("wheel_x", [0.0, 0.0])
        p("wheel_y", [0.15, -0.15])
        p("wheel_ax", [1.0, 1.0])
        p("wheel_ay", [0.0, 0.0])
        p("track_width_scale", 1.0)
        p("max_wheel_speed", 10.0)
        p("max_linear", 0.2)
        p("max_angular", 0.8)
        p("cmd_timeout", 0.5)
        g = lambda k: self.get_parameter(k).value  # noqa: E731

        self.model = model_from_params(list(g("wheel_names")), list(g("wheel_x")), list(g("wheel_y")),
                                       list(g("wheel_ax")), list(g("wheel_ay")), float(g("wheel_radius")),
                                       g("drive_type"), float(g("track_width_scale")))
        self.vmax_wheel = float(g("max_wheel_speed"))
        self.max_lin = float(g("max_linear"))
        self.max_ang = float(g("max_angular"))
        self.timeout = float(g("cmd_timeout"))
        self.last = 0.0
        self.nonzero = False

        self.pub = self.create_publisher(Float64MultiArray, "wheel_cmd", 10)
        self.create_subscription(Twist, "cmd_vel", self._on_twist, 10)
        self.create_timer(0.1, self._timeout_check)
        self.get_logger().info(
            f"base_controller: {g('drive_type')}, wheels {self.model.names}, "
            f"r={self.model.r}, holonomic={self.model.holonomic}")

    @staticmethod
    def _clamp(v, lim):
        return max(-lim, min(lim, v))

    def _on_twist(self, msg):
        vx = self._clamp(msg.linear.x, self.max_lin)
        vy = self._clamp(msg.linear.y, self.max_lin) if self.model.holonomic else 0.0
        wz = self._clamp(msg.angular.z, self.max_ang)
        w = DriveModel.scale_to_limit(self.model.inverse(vx, vy, wz), self.vmax_wheel)
        out = Float64MultiArray()
        out.data = [float(v) for v in w]
        self.pub.publish(out)
        self.last = time.time()
        self.nonzero = any(abs(v) > 1e-9 for v in w)

    def _timeout_check(self):
        if self.nonzero and time.time() - self.last > self.timeout:
            out = Float64MultiArray()
            out.data = [0.0] * len(self.model.wheels)
            self.pub.publish(out)
            self.nonzero = False


def main(args=None):
    rclpy.init(args=args)
    node = BaseController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
