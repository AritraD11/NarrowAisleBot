#!/usr/bin/env python3
"""
sensor_coverage.py -- planar geometry behind docs/Year2_Autonomy_Research.md.

Three questions, all pure 2-D geometry, no ROS, no hardware:

  1. blind   Where is the X4 Pro actually blind once the rear mast wedge
             ([-135, -45] deg, scan_relay.py's mask) is applied? Not just
             "behind": the LiDAR sits 0.27 m forward of base_link, so the
             wedge also swallows the rear half of both flanks at aisle
             clearances.
  2. aisle   How much heading error can a 1.0 x 0.36 m rectangle tolerate
             inside an aisle of width A before a corner touches a wall?
  3. ring    What fraction of the robot's surroundings, at a stand-off d,
             does a given ToF-ring or rear-LiDAR layout actually see?

Frame: this robot's base_link, +X = RIGHT, +Y = FORWARD (docs/Axis_Convention.md).
Bearings are degrees CCW from +X, so 0 = right, +90 = forward, -90 = behind.

Every sensor is modelled as a 2-D cone (horizontal FoV only) and the chassis
as an opaque box at scan height. That is an upper bound on what a real sensor
sees: it ignores vertical FoV, floor returns, target reflectivity and the
mast's exact outline. Treat the output as a layout screen, not a CAD check.

Usage:
    python3 tools/sensor_coverage.py --selftest
    python3 tools/sensor_coverage.py blind
    python3 tools/sensor_coverage.py aisle
    python3 tools/sensor_coverage.py ring
    python3 tools/sensor_coverage.py all
"""

import argparse
import math
import sys

# ---- robot geometry (tape-measured, nav2_params.yaml footprint comment) -----
HALF_W = 0.18          # 36 cm wheel-outer to wheel-outer
HALF_L = 0.50          # 100 cm long
PAD = 0.06             # nav2 footprint margin -> 0.48 x 1.12 m
LIDAR = (0.0, 0.27)    # aislebot.urdf laser_joint, tape-measured 12 Aug 2026
MASK = (-135.0, -45.0) # scan_relay.py mask_min_deg / mask_max_deg


def wrap(deg):
    """Wrap an angle to (-180, 180]."""
    d = (deg + 180.0) % 360.0 - 180.0
    return 180.0 if d == -180.0 else d


def bearing(frm, to):
    return math.degrees(math.atan2(to[1] - frm[1], to[0] - frm[0]))


def in_arc(b, lo, hi):
    """True if bearing b lies on the CCW arc from lo to hi."""
    b, lo, hi = wrap(b), wrap(lo), wrap(hi)
    if lo <= hi:
        return lo <= b <= hi
    return b >= lo or b <= hi


def seg_hits_box(p, q, hx=HALF_W, hy=HALF_L, eps=1e-9):
    """Liang-Barsky: does segment p->q pass through the open chassis box?"""
    x0, y0 = p
    dx, dy = q[0] - x0, q[1] - y0
    t0, t1 = 0.0, 1.0
    for pv, qv in ((-dx, x0 + hx), (dx, hx - x0), (-dy, y0 + hy), (dy, hy - y0)):
        if abs(pv) < eps:
            if qv <= eps:
                return False
            continue
        t = qv / pv
        if pv < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1 - eps:
            return False
    # Ignore grazing contact right at the sensor's own mount point.
    return t1 - t0 > 1e-6 and t1 > 1e-6


def contour(d, step=0.01):
    """Points on the rounded rectangle at stand-off d from the chassis box,
    tagged by region: front, rear, left, right, or a corner."""
    pts = []
    # straight faces
    n = int(round(2 * HALF_W / step))
    for i in range(n + 1):
        x = -HALF_W + i * step
        pts.append(((x, HALF_L + d), 'front'))
        pts.append(((x, -HALF_L - d), 'rear'))
    n = int(round(2 * HALF_L / step))
    for i in range(n + 1):
        y = -HALF_L + i * step
        pts.append(((HALF_W + d, y), 'right'))
        pts.append(((-HALF_W - d, y), 'left'))
    # quarter-circle corners
    arc_n = max(4, int(math.pi / 2 * d / step))
    for cx, cy, a0, tag in ((HALF_W, HALF_L, 0, 'corner'),
                            (-HALF_W, HALF_L, 90, 'corner'),
                            (-HALF_W, -HALF_L, 180, 'corner'),
                            (HALF_W, -HALF_L, 270, 'corner')):
        for k in range(arc_n + 1):
            a = math.radians(a0 + 90.0 * k / arc_n)
            pts.append(((cx + d * math.cos(a), cy + d * math.sin(a)), tag))
    return pts


# ---- sensor models ---------------------------------------------------------

class Lidar:
    """360 deg scanner with an optional masked arc and body occlusion."""

    def __init__(self, pos, mask=None, occluded_by_body=True, rmax=12.0,
                 rmin=0.05, name='lidar'):
        self.pos, self.mask, self.body = pos, mask, occluded_by_body
        self.rmax, self.rmin, self.name = rmax, rmin, name

    def sees(self, q):
        r = math.dist(self.pos, q)
        if not (self.rmin <= r <= self.rmax):
            return False
        if self.mask and in_arc(bearing(self.pos, q), *self.mask):
            return False
        if self.body and seg_hits_box(self.pos, q):
            return False
        return True


class Cone:
    """Single ToF module: horizontal cone of full angle fov_deg."""

    def __init__(self, pos, yaw_deg, fov_deg, rmax=3.5, rmin=0.02):
        self.pos, self.yaw, self.half = pos, yaw_deg, fov_deg / 2.0
        self.rmax, self.rmin = rmax, rmin

    def sees(self, q):
        r = math.dist(self.pos, q)
        if not (self.rmin <= r <= self.rmax):
            return False
        if abs(wrap(bearing(self.pos, q) - self.yaw)) > self.half:
            return False
        return not seg_hits_box(self.pos, q)


def coverage(sensors, d, by_region=True):
    pts = contour(d)
    tot, hit = {}, {}
    for q, tag in pts:
        tot[tag] = tot.get(tag, 0) + 1
        if any(s.sees(q) for s in sensors):
            hit[tag] = hit.get(tag, 0) + 1
    out = {k: hit.get(k, 0) / tot[k] for k in tot}
    out['ALL'] = sum(hit.values()) / sum(tot.values())
    return out


# ---- layouts ---------------------------------------------------------------

def ring_layout(kind, fov):
    """Candidate ToF layouts. Modules sit 1 cm proud of the chassis faces."""
    e = 0.01
    hx, hy = HALF_W + e, HALF_L + e
    corners = [Cone((hx, hy), 45, fov), Cone((-hx, hy), 135, fov),
               Cone((-hx, -hy), -135, fov), Cone((hx, -hy), -45, fov)]
    ends = [Cone((0, hy), 90, fov), Cone((0, -hy), -90, fov)]
    if kind == 'ring8':     # Hardware_Roadmap.md 1.3's estimate: ends, corners, mid-sides
        sides = [Cone((hx, 0), 0, fov), Cone((-hx, 0), 180, fov)]
        return ends + corners + sides
    if kind == 'ring12':    # three per long side
        sides = [Cone((sx * hx, y), 0 if sx > 0 else 180, fov)
                 for sx in (1, -1) for y in (-0.33, 0.0, 0.33)]
        return ends + corners + sides
    if kind == 'ring16':    # five per long side
        sides = [Cone((sx * hx, y), 0 if sx > 0 else 180, fov)
                 for sx in (1, -1) for y in (-0.40, -0.20, 0.0, 0.20, 0.40)]
        return ends + corners + sides
    if kind == 'rear5':     # patch only the X4 Pro's blind region
        return [Cone((0, -hy), -90, fov),
                Cone((hx, -hy), -45, fov), Cone((-hx, -hy), -135, fov),
                Cone((hx, -0.25), 0, fov), Cone((-hx, -0.25), 180, fov)]
    h = fov / 2.0
    # Flank "grazers": mounted at a corner, aimed ALONG the long side and
    # toed out by half the FoV, so the cone's inner edge runs down the flank
    # instead of half the cone being wasted inside the chassis.
    grazers = [Cone((hx, hy), -90 + h, fov), Cone((-hx, hy), -90 - h, fov),
               Cone((hx, -hy), 90 - h, fov), Cone((-hx, -hy), 90 + h, fov)]
    # End grazers: same trick across the short faces (front and rear).
    end_grazers = [Cone((hx, hy), 180 - h, fov), Cone((-hx, hy), h, fov),
                   Cone((hx, -hy), -180 + h, fov), Cone((-hx, -hy), -h, fov)]
    if kind == 'corner8':   # two modules per corner: one down the flank, one across the end
        return grazers + end_grazers
    if kind == 'corner9':   # corner8 plus a rear-centre module for the far rear field
        return grazers + end_grazers + [ends[1]]
    if kind == 'graze10':   # ends, four diagonal corners, four grazers
        return ends + corners + grazers
    if kind == 'graze8':    # ends + grazers + two rear diagonals (reversing matters more)
        return ends + grazers + corners[2:]
    if kind == 'rear_graze4':  # blind-region patch: rear, two rear grazers, rear diagonal pair collapsed
        return [Cone((0, -hy), -90, fov), grazers[2], grazers[3],
                Cone((hx, -hy), -45, fov)]
    raise ValueError(kind)


X4 = Lidar(LIDAR, mask=MASK, occluded_by_body=False, rmax=10.0, rmin=0.12,
           name='X4 Pro (masked)')


def fmt(cov, keys=('front', 'rear', 'left', 'right', 'corner', 'ALL')):
    return '  '.join(f'{k:>6}={100 * cov.get(k, float("nan")):5.1f}%' for k in keys)


# ---- reports ---------------------------------------------------------------

def report_blind():
    print('1. Where the masked X4 Pro is blind')
    print(f'   LiDAR at base_link {LIDAR}, mask {MASK} deg, chassis '
          f'{2 * HALF_W:.2f} x {2 * HALF_L:.2f} m\n')
    for d in (0.05, 0.10, 0.20, 0.30, 0.50):
        # the -45 deg ray reaches x = HALF_W + d at this y
        y_edge = LIDAR[1] - (HALF_W + d) * math.tan(math.radians(45))
        blind_len = max(0.0, min(HALF_L, y_edge) + HALF_L)
        print(f'   stand-off {d:.2f} m: each flank blind from y = {y_edge:+.2f} m '
              f'back to the rear edge, {blind_len:.2f} m of the 1.00 m side')
    print()
    for d in (0.10, 0.30):
        print(f'   contour coverage at d = {d:.2f} m: {fmt(coverage([X4], d))}')
    print()


def max_heading(L, W, A):
    """Largest |theta| (deg) with L*sin + W*cos <= A, starting aligned."""
    if A < W:
        return None
    if A >= math.hypot(L, W):
        return 90.0
    lo, hi = 0.0, math.atan2(L, W)   # f rises monotonically on this interval
    for _ in range(80):
        mid = (lo + hi) / 2
        if L * math.sin(mid) + W * math.cos(mid) <= A:
            lo = mid
        else:
            hi = mid
    return math.degrees(lo)


def report_aisle():
    print('2. Heading budget inside an aisle')
    print('   (largest yaw error before a corner reaches the wall, robot centred)\n')
    print('   aisle A   clear/side   bare 1.00x0.36   padded 1.12x0.48')
    for A in (0.50, 0.60, 0.70, 0.80, 0.90, 1.00, 1.10, 1.25):
        bare = max_heading(2 * HALF_L, 2 * HALF_W, A)
        pad = max_heading(2 * HALF_L + 2 * PAD, 2 * HALF_W + 2 * PAD, A)
        f = lambda v: ' does not fit' if v is None else f'{v:10.1f} deg'
        print(f'   {A:5.2f} m   {(A - 2 * HALF_W) / 2:7.3f} m   {f(bare)}   {f(pad)}')
    print(f'\n   rotate-in-place diameter: bare {math.hypot(1.0, 0.36):.3f} m, '
          f'padded {math.hypot(1.12, 0.48):.3f} m')
    print('   lateral swing of each end per degree of yaw: '
          f'{HALF_L * math.sin(math.radians(1)) * 1000:.1f} mm/deg')
    print(f'   4.49 deg phantom yaw (Research_Journal 17.56) moves each end '
          f'{HALF_L * math.sin(math.radians(4.49)) * 1000:.0f} mm, and over 5 m of '
          f'travel drifts {5 * math.sin(math.radians(4.49)):.2f} m sideways\n')


def report_ring():
    print('3. Stand-off coverage of candidate layouts (horizontal cone model)\n')
    for fov, part in ((45, 'VL53L5CX/L8CX-class, ~45 deg'), (60, 'VL53L7CX, 60 deg')):
        print(f'   {part}')
        for kind in ('ring8', 'ring12', 'ring16', 'graze8', 'corner8'):
            for d in (0.05, 0.10, 0.30, 0.50):
                c = coverage(ring_layout(kind, fov), d)
                print(f'     {kind:<7} d={d:.2f}  {fmt(c)}')
        for kind in ('rear5', 'rear_graze4', 'corner9'):
            for d in (0.05, 0.10, 0.30, 0.50, 0.80):
                c = coverage([X4] + ring_layout(kind, fov), d)
                print(f'     X4+{kind:<11} d={d:.2f} {fmt(c)}')
        print()
    print('   Rear 360 deg DTOF LiDAR added to the masked X4 Pro')
    for label, pos in (('rear centre', (0.0, -0.52)),
                       ('rear-right corner', (0.20, -0.52)),
                       ('rear-left corner', (-0.20, -0.52))):
        rear = Lidar(pos, mask=None, occluded_by_body=True, rmax=12.0, rmin=0.05)
        for d in (0.10, 0.30):
            print(f'     {label:<18} d={d:.2f}  {fmt(coverage([X4, rear], d))}')
    both = [Lidar((-0.20, 0.52), occluded_by_body=True),
            Lidar((0.20, -0.52), occluded_by_body=True)]
    for d in (0.10, 0.30):
        print(f'     diagonal pair, no X4 d={d:.2f}  {fmt(coverage(both, d))}')
    print()


# ---- self-test -------------------------------------------------------------

def selftest():
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f'  [{"PASS" if cond else "FAIL"}] {name}')
        ok &= bool(cond)

    check('wrap(-180) == 180', wrap(-180) == 180)
    check('in_arc handles wrap-around', in_arc(179, 170, -170) and not in_arc(0, 170, -170))
    check('ray through box centre hits box', seg_hits_box((0, -1), (0, 1)))
    check('ray beside box misses box', not seg_hits_box((0.5, -1), (0.5, 1)))
    check('ray grazing from a face-mounted sensor outward misses box',
          not seg_hits_box((0.19, 0.0), (1.0, 0.0)))
    check('heading budget is 0 when aisle == robot width',
          abs(max_heading(1.0, 0.36, 0.36)) < 1e-6)
    check('heading budget is 90 deg once aisle >= diagonal',
          max_heading(1.0, 0.36, 1.07) == 90.0)
    check('robot does not fit a narrower aisle', max_heading(1.0, 0.36, 0.30) is None)
    th = math.radians(max_heading(1.0, 0.36, 0.60))
    check('heading budget solves L sin + W cos = A',
          abs(1.0 * math.sin(th) + 0.36 * math.cos(th) - 0.60) < 1e-9)
    check('unmasked, unoccluded lidar sees the whole contour',
          coverage([Lidar(LIDAR, mask=None, occluded_by_body=False)], 0.2)['ALL'] == 1.0)
    check('masked X4 misses part of the rear',
          coverage([X4], 0.2)['rear'] < 0.5)
    check('a cone facing +Y sees a point dead ahead',
          Cone((0, 0.51), 90, 45).sees((0, 1.0)))
    check('a cone facing +Y does not see a point behind it',
          not Cone((0, 0.51), 90, 45).sees((0, -1.0)))
    print('selftest', 'PASSED' if ok else 'FAILED')
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('what', nargs='?', default='all',
                    choices=['blind', 'aisle', 'ring', 'all'])
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if a.what in ('blind', 'all'):
        report_blind()
    if a.what in ('aisle', 'all'):
        report_aisle()
    if a.what in ('ring', 'all'):
        report_ring()


if __name__ == '__main__':
    main()
