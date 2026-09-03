#!/usr/bin/env python3
"""
map_watch.py -- one line per second: is the map growing, and where is the
robot? Run it in a spare terminal alongside a mapping or calibration run.

WHY THIS EXISTS
    The 15 Aug 2026 first hardware run of zero_point_scan.py reported
    "no growth from rotation" six times in a row and there was no way to
    tell, from any log on the system, WHICH of these was happening:

        - the map was completely static (nothing being processed)
        - the map was growing, but by fewer cells than the threshold
        - /map was never arriving at all
        - the map was growing but the ROBOT's pose estimate was drifting,
          so the growth was landing in the wrong place

    Those are four different bugs with four different fixes, and the run
    took 90 seconds to produce a single word of evidence ("skipped").
    A Foxglove screenshot cannot distinguish them either -- it shows the
    end state, not the trajectory of either quantity.

    The root cause turned out to be the first one, and one number would
    have shown it instantly: known-cell count, flat across the entire run.

WHAT EACH COLUMN MEANS
    t         seconds since this watcher started
    cells     count of /map cells that are not -1 (unknown), i.e. how much
              of the world SLAM has actually committed to the map
    d_cells   change since the previous line. THIS is the number that says
              whether a nudge did anything. Flat zero across a move means
              slam_toolbox is not processing the scan at all -- check the
              move against minimum_travel_distance in slam_nodom.yaml.
    map_x/y   robot position in the map frame (metres)
    yaw       robot heading in the map frame (deg). -90 = parked square on
              the zero mark, per this robot's axis convention (sec 17.10).
    d_moved   distance travelled since the previous line, from TF. Compare
              against d_cells: movement with no cell change is the exact
              signature of the nudge-below-threshold bug.
    home      distance from map (0,0), i.e. from the zero mark -- but only
              as good as SLAM's own correction. If d_cells is flat, no
              scans are being processed, map->odom is frozen, and this
              number is raw wheel odometry with all its drift.

Usage:
    python3 map_watch.py                 # print until Ctrl-C
    python3 map_watch.py --interval 0.5  # finer
    python3 map_watch.py --csv ~/aislebot_logs/watch.csv   # also to file
"""

import argparse
import math
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
from tf2_ros import Buffer, TransformListener, TransformException
from nav_msgs.msg import OccupancyGrid


def yaw_from_quat(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class MapWatch(Node):

    def __init__(self, args):
        super().__init__('map_watch')
        self.args = args

        self.tf_buffer = Buffer()
        TransformListener(self.tf_buffer, self)

        # Must match how slam_toolbox publishes /map or nothing arrives and
        # this tool silently reports nothing -- the same QoS trap that made
        # slam_toolbox itself hang on "Waiting for laser_scans" (sec 13.4).
        self.create_subscription(
            OccupancyGrid, '/map', self._map_cb,
            QoSProfile(depth=1,
                       durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
                       reliability=QoSReliabilityPolicy.RELIABLE))

        self.latest_map = None
        self.csv = open(args.csv, 'w') if args.csv else None

    def _map_cb(self, msg):
        self.latest_map = msg

    def known_cells(self):
        if self.latest_map is None:
            return None
        return sum(1 for c in self.latest_map.data if c != -1)

    def pose(self):
        try:
            tf = self.tf_buffer.lookup_transform('map', 'base_link', Time())
            t = tf.transform.translation
            return t.x, t.y, math.degrees(yaw_from_quat(tf.transform.rotation))
        except TransformException:
            return None

    def run(self):
        header = ('    t   cells  d_cells    map_x    map_y      yaw  '
                  'd_moved     home')
        print(header)
        print('-' * len(header))
        if self.csv:
            self.csv.write('t,cells,d_cells,map_x,map_y,yaw,d_moved,home\n')

        t0 = time.monotonic()
        prev_cells, prev_xy = None, None

        while rclpy.ok():
            deadline = time.monotonic() + self.args.interval
            while rclpy.ok() and time.monotonic() < deadline:
                rclpy.spin_once(self, timeout_sec=0.05)

            t = time.monotonic() - t0
            cells = self.known_cells()
            p = self.pose()

            d_cells = '' if (cells is None or prev_cells is None) \
                else '{:+d}'.format(cells - prev_cells)

            if p is None:
                line = '{:5.1f}  {:>6}  {:>7}   (no map->base_link TF yet)'.format(
                    t, '-' if cells is None else cells, d_cells)
                xs = ys = yaws = moved = home = None
            else:
                x, y, yaw = p
                moved = 0.0 if prev_xy is None else math.hypot(
                    x - prev_xy[0], y - prev_xy[1])
                home = math.hypot(x, y)
                line = ('{:5.1f}  {:>6}  {:>7}  {:7.3f}  {:7.3f}  {:7.1f}  '
                        '{:7.3f}  {:7.3f}').format(
                            t, '-' if cells is None else cells, d_cells,
                            x, y, yaw, moved, home)
                xs, ys, yaws = x, y, yaw
                prev_xy = (x, y)

            print(line, flush=True)
            if self.csv:
                self.csv.write('{:.2f},{},{},{},{},{},{},{}\n'.format(
                    t, cells if cells is not None else '', d_cells,
                    '' if xs is None else '{:.4f}'.format(xs),
                    '' if ys is None else '{:.4f}'.format(ys),
                    '' if yaws is None else '{:.2f}'.format(yaws),
                    '' if moved is None else '{:.4f}'.format(moved),
                    '' if home is None else '{:.4f}'.format(home)))
                self.csv.flush()

            if cells is not None:
                prev_cells = cells

    def close(self):
        if self.csv:
            self.csv.close()


def main():
    parser = argparse.ArgumentParser(
        description='Live one-line-per-second view of map growth and robot '
                    'pose, for watching a mapping or calibration run.')
    parser.add_argument('--interval', type=float, default=1.0,
                        help='seconds between lines. Default 1.0.')
    parser.add_argument('--csv', default=None,
                        help='also append each line to this CSV file.')
    args = parser.parse_args()

    rclpy.init()
    node = MapWatch(args)
    try:
        node.run()
    except KeyboardInterrupt:
        print('\nstopped', file=sys.stderr)
    finally:
        node.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
