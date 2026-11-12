#!/usr/bin/env python3
"""
telemetry_logger - write /mcu/telemetry to CSV while the robot runs under ROS.

The encoder logger (tools/encoder_logger.py) needs the serial port to
itself, so it cannot log while ROS drives. This node can: it records what
mcu_bridge already publishes, in the same CSV format, so analyze_log.py reads
either.

    ros2 run robot_base telemetry_logger                      # until Ctrl-C
    ros2 run robot_base telemetry_logger --ros-args -p duration:=60.0

The dashboard's REC button does the same thing from the phone.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

from robot_base.telemetry_csv import TelemetryCsv


class TelemetryLogger(Node):
    def __init__(self):
        super().__init__("telemetry_logger")
        self.declare_parameter("wheel_names", ["left", "right"])
        self.declare_parameter("log_dir", "~/robot_logs")
        self.declare_parameter("duration", 0.0)
        names = list(self.get_parameter("wheel_names").value)
        self.csv = TelemetryCsv(self.get_parameter("log_dir").value, names)
        self.t0 = self.get_clock().now()
        self.duration = float(self.get_parameter("duration").value)
        self.create_subscription(Float64MultiArray, "mcu/telemetry", self._on, 50)
        self.get_logger().info(f"logging /mcu/telemetry to {self.csv.path}")

    def _on(self, msg):
        now = self.get_clock().now()
        self.csv.add(now.nanoseconds * 1e-9, msg.data)
        if self.duration > 0 and (now - self.t0).nanoseconds * 1e-9 > self.duration:
            raise KeyboardInterrupt


def main(args=None):
    rclpy.init(args=args)
    node = TelemetryLogger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        path = node.csv.close()
        print(f"{node.csv.rows} rows -> {path}")
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
