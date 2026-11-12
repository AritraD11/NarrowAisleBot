#!/usr/bin/env python3
"""
wheel_odometry - wheel encoders in, /odom and TF odom -> base_link out.

  subscribes  /wheel_states  JointState  from mcu_bridge
              /odom/reset    Empty       zero the pose where the robot stands
  publishes   /odom          Odometry    REP-103, frame odom, child base_link
              TF             odom -> base_link

How it integrates. When the firmware sends extended telemetry (<L2>, the
bridge's default), each message carries every wheel's accumulated ANGLE, an
exact integral of encoder counts. This node differences those angles, runs
them through the forward kinematics to get the body displacement for that
interval, and integrates with the midpoint heading. Nothing is filtered and
no timestamp enters the pose, so neither the firmware's velocity filter nor
USB jitter can bias it. NarrowAisleBot integrated filtered 20 Hz velocity
against Pi arrival time; this is the improvement its own firmware inventory
asked for (section 16, item 4).

Without angles (basic <L1> telemetry) it falls back to velocity x dt.

lateral_scale and track_width_scale are read on every message, so
    ros2 param set /wheel_odometry lateral_scale 0.92
takes effect immediately, without a restart that would lose the pose.

Re-zero ORDER matters once mapping runs: slam_toolbox fixes map -> odom at
its first scan, so zero odometry BEFORE starting a map, never during one.
The dashboard refuses /odom/reset while mapping or navigation is running.
"""

import math

import rclpy
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Empty
from tf2_ros import TransformBroadcaster

from robot_base.kinematics import OdometryIntegrator, model_from_params


class WheelOdometry(Node):

    def __init__(self):
        super().__init__("wheel_odometry")
        p = self.declare_parameter
        p("drive_type", "differential")
        p("wheel_radius", 0.05)
        p("wheel_names", ["left", "right"])
        p("wheel_x", [0.0, 0.0])
        p("wheel_y", [0.15, -0.15])
        p("wheel_ax", [1.0, 1.0])
        p("wheel_ay", [0.0, 0.0])
        p("track_width_scale", 1.0)
        p("lateral_scale", 1.0)
        p("odom_frame", "odom")
        p("base_frame", "base_link")
        p("publish_tf", True)
        p("max_wheel_jump", 50.0)    # rad between two messages: anything bigger is a reset
        self.names = list(self.get_parameter("wheel_names").value)
        self.odom_frame = self.get_parameter("odom_frame").value
        self.base_frame = self.get_parameter("base_frame").value
        self.publish_tf = bool(self.get_parameter("publish_tf").value)
        self._scales = None
        self.model = None
        self._rebuild()

        self.odo = OdometryIntegrator()
        self.prev_pos = None
        self.prev_t = None
        self.pub = self.create_publisher(Odometry, "odom", 20)
        self.tf = TransformBroadcaster(self) if self.publish_tf else None
        self.create_subscription(JointState, "wheel_states", self._on_states, 20)
        self.create_subscription(Empty, "odom/reset", self._on_reset, 10)
        self.get_logger().info(f"wheel_odometry: {self.get_parameter('drive_type').value}, "
                               f"wheels {self.names}")

    def _rebuild(self):
        g = lambda k: self.get_parameter(k).value  # noqa: E731
        scales = (float(g("track_width_scale")), float(g("lateral_scale")))
        if scales == self._scales:
            return
        self._scales = scales
        self.model = model_from_params(self.names, list(g("wheel_x")), list(g("wheel_y")),
                                       list(g("wheel_ax")), list(g("wheel_ay")),
                                       float(g("wheel_radius")), g("drive_type"), *scales)
        self.get_logger().info(f"scales: track_width {scales[0]}, lateral {scales[1]}")

    def _on_reset(self, _msg):
        self.odo.reset()
        self.prev_pos = None
        self.get_logger().info("odometry re-zeroed: this spot is now odom (0, 0, 0)")

    def _on_states(self, msg):
        if list(msg.name) != self.names:
            self.get_logger().warn(f"/wheel_states names {list(msg.name)} != {self.names}",
                                   throttle_duration_sec=10.0)
            return
        self._rebuild()
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        vx, vy, wz = self.model.forward(list(msg.velocity))

        if msg.position:
            pos = list(msg.position)
            if self.prev_pos is not None:
                dphi = [a - b for a, b in zip(pos, self.prev_pos)]
                lim = float(self.get_parameter("max_wheel_jump").value)
                if all(abs(d) < lim for d in dphi):
                    self.odo.step(*self.model.forward(dphi))
                else:
                    self.get_logger().warn("wheel angle jumped (MCU reset or <R>?); "
                                           "skipping one step")
            self.prev_pos = pos
        elif self.prev_t is not None:
            dt = t - self.prev_t
            if 0.0 < dt < 0.5:
                self.odo.step(vx * dt, vy * dt, wz * dt)
        self.prev_t = t

        x, y, th = self.odo.x, self.odo.y, self.odo.theta
        qz, qw = math.sin(th / 2.0), math.cos(th / 2.0)
        od = Odometry()
        od.header.stamp = msg.header.stamp
        od.header.frame_id = self.odom_frame
        od.child_frame_id = self.base_frame
        od.pose.pose.position.x = x
        od.pose.pose.position.y = y
        od.pose.pose.orientation.z = qz
        od.pose.pose.orientation.w = qw
        od.twist.twist.linear.x = vx
        od.twist.twist.linear.y = vy
        od.twist.twist.angular.z = wz
        # Fixed covariances. Nothing in this stack fuses them yet; an EKF
        # (robot_localization) would, and they should then be measured.
        for k, v in ((0, 0.01), (7, 0.01 if self.model.holonomic else 1e-3), (35, 0.03)):
            od.pose.covariance[k] = v
            od.twist.covariance[k] = v
        self.pub.publish(od)

        if self.tf:
            tf = TransformStamped()
            tf.header = od.header
            tf.child_frame_id = self.base_frame
            tf.transform.translation.x = x
            tf.transform.translation.y = y
            tf.transform.rotation.z = qz
            tf.transform.rotation.w = qw
            self.tf.sendTransform(tf)


def main(args=None):
    rclpy.init(args=args)
    node = WheelOdometry()
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
