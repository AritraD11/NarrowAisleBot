#!/usr/bin/env python3
"""
scan_filter - /scan (driver, best effort) -> /scan_filtered (reliable).

Three jobs, all in scan_math.py:

  1. QoS. LiDAR drivers publish BEST_EFFORT. slam_toolbox and the Nav2
     costmaps subscribe RELIABLE, and a reliable subscriber never connects
     to a best-effort publisher: no error, just no data. Republishing as
     reliable is the whole reason NarrowAisleBot's scan_relay first existed.
  2. mirror (parameter), for a scanner that reports bearings backwards.
  3. mask_deg, arcs blanked to NaN where the laser sees the robot itself.

Everything downstream (SLAM, both costmaps, the collision monitor, the
dashboard) reads /scan_filtered, never /scan. If you add a consumer, point
it here too. (NarrowAisleBot's AMCL block was left on /scan by default and
would have read the raw, mirrored scan the day it first ran.)
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

from robot_base import scan_math


class ScanFilter(Node):

    def __init__(self):
        super().__init__("scan_filter")
        self.declare_parameter("input_topic", "scan")
        self.declare_parameter("output_topic", "scan_filtered")
        self.declare_parameter("mirror", False)
        self.declare_parameter("mask_enabled", False)
        self.declare_parameter("mask_deg", [0.0, 0.0])
        self.declare_parameter("range_min", 0.1)
        self.declare_parameter("range_max", 10.0)
        self.mirror = bool(self.get_parameter("mirror").value)
        self.arcs = scan_math.pairs(list(self.get_parameter("mask_deg").value)) \
            if self.get_parameter("mask_enabled").value else []
        self.rmin = float(self.get_parameter("range_min").value)
        self.rmax = float(self.get_parameter("range_max").value)
        out_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                             history=HistoryPolicy.KEEP_LAST)
        self.pub = self.create_publisher(LaserScan, self.get_parameter("output_topic").value, out_qos)
        self.create_subscription(LaserScan, self.get_parameter("input_topic").value,
                                 self._on_scan, qos_profile_sensor_data)
        self.masked = 0
        self.get_logger().info(f"scan_filter: mirror={self.mirror} mask={self.arcs} "
                               f"range {self.rmin}..{self.rmax} m")

    def _on_scan(self, msg):
        ranges, inten = list(msg.ranges), list(msg.intensities)
        amin, amax = msg.angle_min, msg.angle_max
        if self.mirror:
            ranges, inten, amin, amax = scan_math.mirror(ranges, inten, amin, amax)
        ranges, self.masked = scan_math.apply_mask(ranges, amin, msg.angle_increment, self.arcs)
        out = LaserScan()
        out.header = msg.header
        out.angle_min = amin
        out.angle_max = amax
        out.angle_increment = msg.angle_increment
        out.time_increment = msg.time_increment
        out.scan_time = msg.scan_time
        out.range_min = max(msg.range_min, self.rmin)
        out.range_max = min(msg.range_max, self.rmax) if msg.range_max > 0 else self.rmax
        out.ranges = ranges
        out.intensities = inten
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = ScanFilter()
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
