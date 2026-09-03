#!/usr/bin/env python3
"""scan_quality.py — measure what the LiDAR actually gives the scan matcher.

Everything else in this project has been measured. The map (map_integrity),
the odometry and corrections (run_analyzer), the wheels (telemetry), the pose
graph (graph_residuals). The one input the scan matcher actually consumes —
the scan itself — never has been. That is the gap this closes.

It exists because of a specific finding: run_20260826_120314 produced 19
correction events, and EVERY ONE fired while wheel odometry was reporting
0.004-0.016 m of motion. The robot was standing still and the pose graph
moved anyway. A stationary robot's scan should be near-identical frame to
frame, so either the scan is unstable, or the geometry is ambiguous enough
that two different poses score equally well. Both are measurable, and
neither has been measured.

    ./tools/scan_quality.py                    # 10 s capture, PARK THE ROBOT
    ./tools/scan_quality.py --seconds 30
    ./tools/scan_quality.py --save scan.json   # capture for later
    ./tools/scan_quality.py --load scan.json   # analyse, no ROS needed
    ./tools/scan_quality.py --selftest

═══════════════════════════════════════════════════════════════════════════
  THE THREE THINGS IT MEASURES
═══════════════════════════════════════════════════════════════════════════

1. RETURN QUALITY -- how much of each scan is usable at all.
   The X4 Pro reports out to 12 m but slam_nodom_stageB.yaml sets
   `max_laser_range: 10.0`, so everything past 10 m is DISCARDED by
   slam_toolbox before matching. A scan that looks full can be mostly
   waste. Note `invalid_range_is_inf: false` in ydlidar_params.yaml: dead
   rays arrive as 0.0, not inf, and a tool checking only for inf silently
   counts them as 0 m obstacles.

2. GEOMETRIC CONDITIONING -- whether the scan can pin down a pose AT ALL.
   This is the one that matters, and it is not a heuristic. A scan
   constrains translation only along directions its surfaces face. Build
   M = SUM(n n^T) over surface normals; its eigenvalues say how well each
   direction is constrained. Two parallel walls (a corridor, an aisle) put
   every normal on one axis, so the scan slides freely along the other and
   the matcher has nothing to stop it. That is textbook perceptual aliasing
   and it is exactly the failure this robot keeps hitting. Reported as
   conditioning = lambda_min / lambda_max, in [0, 1], with the bearing of
   the weak direction so it can be checked against the floor plan.

3. STATIONARY STABILITY -- the discriminator.
   With the robot PARKED and nothing moving, per-ray range variation across
   scans is the sensor's own noise floor. Steady to a few mm means the
   sensor is fine and the corrections are a matcher/geometry problem.
   Ranges that wander centimetres, or flicker valid/invalid, mean the
   matcher is being fed a moving target and no amount of parameter tuning
   fixes that.

Pure standard library. rclpy is imported only in live mode, so --selftest
and --load run anywhere.
"""
import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path

TOPIC = '/scan_reliable'          # what slam_toolbox consumes (stageB yaml)
# max_laser_range: beyond this, slam_toolbox discards the return.
# DEFAULT DELIBERATELY LEFT AT 10.0 even though Stage G deployed 5.0 on
# 3 Sep 2026. §17.46's rule: changing an instrument mid-campaign destroys
# the baseline it is being compared against, and every figure already in
# the journal was computed against 10.0. Pass --slam-max-range 5.0 to see
# the deployed reality; the default output stays byte-comparable with
# §17.45 and every run before it.
SLAM_MAX_RANGE = 10.0
CONTINUITY_M = 0.10               # adjacent rays within this = one surface
MIN_SURFACE_PTS = 20
COND_POOR = 0.15                  # below this, one axis is barely constrained
COND_MARGINAL = 0.35
STABLE_MM = 15.0                  # per-ray std above this = unstable
FLICKER_FRAC = 0.05


# ═════════════════════════════════════════════════════════════════════════
#  Scan handling
# ═════════════════════════════════════════════════════════════════════════
def valid_mask(ranges, rmin, rmax):
    """ydlidar_params.yaml sets invalid_range_is_inf: false, so a dead ray
    arrives as 0.0. Treating that as a 0 m obstacle would put a phantom wall
    on the sensor -- check the floor explicitly, not just inf/nan."""
    out = []
    for r in ranges:
        ok = (r is not None and not math.isinf(r) and not math.isnan(r)
              and r > max(rmin, 1e-3) and r < rmax)
        out.append(ok)
    return out


def to_points(ranges, mask, angle_min, angle_inc):
    pts = []
    for i, (r, ok) in enumerate(zip(ranges, mask)):
        if not ok:
            pts.append(None)
            continue
        a = angle_min + i * angle_inc
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def conditioning(ranges, mask, angle_min, angle_inc, max_range=SLAM_MAX_RANGE):
    """How well this scan constrains a 2-D translation.

    For each ray that sits on a locally continuous surface, estimate the
    surface direction from its neighbours and take the normal. Accumulate
    M = SUM(n n^T). Its eigenvalues are the constraint strength along each
    principal direction: equal eigenvalues mean surfaces face every way and
    the pose is pinned; a near-zero smaller eigenvalue means every surface
    faces the same way and the scan can slide perpendicular to it for free.

    Only rays inside `max_range` are used, because slam_toolbox discards the
    rest before matching -- conditioning computed on rays it never sees would
    describe a scan that does not exist.
    """
    pts = to_points(ranges, mask, angle_min, angle_inc)
    n = len(pts)
    sxx = sxy = syy = 0.0
    used = 0
    for i in range(n):
        p, pa, pb = pts[i], pts[(i - 1) % n], pts[(i + 1) % n]
        if p is None or pa is None or pb is None:
            continue
        if ranges[i] > max_range:
            continue
        # both neighbours must lie on the same surface, or this is an edge
        if (abs(ranges[i] - ranges[(i - 1) % n]) > CONTINUITY_M or
                abs(ranges[i] - ranges[(i + 1) % n]) > CONTINUITY_M):
            continue
        tx, ty = pb[0] - pa[0], pb[1] - pa[1]
        L = math.hypot(tx, ty)
        if L < 1e-6:
            continue
        nx, ny = -ty / L, tx / L          # normal = tangent rotated 90 deg
        sxx += nx * nx
        sxy += nx * ny
        syy += ny * ny
        used += 1

    if used < MIN_SURFACE_PTS:
        return {'surface_points': used, 'conditioning': None,
                'weak_axis_deg': None, 'lambda_max': None, 'lambda_min': None}

    tr = sxx + syy
    det = sxx * syy - sxy * sxy
    disc = max(tr * tr - 4 * det, 0.0)
    lmax = (tr + math.sqrt(disc)) / 2
    lmin = (tr - math.sqrt(disc)) / 2
    # eigenvector for the SMALLER eigenvalue = the poorly constrained axis
    if abs(sxy) > 1e-12:
        wx, wy = lmin - syy, sxy
    else:
        wx, wy = (1.0, 0.0) if sxx <= syy else (0.0, 1.0)
    return {
        'surface_points': used,
        'conditioning': round(lmin / lmax, 4) if lmax > 0 else None,
        'weak_axis_deg': round(math.degrees(math.atan2(wy, wx)) % 180.0, 1),
        'lambda_max': round(lmax, 1), 'lambda_min': round(lmin, 1),
    }


def scan_stats(s):
    rmin, rmax = s['range_min'], s['range_max']
    ranges = s['ranges']
    mask = valid_mask(ranges, rmin, rmax)
    nvalid = sum(mask)
    vals = [r for r, ok in zip(ranges, mask) if ok]
    out = {'rays': len(ranges), 'valid': nvalid,
           'valid_pct': round(100.0 * nvalid / max(len(ranges), 1), 1)}
    if vals:
        sv = sorted(vals)
        out.update({
            'range_min_m': round(sv[0], 2),
            'range_p50_m': round(statistics.median(sv), 2),
            'range_p90_m': round(sv[min(len(sv) - 1, int(0.9 * len(sv)))], 2),
            'range_max_m': round(sv[-1], 2),
            'beyond_slam_max_pct': round(
                100.0 * sum(1 for v in vals if v > SLAM_MAX_RANGE) / len(vals), 1),
            'within_1m_pct': round(100.0 * sum(1 for v in vals if v <= 1.0) / len(vals), 1),
            'within_3m_pct': round(100.0 * sum(1 for v in vals if v <= 3.0) / len(vals), 1),
            'within_5m_pct': round(100.0 * sum(1 for v in vals if v <= 5.0) / len(vals), 1),
        })
    # largest angular gap of consecutive invalid rays -- the mast's blind arc
    # should show up here at roughly 90 deg, which doubles as a sanity check
    # that the tool is reading the right topic.
    best = cur = 0
    for ok in mask + mask:                 # wrap once for a gap across 0 deg
        cur = 0 if ok else cur + 1
        best = max(best, cur)
    best = min(best, len(ranges))
    out['largest_gap_deg'] = round(best * math.degrees(s['angle_increment']), 1)
    out.update(conditioning(ranges, mask, s['angle_min'], s['angle_increment']))
    return out


def stability(scans):
    """Per-ray variation across a stationary capture.

    Only rays valid in EVERY scan get a std -- a ray that drops in and out is
    reported separately as flicker, because averaging over its valid samples
    would hide exactly the instability being looked for.
    """
    if len(scans) < 3:
        return {'scans': len(scans), 'note': 'need at least 3 scans'}
    n = min(len(s['ranges']) for s in scans)
    masks = [valid_mask(s['ranges'][:n], s['range_min'], s['range_max']) for s in scans]
    always = [i for i in range(n) if all(m[i] for m in masks)]
    ever = [i for i in range(n) if any(m[i] for m in masks)]
    flicker = [i for i in ever if i not in always]

    stds = []
    for i in always:
        vals = [s['ranges'][i] for s in scans]
        if len(vals) >= 2:
            stds.append(statistics.pstdev(vals))
    out = {
        'scans': len(scans),
        'rays_always_valid': len(always),
        'rays_ever_valid': len(ever),
        'flicker_rays': len(flicker),
        'flicker_pct': round(100.0 * len(flicker) / max(len(ever), 1), 1),
    }
    if stds:
        ss = sorted(stds)
        out.update({
            'range_std_median_mm': round(1000 * statistics.median(ss), 1),
            'range_std_p90_mm': round(1000 * ss[min(len(ss) - 1, int(0.9 * len(ss)))], 1),
            'range_std_max_mm': round(1000 * ss[-1], 1),
        })
    return out


def analyse(scans):
    per = [scan_stats(s) for s in scans]
    conds = [p['conditioning'] for p in per if p['conditioning'] is not None]
    res = {
        'n_scans': len(scans),
        'per_scan_median': {},
        'stability': stability(scans),
    }
    for k in ('valid_pct', 'range_p50_m', 'range_p90_m', 'beyond_slam_max_pct',
              'within_1m_pct', 'within_3m_pct', 'within_5m_pct',
              'largest_gap_deg', 'surface_points'):
        vals = [p[k] for p in per if p.get(k) is not None]
        if vals:
            res['per_scan_median'][k] = round(statistics.median(vals), 1)
    if conds:
        res['conditioning'] = {
            'median': round(statistics.median(conds), 4),
            'min': round(min(conds), 4), 'max': round(max(conds), 4),
        }
        weak = [p['weak_axis_deg'] for p in per if p.get('weak_axis_deg') is not None]
        if weak:
            res['conditioning']['weak_axis_deg_median'] = round(statistics.median(weak), 1)
    else:
        res['conditioning'] = None

    flags, verdict = [], 'OK'
    c = (res.get('conditioning') or {}).get('median')
    if c is not None:
        if c < COND_POOR:
            flags.append(
                f"conditioning {c:.3f} -- the scan barely constrains one axis "
                f"(weak direction ~{res['conditioning'].get('weak_axis_deg_median')} deg). "
                f"The matcher can slide along it for free; this is aliasing, "
                f"not noise, and parameter tuning will not fix geometry.")
            verdict = 'POORLY CONSTRAINED'
        elif c < COND_MARGINAL:
            flags.append(f"conditioning {c:.3f} -- marginal; one axis is much "
                         f"weaker than the other")
            verdict = 'MARGINAL'
    st = res['stability']
    if st.get('range_std_p90_mm', 0) > STABLE_MM:
        flags.append(f"stationary range noise p90 {st['range_std_p90_mm']} mm -- "
                     f"the scan is moving while the robot is not")
        verdict = 'UNSTABLE'
    if st.get('flicker_pct', 0) > 100 * FLICKER_FRAC:
        flags.append(f"{st['flicker_pct']}% of rays flicker valid/invalid while "
                     f"parked")
        if verdict == 'OK':
            verdict = 'UNSTABLE'
    b = res['per_scan_median'].get('beyond_slam_max_pct', 0)
    if b > 25:
        flags.append(f"{b}% of returns are beyond max_laser_range "
                     f"({SLAM_MAX_RANGE} m) and are discarded before matching")
    res['flags'] = flags
    res['verdict'] = verdict
    return res


# ═════════════════════════════════════════════════════════════════════════
#  Report
# ═════════════════════════════════════════════════════════════════════════
def print_report(r):
    print(f"\n{'=' * 70}\n  LIDAR SCAN QUALITY  ->  {r['verdict']}\n{'=' * 70}")
    m = r['per_scan_median']
    print(f"  {r['n_scans']} scans")
    print(f"\n  RETURNS (median per scan)")
    print(f"    valid            {m.get('valid_pct','?')}% of rays")
    print(f"    range            p50 {m.get('range_p50_m','?')} m, "
          f"p90 {m.get('range_p90_m','?')} m")
    print(f"    close structure  {m.get('within_1m_pct','?')}% <1 m, "
          f"{m.get('within_3m_pct','?')}% <3 m, {m.get('within_5m_pct','?')}% <5 m")
    print(f"    discarded        {m.get('beyond_slam_max_pct','?')}% beyond "
          f"max_laser_range {SLAM_MAX_RANGE} m")
    print(f"    largest gap      {m.get('largest_gap_deg','?')} deg "
          f"(the mast blinds ~90 deg by design)")

    c = r.get('conditioning')
    print(f"\n  GEOMETRIC CONDITIONING -- can this scan pin down a pose?")
    if not c:
        print("    not computable: too few continuous surface points.")
        print("    That is itself the finding -- the scan is scattered clutter,")
        print("    not surfaces, and there is nothing for the matcher to lock onto.")
    else:
        print(f"    surface points   {m.get('surface_points','?')} per scan")
        print(f"    conditioning     {c['median']:.3f}   (0 = one axis free, "
              f"1 = fully pinned)")
        print(f"    range over run   {c['min']:.3f} .. {c['max']:.3f}")
        print(f"    weak axis        ~{c.get('weak_axis_deg_median','?')} deg "
              f"in the sensor frame")

    st = r['stability']
    print(f"\n  STATIONARY STABILITY -- robot parked, nothing moving")
    if 'note' in st:
        print(f"    {st['note']}")
    else:
        print(f"    rays valid in every scan  {st['rays_always_valid']} of "
              f"{st['rays_ever_valid']} ever-valid")
        print(f"    flicker                   {st['flicker_pct']}% of rays "
              f"drop in and out")
        if 'range_std_median_mm' in st:
            print(f"    per-ray range noise       median "
                  f"{st['range_std_median_mm']} mm, p90 {st['range_std_p90_mm']} mm, "
                  f"max {st['range_std_max_mm']} mm")

    if r['flags']:
        print('\n  flags:')
        for f in r['flags']:
            print(f'    - {f}')
    print()
    if r['verdict'] == 'OK':
        print('  The sensor is steady and the geometry constrains a pose. If the')
        print('  pose graph is still jumping here, the cause is the matcher or its')
        print('  parameters, not what it is being fed.')
    elif r['verdict'] == 'UNSTABLE':
        print('  The scan is changing while the robot is not. The matcher is being')
        print('  fed a moving target -- fix that before tuning anything, because no')
        print('  parameter compensates for an input that will not sit still.')
    else:
        print('  The geometry does not pin the pose down. Corrections here are the')
        print('  matcher sliding along an unconstrained axis, which is a property of')
        print('  the SPACE, not a bug. Map somewhere with more varied surfaces, or')
        print('  drive close enough that near structure dominates the scan.')


# ═════════════════════════════════════════════════════════════════════════
#  Live capture
# ═════════════════════════════════════════════════════════════════════════
def run_live(args):
    try:
        import rclpy
        from rclpy.node import Node
        from rclpy.qos import qos_profile_sensor_data
        from sensor_msgs.msg import LaserScan
    except ImportError as exc:
        sys.exit(f'{exc}\n\nLive mode needs a sourced ROS 2 environment:\n'
                 '  source /opt/ros/jazzy/setup.bash\n'
                 'To analyse without ROS, use --load on a file made by --save.')

    got = []

    class Sub(Node):
        def __init__(self):
            super().__init__('scan_quality')
            self.create_subscription(LaserScan, args.topic, self.cb,
                                     qos_profile_sensor_data)

        def cb(self, msg):
            got.append({
                'angle_min': msg.angle_min, 'angle_max': msg.angle_max,
                'angle_increment': msg.angle_increment,
                'range_min': msg.range_min, 'range_max': msg.range_max,
                'ranges': [float(v) for v in msg.ranges],
            })
            if len(got) % 10 == 0:
                print(f'  {len(got)} scans...', flush=True)

    rclpy.init()
    node = Sub()
    print(f'subscribed to {args.topic}')
    print(f'capturing {args.seconds:.0f} s — KEEP THE ROBOT PARKED AND STILL,')
    print('and keep people out of the LiDAR plane, or the stability number')
    print('measures them instead of the sensor.\n')
    deadline = time.time() + args.seconds
    try:
        while rclpy.ok() and time.time() < deadline:
            rclpy.spin_once(node, timeout_sec=0.2)
    except KeyboardInterrupt:
        print('\nstopped early')
    finally:
        node.destroy_node()
        rclpy.shutdown()

    if not got:
        sys.exit(f'\nno messages on {args.topic} in {args.seconds:.0f} s.\n'
                 'Is the LiDAR running? Try --topic /scan if scan_relay is down.')
    return got


# ═════════════════════════════════════════════════════════════════════════
#  Self-test — synthetic scans with known answers
# ═════════════════════════════════════════════════════════════════════════
def _synth(kind, n=720, noise=0.0, seed=1):
    import random
    rnd = random.Random(seed)
    amin, ainc = -math.pi, 2 * math.pi / n
    ranges = []
    for i in range(n):
        a = amin + i * ainc
        ca, sa = math.cos(a), math.sin(a)
        if kind == 'room':                 # 6x6 m box: normals on both axes
            cands = []
            for half, c in ((3.0, ca), (3.0, sa)):
                if abs(c) > 1e-9:
                    t = half / abs(c)
                    cands.append(t)
            r = min(cands) if cands else 0.0
        elif kind == 'corridor':           # two parallel walls only: aliasing
            r = 1.5 / abs(sa) if abs(sa) > 1e-9 else 0.0
            if r > 11.0:
                r = 0.0                    # no return down the corridor
        elif kind == 'clutter':            # scattered points, no surfaces
            r = rnd.uniform(0.5, 8.0) if rnd.random() < 0.5 else 0.0
        else:
            r = 0.0
        if r and noise:
            r += rnd.gauss(0, noise)
        ranges.append(max(r, 0.0))
    return {'angle_min': amin, 'angle_max': -amin, 'angle_increment': ainc,
            'range_min': 0.1, 'range_max': 12.0, 'ranges': ranges}


def selftest(args):
    ok = True

    room = [_synth('room', noise=0.001, seed=s) for s in range(8)]
    r = analyse(room)
    c = (r['conditioning'] or {}).get('median')
    print(f"  square room    conditioning {c}  verdict {r['verdict']}")
    if c is None or c < 0.5:
        print('                 FAIL: a box has surfaces on both axes and must '
              'be well conditioned')
        ok = False

    corr = [_synth('corridor', noise=0.001, seed=s) for s in range(8)]
    r = analyse(corr)
    c = (r['conditioning'] or {}).get('median')
    print(f"  corridor       conditioning {c}  verdict {r['verdict']}  "
          f"weak axis {(r['conditioning'] or {}).get('weak_axis_deg_median')} deg")
    if c is None or c > COND_POOR:
        print('                 FAIL: two parallel walls must come out poorly '
              'constrained -- this is the aliasing case the tool exists for')
        ok = False
    elif r['verdict'] != 'POORLY CONSTRAINED':
        print(f"                 FAIL: expected POORLY CONSTRAINED")
        ok = False

    clut = [_synth('clutter', seed=s) for s in range(8)]
    r = analyse(clut)
    c = (r['conditioning'] or {}).get('median')
    print(f"  scatter        conditioning {c}  surface pts "
          f"{r['per_scan_median'].get('surface_points', 0)}")
    if c is not None and c > 0.5:
        print('                 FAIL: random scatter has no real surfaces and '
              'must not read as well-conditioned')
        ok = False

    steady = [_synth('room', noise=0.001, seed=s) for s in range(10)]
    r = analyse(steady)
    p90 = r['stability'].get('range_std_p90_mm')
    print(f"  steady sensor  range noise p90 {p90} mm  verdict {r['verdict']}")
    if p90 is None or p90 > STABLE_MM:
        print('                 FAIL: 1 mm synthetic noise must not read as unstable')
        ok = False

    noisy = [_synth('room', noise=0.05, seed=s) for s in range(10)]
    r = analyse(noisy)
    p90 = r['stability'].get('range_std_p90_mm')
    print(f"  noisy sensor   range noise p90 {p90} mm  verdict {r['verdict']}")
    if p90 is None or p90 < STABLE_MM:
        print('                 FAIL: 50 mm synthetic noise must be caught')
        ok = False

    print('\nselftest:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--topic', default=TOPIC)
    ap.add_argument('--seconds', type=float, default=10.0)
    ap.add_argument('--save')
    ap.add_argument('--load')
    ap.add_argument('--json')
    ap.add_argument('--slam-max-range', type=float, default=None,
                    help='override max_laser_range for the "discarded" figure '
                         '(deployed value is 5.0 since Stage G; the default '
                         'stays 10.0 so historical runs remain comparable)')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        return selftest(args)

    scans = json.loads(Path(args.load).read_text()) if args.load else run_live(args)
    if args.slam_max_range is not None:
        global SLAM_MAX_RANGE
        SLAM_MAX_RANGE = args.slam_max_range

    if args.save:
        Path(args.save).write_text(json.dumps(scans))
        print(f'wrote {args.save} ({len(scans)} scans)')

    res = analyse(scans)
    print_report(res)
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=2))
        print(f'  wrote {args.json}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
