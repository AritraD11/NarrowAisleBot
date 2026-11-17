"""
scan_math.py - the LaserScan arithmetic behind scan_filter.py. No ROS.

Two corrections, both learnt the hard way on NarrowAisleBot:

mirror
    Some scanners report bearings in the opposite rotational sense to
    REP-103 (counter-clockwise positive). TF cannot express a reflection, so
    no URDF rotation fixes it: the array has to be reversed. Reversing it
    and swapping the angle limits (new min = -old max, new max = -old min)
    puts every beam at exactly the negated angle, symmetric limits or not.

mask
    Arcs where the laser sees the robot's own body (a mast, a bracket, a
    cable) are set to NaN. NaN, not 0 and not inf: 0 would mark an obstacle
    on top of the sensor, inf would CLEAR the costmap along that ray; NaN is
    "no information" to both slam_toolbox and the costmaps.
"""

import math


def in_arc(theta_deg, a_deg, b_deg):
    """True if theta lies on the counter-clockwise arc from a to b
    (inclusive). Works across +/-180: in_arc(170, 135, 225) is True."""
    span = (b_deg - a_deg) % 360.0
    d = (theta_deg - a_deg) % 360.0
    return d <= span + 1e-9


def mirror(ranges, intensities, angle_min, angle_max):
    """Reverse the beam order. Returns (ranges, intensities, new_min, new_max)."""
    r = list(reversed(ranges))
    i = list(reversed(intensities)) if intensities else intensities
    return r, i, -angle_max, -angle_min


def apply_mask(ranges, angle_min, angle_increment, arcs_deg):
    """Set every beam whose angle falls in any [from, to] arc (degrees,
    laser frame) to NaN. Returns (ranges, number masked)."""
    out = list(ranges)
    n = 0
    if not arcs_deg:
        return out, 0
    for k in range(len(out)):
        th = math.degrees(angle_min + k * angle_increment)
        for a, b in arcs_deg:
            if in_arc(th, a, b):
                out[k] = float("nan")
                n += 1
                break
    return out, n


def pairs(flat):
    """[a0, b0, a1, b1, ...] -> [(a0, b0), (a1, b1), ...]"""
    if len(flat) % 2:
        raise ValueError("mask_deg needs an even number of values (pairs of from, to)")
    return [(float(flat[k]), float(flat[k + 1])) for k in range(0, len(flat), 2)]


def scan_to_points(ranges, angle_min, angle_increment, range_min, range_max, step=1):
    """(x, y) in the laser frame for every valid beam, every `step`th beam."""
    pts = []
    for k in range(0, len(ranges), step):
        r = ranges[k]
        if r is None or not (range_min <= r <= range_max) or math.isnan(r):
            continue
        a = angle_min + k * angle_increment
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts
