#!/usr/bin/env python3
"""
scan_relay.py — /scan (best-effort) -> /scan_reliable (reliable), with an
optional angular correction applied on the way through.

TWO JOBS
--------

1. QoS BRIDGE (original purpose, Research_Journal.md 13.4).
   The ydlidar driver publishes /scan BEST_EFFORT; slam_toolbox and
   nav2_costmap_2d subscribe RELIABLE by default. Those endpoints never
   connect, and the symptom is a node that waits forever on a topic that
   `ros2 topic hz` says is perfectly alive.

2. ANGULAR CORRECTION (added 11 Aug 2026, section 17.9).
   Measured on hardware by placing a single block at known bearings and
   reading where it appeared:

       block truly at FRONT (   0 deg)  ->  reported  180 deg   WRONG
       block truly at RIGHT ( -90 deg)  ->  reported  -90 deg   correct
       block truly at LEFT  ( +90 deg)  ->  reported  +90 deg   correct

   Left/right correct, front/back swapped. That is a REFLECTION about the
   robot's Y axis, i.e.

       reported = 180 deg - true

   not a rotation. A rotation by 180 deg would have swapped left and right
   as well, and it demonstrably did not.

   This distinction decides where the fix can live: **a TF cannot express a
   reflection.** tf2 carries proper rigid motions (rotation + translation)
   only, so no base_link -> laser_frame transform, at any yaw, can undo
   this. The scan data itself has to be re-indexed -- which is why the fix
   is here, in the one node that already touches every scan.

   The correction is an involution (applying `reported = 180 - true` twice
   returns the original), so the same expression that describes the fault
   also repairs it.

PARAMETERS
----------
   mirror         (bool,   default True)   negate the scan angle
   yaw_offset_deg (double, default 180.0)  rotation applied after the mirror

   Physical angle recovered as:  true = mirror_sign * reported + yaw_offset

   Set `mirror:=false yaw_offset_deg:=0.0` for a pass-through relay, which
   reproduces this file's original behaviour exactly.

   These are parameters rather than hard-coded constants because the values
   describe THIS mounting of THIS sensor. Re-mount the LiDAR and they must
   be re-measured (tools/scan_bearing.py), not assumed to carry over.

Run directly -- it is a plain script, no colcon build needed:

    python3 scan_relay.py
    python3 scan_relay.py --ros-args -p mirror:=false -p yaw_offset_deg:=0.0
"""

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan


class ScanRelay(Node):

    def __init__(self):
        super().__init__('scan_relay')

        self.declare_parameter('mirror', True)
        self.declare_parameter('yaw_offset_deg', 180.0)
        self.mirror = self.get_parameter('mirror').value
        self.yaw_offset = math.radians(
            self.get_parameter('yaw_offset_deg').value)

        be = QoSProfile(depth=10,
                        reliability=ReliabilityPolicy.BEST_EFFORT,
                        history=HistoryPolicy.KEEP_LAST)
        rel = QoSProfile(depth=10,
                         reliability=ReliabilityPolicy.RELIABLE,
                         history=HistoryPolicy.KEEP_LAST)
        self.pub = self.create_publisher(LaserScan, '/scan_reliable', rel)
        self.sub = self.create_subscription(LaserScan, '/scan', self.cb, be)

        # Index map is rebuilt only when the scan's geometry changes, so the
        # per-message cost is a list comprehension, not trigonometry.
        self._map = None
        self._map_key = None

        self.get_logger().info(
            'scan_relay up: /scan (best_effort) -> /scan_reliable (reliable); '
            f'mirror={self.mirror}, yaw_offset='
            f'{math.degrees(self.yaw_offset):.1f} deg')
        if not self.mirror and abs(self.yaw_offset) < 1e-9:
            self.get_logger().info('  (pass-through: no angular correction)')

    def _build_map(self, msg):
        """Output bin j takes its reading from input bin _map[j].

        Output bin j is meant to represent physical angle
            theta_out = angle_min + j * angle_increment
        The reading that actually corresponds to that direction sits at the
        reported angle theta_in satisfying
            theta_out = sign * theta_in + yaw_offset
        so
            theta_in = (theta_out - yaw_offset) / sign

        The modulo wrap below assumes the scan spans a full revolution, which
        holds for the X4 Pro (360 deg). On a partial-arc sensor the wrap would
        fold one end of the arc onto the other, so this would need bounds
        checks and an out-of-arc fill instead.
        """
        n = len(msg.ranges)
        if n == 0 or msg.angle_increment == 0.0:
            return None
        sign = -1.0 if self.mirror else 1.0
        idx = []
        for j in range(n):
            theta_out = msg.angle_min + j * msg.angle_increment
            theta_in = (theta_out - self.yaw_offset) / sign
            i = int(round((theta_in - msg.angle_min) / msg.angle_increment))
            idx.append(i % n)
        return idx

    def cb(self, msg):
        if not self.mirror and abs(self.yaw_offset) < 1e-9:
            self.pub.publish(msg)
            return

        key = (len(msg.ranges), msg.angle_min, msg.angle_increment)
        if key != self._map_key:
            self._map = self._build_map(msg)
            self._map_key = key
            if self._map is not None:
                self.get_logger().info(
                    f'angle correction map rebuilt for {len(msg.ranges)} beams')

        if self._map is None:
            self.pub.publish(msg)
            return

        out = LaserScan()
        out.header = msg.header
        out.angle_min = msg.angle_min
        out.angle_max = msg.angle_max
        out.angle_increment = msg.angle_increment
        out.time_increment = msg.time_increment
        out.scan_time = msg.scan_time
        out.range_min = msg.range_min
        out.range_max = msg.range_max
        out.ranges = [msg.ranges[i] for i in self._map]
        if msg.intensities:
            out.intensities = [msg.intensities[i] for i in self._map]
        self.pub.publish(out)


def main():
    rclpy.init()
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
