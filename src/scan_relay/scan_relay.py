#!/usr/bin/env python3
"""
scan_relay.py — /scan (best-effort) -> /scan_reliable (reliable), with an
optional angular correction applied on the way through.

THREE JOBS
----------

1. QoS BRIDGE (original purpose, Research_Journal.md 13.4).
   The ydlidar driver publishes /scan BEST_EFFORT; slam_toolbox and
   nav2_costmap_2d subscribe RELIABLE by default. Those endpoints never
   connect, and the symptom is a node that waits forever on a topic that
   `ros2 topic hz` says is perfectly alive.

2. ANGULAR CORRECTION (added 11 Aug 2026, section 17.9).
   Measured on hardware by placing a single block at known bearings *in
   base_link's own frame as this robot actually drives it* -- confirmed
   empirically (W -> +Y, D -> +X, both against Foxglove's Fixed/Display
   frame set to base_link), not assumed from the REP-103 textbook
   convention (which would put forward on +X). Whatever base_link's real
   axes are is what this scan has to line up with, so that is what was
   measured against:

       block truly RIGHT (base_link +X,   0 deg) -> reported  270 deg
       block truly FRONT (base_link +Y,  90 deg) -> reported  180 deg
       block truly LEFT  (base_link -X, 180 deg) -> reported   90 deg

   All three solve the same relationship: reported = 270 deg - true. That
   is a REFLECTION (a rotation would add the same signed delta at every
   heading; here the delta is 270, 90, 270 -- not constant -- while
   reported + true IS constant at every heading, which is what a mirror
   about a fixed line produces, not a turn).

   An earlier pass at this fix assumed base_link's forward was +X
   (REP-103) and derived yaw_offset=180 deg. That number is 90 deg off
   from every one of the three measurements above and was never deployed
   -- flagged here because it is the mistake to not repeat if this is ever
   re-derived: measure against how the robot actually drives, not against
   the textbook axis convention.

   This distinction decides where the fix can live: **a TF cannot express a
   reflection.** tf2 carries proper rigid motions (rotation + translation)
   only, so no base_link -> laser_frame transform, at any yaw, can undo
   this. The scan data itself has to be re-indexed -- which is why the fix
   is here, in the one node that already touches every scan.

   The correction is an involution (applying `reported = 180 - true` twice
   returns the original), so the same expression that describes the fault
   also repairs it.

3. SELF-OCCLUSION MASK (added 13 Aug 2026, section 17.15).
   The robot's own rear mast sits inside the LiDAR's field of view and
   BEYOND its 0.10 m minimum range, so it returns a valid, in-band hit on
   every single scan -- a phantom obstacle fixed in the robot's own frame
   rather than in the room. Navigation_Theory.md section 4 predicted this
   failure mode before Nav2 was ever run; these are the measurements that
   confirmed it.

   Measured with tools/scan_bearing.py at five headings around a full 360
   deg rotation (0/90/180/270/360). The discriminator is that real features
   sweep through the laser frame as the robot turns while self-occlusion
   does not, and the result is about as unambiguous as this kind of
   measurement gets -- nearest return per sector, across all five headings:

       sector        run1  run2  run3  run4  run5   spread
       -135..-120    0.13  0.12  0.13  0.12  0.13   0.01 m
       -120..-105    0.13  0.14  0.13  0.13  0.13   0.01 m
       -105.. -90    0.13  0.13  0.13  0.13  0.13   0.00 m
        -90.. -75    0.24  0.24  0.24  0.24  0.24   0.00 m
        -75.. -60    0.14  0.14  0.14  0.14  0.14   0.00 m
        -60.. -45    0.16  0.16  0.16  0.16  0.16   0.00 m

   A full revolution of the robot moved those distances by at most one
   centimetre. For scale, a genuinely room-dependent sector (+180..-165)
   ranged over 3.86 m across the same five headings. Second signature:
   in every masked sector hits% == close% exactly -- every beam that
   returns anything returns something under 1 m, i.e. nothing gets past.

   -90 deg is dead astern in this robot's frame (+X right, +Y forward, so
   -Y rear), which matches the physical rear stack exactly.

   THE SECTOR IS 90 DEG, NOT THE ~120 DEG ("about a third of the sweep")
   recorded in section 17.8. That earlier figure was measured in the
   pre-mirror-fix frame and was an estimate from block placement; this is a
   direct numeric measurement in the corrected frame. 90 deg -- a quarter --
   supersedes it.

   Masked beams are set to NaN, not to zero and not to inf, and the
   distinction matters:
     - a finite value would MARK a phantom obstacle (the bug)
     - inf reads as "nothing out to max range" and would CLEAR through
       whatever is really back there, which is worse than the bug
     - NaN is dropped by laser_geometry's projection, so the beam
       contributes nothing at all: it neither marks nor clears, which is
       the honest representation of "this sensor cannot see here."

   Nothing real is lost. Every valid return inside the arc was the mast
   itself (that is what hits% == close% means); beams that clear the mast
   simply never come back. The arc contained no room data to discard.

PARAMETERS
----------
   mirror         (bool,   default True)   negate the scan angle
   yaw_offset_deg (double, default 270.0)  rotation applied after the mirror
   mask_enabled   (bool,   default True)   blank the self-occluded arc
   mask_min_deg   (double, default -135.0) arc start, OUTPUT frame
   mask_max_deg   (double, default  -45.0) arc end, OUTPUT frame

   Physical angle recovered as:  true = mirror_sign * reported + yaw_offset

   Mask bounds are in the CORRECTED (published) frame -- the same frame
   tools/scan_bearing.py reports against when reading /scan_reliable, so a
   re-measurement can be typed straight in without re-deriving anything.
   The arc runs counter-clockwise from mask_min_deg to mask_max_deg and may
   wrap through +/-180.

   Set `mirror:=false yaw_offset_deg:=0.0 mask_enabled:=false` for a
   pass-through relay, which reproduces this file's original behaviour
   exactly.

   These are parameters rather than hard-coded constants because the values
   describe THIS mounting of THIS sensor on THIS chassis. Re-mount the
   LiDAR, or change what is bolted to the frame around it, and they must be
   re-measured (tools/scan_bearing.py), not assumed to carry over.

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
        self.declare_parameter('yaw_offset_deg', 270.0)
        self.declare_parameter('mask_enabled', True)
        self.declare_parameter('mask_min_deg', -135.0)
        self.declare_parameter('mask_max_deg', -45.0)
        self.mirror = self.get_parameter('mirror').value
        self.yaw_offset = math.radians(
            self.get_parameter('yaw_offset_deg').value)
        self.mask_enabled = self.get_parameter('mask_enabled').value
        self.mask_min_deg = self.get_parameter('mask_min_deg').value
        self.mask_max_deg = self.get_parameter('mask_max_deg').value

        self._corrects_angle = self.mirror or abs(self.yaw_offset) > 1e-9
        self._passthrough = not self._corrects_angle and not self.mask_enabled

        be = QoSProfile(depth=10,
                        reliability=ReliabilityPolicy.BEST_EFFORT,
                        history=HistoryPolicy.KEEP_LAST)
        rel = QoSProfile(depth=10,
                         reliability=ReliabilityPolicy.RELIABLE,
                         history=HistoryPolicy.KEEP_LAST)
        self.pub = self.create_publisher(LaserScan, '/scan_reliable', rel)
        self.sub = self.create_subscription(LaserScan, '/scan', self.cb, be)

        # Index map and mask are rebuilt only when the scan's geometry
        # changes, so the per-message cost is a list comprehension, not
        # trigonometry.
        self._map = None
        self._mask = None
        self._map_key = None

        self.get_logger().info(
            'scan_relay up: /scan (best_effort) -> /scan_reliable (reliable); '
            f'mirror={self.mirror}, yaw_offset='
            f'{math.degrees(self.yaw_offset):.1f} deg')
        if self.mask_enabled:
            self.get_logger().info(
                f'  self-occlusion mask ON: {self.mask_min_deg:.1f} to '
                f'{self.mask_max_deg:.1f} deg blanked to NaN (rear mast, '
                'section 17.15)')
        else:
            self.get_logger().warn(
                '  self-occlusion mask OFF -- the rear mast will read as a '
                'phantom obstacle ~0.13 m behind the robot')
        if self._passthrough:
            self.get_logger().info('  (pass-through: no correction, no mask)')

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
        if not self._corrects_angle:
            return list(range(n))       # identity: mask-only configuration
        sign = -1.0 if self.mirror else 1.0
        idx = []
        for j in range(n):
            theta_out = msg.angle_min + j * msg.angle_increment
            theta_in = (theta_out - self.yaw_offset) / sign
            i = int(round((theta_in - msg.angle_min) / msg.angle_increment))
            idx.append(i % n)
        return idx

    def _build_mask(self, msg):
        """Which OUTPUT bins fall inside the self-occluded arc.

        Bounds are in the corrected/published frame, so this is applied
        after the index remap, against each output bin's own angle.

        The arc runs counter-clockwise from mask_min_deg to mask_max_deg.
        Testing `(a - lo) mod 360 <= (hi - lo) mod 360` rather than a plain
        `lo <= a <= hi` keeps that correct when the arc wraps through
        +/-180 -- not the case for the measured rear sector, but a
        re-measured mount could straddle the wrap and this should not
        silently invert if it does.
        """
        n = len(msg.ranges)
        if n == 0 or msg.angle_increment == 0.0:
            return None
        span = (self.mask_max_deg - self.mask_min_deg) % 360.0
        flags = []
        for j in range(n):
            deg = math.degrees(msg.angle_min + j * msg.angle_increment)
            flags.append(((deg - self.mask_min_deg) % 360.0) <= span)
        return flags

    def cb(self, msg):
        if self._passthrough:
            self.pub.publish(msg)
            return

        key = (len(msg.ranges), msg.angle_min, msg.angle_increment)
        if key != self._map_key:
            self._map = self._build_map(msg)
            self._mask = self._build_mask(msg) if self.mask_enabled else None
            self._map_key = key
            if self._map is not None:
                blanked = sum(self._mask) if self._mask else 0
                self.get_logger().info(
                    f'angle correction map rebuilt for {len(msg.ranges)} '
                    f'beams; {blanked} masked as self-occluded')

        if self._map is None:
            self.pub.publish(msg)
            return

        ranges = [msg.ranges[i] for i in self._map]
        if self._mask is not None:
            nan = float('nan')
            ranges = [nan if m else r for r, m in zip(ranges, self._mask)]

        out = LaserScan()
        out.header = msg.header
        out.angle_min = msg.angle_min
        out.angle_max = msg.angle_max
        out.angle_increment = msg.angle_increment
        out.time_increment = msg.time_increment
        out.scan_time = msg.scan_time
        out.range_min = msg.range_min
        out.range_max = msg.range_max
        out.ranges = ranges
        if msg.intensities:
            # Intensities are remapped but deliberately NOT masked: a NaN
            # range already invalidates the beam everywhere it matters, and
            # leaving intensity intact keeps the two arrays the same length
            # and the raw signal inspectable if the mask is ever re-examined.
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
