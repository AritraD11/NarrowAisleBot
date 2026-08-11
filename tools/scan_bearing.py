#!/usr/bin/env python3
"""
scan_bearing.py — answer two questions about /scan_reliable numerically,
instead of by squinting at a visualiser.

  1. WHERE DOES THE LIDAR THINK THE NEAREST THING IS?
     Put one distinctive object at a known bearing (e.g. directly ahead of
     the robot's physical front) with clear space around it, run this, and
     compare the reported bearing against where the object actually is.
     The difference is the LiDAR's mounting-yaw error — the number needed to
     correct the base_link -> laser_frame static transform.

     ROS convention (REP-103): 0 deg = +X = robot forward, +90 deg = +Y =
     robot LEFT, 180 deg = behind, -90 deg = right. Bearings increase
     counter-clockwise viewed from above.

  2. WHICH SECTORS ARE BLOCKED BY THE ROBOT ITSELF?
     Self-occlusion is fixed in the laser frame: it reads the same bearing
     no matter which way the robot is pointing, while real features sweep
     past as the robot rotates. Run this at several headings and compare the
     sector table — bins that stay short/invalid at every heading are the
     robot's own structure (Navigation_Theory.md section 4).

Usage (on the Pi, with the mapping stack running):

    python3 scan_bearing.py                  # one scan, default topic
    python3 scan_bearing.py --samples 20     # average over 20 scans (steadier)
    python3 scan_bearing.py --topic /scan    # a different topic
    python3 scan_bearing.py --max-range 2.0  # only consider returns within 2 m

Pure rclpy + stdlib. No numpy, matching the dependency-light convention the
rest of the on-Pi tooling follows (run_report.py, scan_relay.py).
"""

import argparse
import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan


SECTOR_COUNT = 24                      # 15-degree bins
BLOCKED_FRACTION = 0.6                 # bin counts as suspicious above this


def normalise_deg(deg):
    """Wrap to (-180, 180]."""
    while deg <= -180.0:
        deg += 360.0
    while deg > 180.0:
        deg -= 360.0
    return deg


class ScanBearing(Node):

    def __init__(self, topic, samples, max_range):
        super().__init__("scan_bearing")
        self.samples_wanted = samples
        self.max_range = max_range
        self.scans = []
        # /scan_reliable is published RELIABLE by scan_relay.py; /scan from the
        # driver is BEST_EFFORT. Subscribing BEST_EFFORT is compatible with
        # both (a reliable publisher can satisfy a best-effort subscriber, but
        # not the reverse) -- so this works on either topic without a flag.
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self.sub = self.create_subscription(LaserScan, topic, self._cb, qos)

    def _cb(self, msg):
        if len(self.scans) < self.samples_wanted:
            self.scans.append(msg)

    def done(self):
        return len(self.scans) >= self.samples_wanted


def valid_returns(scan, max_range):
    """Yield (bearing_deg, range_m) for finite in-band returns."""
    lo = scan.range_min
    hi = scan.range_max if max_range is None else min(scan.range_max, max_range)
    for i, r in enumerate(scan.ranges):
        if r is None or math.isnan(r) or math.isinf(r):
            continue
        if r < lo or r > hi:
            continue
        bearing = math.degrees(scan.angle_min + i * scan.angle_increment)
        yield normalise_deg(bearing), r


def report(scans, max_range):
    first = scans[0]

    print("=" * 68)
    print("SCAN GEOMETRY (as the driver reports it)")
    print("=" * 68)
    print(f"  frame_id        : {first.header.frame_id}")
    print(f"  beams per scan  : {len(first.ranges)}")
    print(f"  angle_min       : {math.degrees(first.angle_min):8.2f} deg")
    print(f"  angle_max       : {math.degrees(first.angle_max):8.2f} deg")
    print(f"  angle_increment : {math.degrees(first.angle_increment):8.4f} deg")
    print(f"  range_min/max   : {first.range_min:.3f} / {first.range_max:.3f} m")
    print(f"  scans averaged  : {len(scans)}")
    if max_range is not None:
        print(f"  --max-range     : {max_range:.2f} m (returns beyond ignored)")

    # ---- 1. nearest return, for mounting-yaw calibration -----------------
    nearest = None
    for scan in scans:
        for bearing, r in valid_returns(scan, max_range):
            if nearest is None or r < nearest[1]:
                nearest = (bearing, r)

    print()
    print("=" * 68)
    print("NEAREST RETURN  (point one known object at a known bearing)")
    print("=" * 68)
    if nearest is None:
        print("  No valid returns at all. Check the LiDAR is spinning and")
        print("  publishing, and that --max-range is not too small.")
    else:
        bearing, r = nearest
        print(f"  bearing : {bearing:+8.2f} deg")
        print(f"  range   : {r:8.3f} m")
        print()
        print("  Compare against where the object physically is:")
        print("    object ahead      -> expect    0 deg")
        print("    object to LEFT    -> expect  +90 deg")
        print("    object to RIGHT   -> expect  -90 deg")
        print("    object behind     -> expect  180 deg")
        print()
        print("  Any difference is the mounting-yaw error. Feed the CORRECTION")
        print("  (negative of the error, in radians) into the base_link ->")
        print("  laser_frame static transform's yaw.")

    # ---- 2. sector occupancy, for self-occlusion -------------------------
    width = 360.0 / SECTOR_COUNT
    hits = [0] * SECTOR_COUNT
    close = [0] * SECTOR_COUNT
    mins = [None] * SECTOR_COUNT
    beams = [0] * SECTOR_COUNT

    for scan in scans:
        for i, r in enumerate(scan.ranges):
            bearing = normalise_deg(
                math.degrees(scan.angle_min + i * scan.angle_increment))
            idx = int((bearing + 180.0) / width) % SECTOR_COUNT
            beams[idx] += 1
            if r is None or math.isnan(r) or math.isinf(r):
                continue
            if r < scan.range_min or r > scan.range_max:
                continue
            hits[idx] += 1
            if mins[idx] is None or r < mins[idx]:
                mins[idx] = r
            if r < 1.0:
                close[idx] += 1

    print()
    print("=" * 68)
    print("SECTOR TABLE  (run at several headings; compare)")
    print("=" * 68)
    print("  Self-occlusion holds the SAME bearing at every heading.")
    print("  Real walls move between headings. That difference is the test.")
    print()
    print("   bearing range      hits   <1m    nearest   profile")
    print("   " + "-" * 60)
    for idx in range(SECTOR_COUNT):
        lo = normalise_deg(-180.0 + idx * width)
        hi = normalise_deg(lo + width)
        n = beams[idx]
        hit_frac = (hits[idx] / n) if n else 0.0
        close_frac = (close[idx] / n) if n else 0.0
        nearest_s = f"{mins[idx]:6.2f}m" if mins[idx] is not None else "     --"
        bar = "#" * int(round(close_frac * 20))
        flag = "  <== always close" if close_frac > BLOCKED_FRACTION else ""
        print(f"  {lo:+7.1f}..{hi:+7.1f}  {hit_frac:5.0%} {close_frac:5.0%}"
              f"  {nearest_s}   {bar}{flag}")

    print()
    print("  'hits'  = fraction of beams returning anything valid")
    print("  '<1m'   = fraction returning something closer than 1 m")
    print()
    print("  A sector that is BOTH consistently <1m AND unchanged across")
    print("  headings is the robot's own structure -> mask it in scan_relay.py.")
    print("  A sector with near-zero hits everywhere is pure shadow: nothing")
    print("  to mask, the beams simply never come back.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", default="/scan_reliable")
    ap.add_argument("--samples", type=int, default=10,
                    help="scans to accumulate before reporting (default 10)")
    ap.add_argument("--max-range", type=float, default=None,
                    help="ignore returns beyond this many metres")
    ap.add_argument("--timeout", type=float, default=15.0,
                    help="seconds to wait for scans (default 15)")
    args = ap.parse_args()

    rclpy.init()
    node = ScanBearing(args.topic, args.samples, args.max_range)

    print(f"Waiting for {args.samples} scan(s) on {args.topic} ...")
    start = node.get_clock().now()
    while rclpy.ok() and not node.done():
        rclpy.spin_once(node, timeout_sec=0.2)
        elapsed = (node.get_clock().now() - start).nanoseconds / 1e9
        if elapsed > args.timeout:
            break

    if not node.scans:
        print()
        print(f"No messages on {args.topic} within {args.timeout:.0f}s.")
        print("Is the mapping stack running? Check:  ros2 topic hz " + args.topic)
        node.destroy_node()
        rclpy.shutdown()
        return 1

    if not node.done():
        print(f"(timed out with {len(node.scans)} of {args.samples} scans "
              f"-- reporting on what arrived)")
    print()
    report(node.scans, args.max_range)

    node.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
