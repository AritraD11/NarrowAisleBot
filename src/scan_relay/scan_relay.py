#!/usr/bin/env python3
"""
scan_relay.py — QoS bridge from best-effort /scan to reliable /scan_reliable.

RECONSTRUCTED FROM DOCUMENTATION (docs/LiDAR_SLAM_Bringup.md), not pulled
from the live copy at ~/ros2_ws/src/scan_relay/scan_relay.py on the Pi —
verify against that file and replace this one if they differ.

Why this exists: ydlidar_ros2_driver publishes /scan as best-effort. Both
rf2o and slam_toolbox subscribe as reliable by default, so they never
connect even though /scan is clearly alive (ros2 topic echo/hz work fine
because those tools negotiate compatible QoS). This node re-publishes the
same scan on /scan_reliable with reliable QoS so downstream reliable
subscribers can see it. rf2o has since been dropped from the stack; slam_toolbox
still needs this relay.

Run directly, no colcon build needed:
    source ~/ros2_ws/install/setup.bash
    python3 ~/ros2_ws/src/scan_relay/scan_relay.py
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan


class ScanRelay(Node):
    def __init__(self):
        super().__init__('scan_relay')

        best_effort = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )
        reliable = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )

        self._pub = self.create_publisher(LaserScan, '/scan_reliable', reliable)
        self.create_subscription(LaserScan, '/scan', self._on_scan, best_effort)

        self._forwarded = False

    def _on_scan(self, msg: LaserScan):
        self._pub.publish(msg)
        if not self._forwarded:
            self._forwarded = True
            self.get_logger().info(
                'Forwarding /scan (best-effort) -> /scan_reliable (reliable)'
            )


def main(args=None):
    rclpy.init(args=args)
    node = ScanRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
