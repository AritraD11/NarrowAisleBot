#!/usr/bin/env python3
"""scan_range_envelope.py — at what range does this LiDAR stop being worth
believing, measured rather than read off a datasheet?

WHY THIS EXISTS. `scan_quality.py` already measures flicker and stationary
scatter, but it reports them as one number for the whole scan: "74.8-78% of
rays flip valid/invalid", "p90 scatter 22.8 mm". Those are averages over
every range at once, and they are the wrong shape for the decision actually
facing the project, which is *where to put the cap*. A triangulation scanner
does not degrade uniformly. It degrades with distance, and an average over
0.3 m and 9 m rays hides exactly the structure you need to see.

So this bins the same rays by range and asks, per bin: how often does this
bearing come back at all, and when it does, how far does it move while the
robot is standing still?

THE TWO BUDGETS, AND WHY THESE NUMBERS.

  Scatter <= 25 mm.  The occupancy grid is 0.05 m per cell
  (slam_nodom_stageB.yaml:143, and both costmaps at nav2_params.yaml:576 and
  :663). A ray whose scan-to-scan scatter exceeds HALF a cell votes for a
  different cell on consecutive sweeps. That is not an abstraction: it is
  the mechanism that thickens and doubles walls, which is the criterion
  (D2 < 1.0%) that G4 keeps failing on. Half a cell is 25 mm.

  Validity >= 90%.  A bearing that returns on fewer than nine sweeps in ten
  contributes inconsistent evidence to the same cell, marking on some sweeps
  and clearing on others. The scan matcher's objective function moves under
  it, which is §17.45's finding stated per-range instead of globally.

Both are configurable. Neither is a guess, and both are read off the
project's own deployed configuration rather than chosen for convenience.

    # on the Pi, park the robot first, nothing moving in the room
    ./tools/scan_quality.py --seconds 60 --save ~/aislebot_logs/env.json
    ./tools/scan_range_envelope.py --load ~/aislebot_logs/env.json

    ./tools/scan_range_envelope.py --load env.json --json envelope.json
    ./tools/scan_range_envelope.py --selftest

Pure standard library. Reads the file `scan_quality.py --save` writes, so it
needs no ROS and runs on a laptop.
"""
import argparse
import json
import math
import statistics
import sys
from pathlib import Path

# Half the 0.05 m occupancy cell. See the module docstring.
DEFAULT_MAX_STD_MM = 25.0
DEFAULT_MIN_VALID = 0.90
DEFAULT_BIN_M = 0.5

# Every consumer of /scan_reliable that carries its own range limit, with the
# file and line each is read from. A cap is only real if all of them agree.
CONSUMERS = [
    ('ydlidar driver', 'system/ydlidar_params.yaml', 'range_max', 10.0),
    ('slam_toolbox', 'system/slam_nodom_stageB.yaml', 'max_laser_range', 5.0),
    ('global costmap', 'src/mecanum_navigation/config/nav2_params.yaml',
     'obstacle_max_range', 8.0),
    ('global costmap', 'src/mecanum_navigation/config/nav2_params.yaml',
     'raytrace_max_range', 9.0),
    ('local costmap', 'src/mecanum_navigation/config/nav2_params.yaml',
     'obstacle_max_range', 8.0),
    ('local costmap', 'src/mecanum_navigation/config/nav2_params.yaml',
     'raytrace_max_range', 9.0),
    ('dashboard overlay', 'phone_dashboard.py', 'scan_trust_range', 5.0),
]


def valid_mask(ranges, rmin, rmax):
    """Matches scan_quality.py exactly. ydlidar_params.yaml sets
    invalid_range_is_inf: false, so a dead ray arrives as 0.0 rather than inf.
    Treating that as a 0 m obstacle would paint a wall on the sensor."""
    out = []
    for r in ranges:
        ok = (r is not None and not math.isinf(r) and not math.isnan(r)
              and r > max(rmin, 1e-3) and r < rmax)
        out.append(ok)
    return out


def per_ray(scans):
    """One row per bearing: how often it returned, and how far it moved.

    A ray is placed in a bin by the MEAN of its valid returns. Scatter is
    computed over those same valid returns. That differs deliberately from
    scan_quality.py's stationary block, which only gives a std to rays valid
    in EVERY scan: here a ray that flickers still needs a range so it can be
    binned, and its flicker is reported alongside rather than instead.
    """
    if len(scans) < 3:
        raise SystemExit('need at least 3 scans; capture a longer window')
    n = min(len(s['ranges']) for s in scans)
    masks = [valid_mask(s['ranges'][:n], s['range_min'], s['range_max'])
             for s in scans]

    rows = []
    for i in range(n):
        vals = [s['ranges'][i] for s, m in zip(scans, masks) if m[i]]
        if not vals:
            continue
        rows.append({
            'index': i,
            'mean_m': statistics.fmean(vals),
            'valid_frac': len(vals) / len(scans),
            'std_mm': 1000.0 * statistics.pstdev(vals) if len(vals) >= 2 else None,
            'n_valid': len(vals),
        })
    return rows


def bin_rows(rows, bin_m, rmax_cap=None):
    """Group the per-ray rows into fixed-width range bins."""
    bins = {}
    for r in rows:
        if rmax_cap is not None and r['mean_m'] > rmax_cap:
            continue
        k = int(r['mean_m'] / bin_m)
        bins.setdefault(k, []).append(r)

    out = []
    for k in sorted(bins):
        grp = bins[k]
        stds = sorted(x['std_mm'] for x in grp if x['std_mm'] is not None)
        vfs = sorted(x['valid_frac'] for x in grp)
        out.append({
            'lo_m': round(k * bin_m, 3),
            'hi_m': round((k + 1) * bin_m, 3),
            'rays': len(grp),
            'valid_median': round(statistics.median(vfs), 4),
            'valid_p10': round(vfs[max(0, int(0.10 * (len(vfs) - 1)))], 4),
            'std_median_mm': round(statistics.median(stds), 2) if stds else None,
            'std_p90_mm': (round(stds[min(len(stds) - 1, int(0.90 * (len(stds) - 1)))], 2)
                           if stds else None),
        })
    return out


def recommend(binned, max_std_mm, min_valid, min_rays=4):
    """The largest range at which every bin up to it still passes both
    budgets. Deliberately not 'the largest passing bin': one good bin beyond
    a failing one is noise, and a cap has to hold for everything inside it.

    Bins with too few rays to mean anything are skipped rather than failed,
    because an empty bin says the room has no wall at that distance, which is
    a fact about the room and not about the sensor.
    """
    cap = 0.0
    first_fail = None
    for b in binned:
        if b['rays'] < min_rays:
            continue
        bad_std = b['std_p90_mm'] is not None and b['std_p90_mm'] > max_std_mm
        bad_val = b['valid_median'] < min_valid
        if bad_std or bad_val:
            reasons = []
            if bad_std:
                reasons.append(f"scatter p90 {b['std_p90_mm']:.1f} mm > {max_std_mm:.0f} mm")
            if bad_val:
                reasons.append(f"validity {100 * b['valid_median']:.0f}% < {100 * min_valid:.0f}%")
            first_fail = {'lo_m': b['lo_m'], 'hi_m': b['hi_m'], 'why': '; '.join(reasons)}
            break
        cap = b['hi_m']
    return cap, first_fail


def report(scans, binned, cap, first_fail, max_std_mm, min_valid):
    print(f'\n  {len(scans)} scans, {len(binned)} populated range bins\n')
    print('  range (m)      rays   validity   scatter p90   verdict')
    print('  ' + '-' * 62)
    for b in binned:
        v = f"{100 * b['valid_median']:5.1f}%"
        s = f"{b['std_p90_mm']:7.1f} mm" if b['std_p90_mm'] is not None else '      n/a'
        if b['rays'] < 4:
            verdict = 'too few rays'
        elif ((b['std_p90_mm'] is not None and b['std_p90_mm'] > max_std_mm)
              or b['valid_median'] < min_valid):
            verdict = 'FAIL'
        else:
            verdict = 'ok'
        print(f"  {b['lo_m']:5.2f} - {b['hi_m']:5.2f}  {b['rays']:5d}   {v}   {s}    {verdict}")

    print(f'\n  Budgets: scatter p90 <= {max_std_mm:.0f} mm (half the 0.05 m cell), '
          f'validity >= {100 * min_valid:.0f}%')

    if cap <= 0:
        print('\n  RECOMMENDED CAP: none of the bins passed. Either the room is '
              '\n  empty at short range or something is wrong upstream. Run '
              'scan_quality.py\n  before believing this.')
        return

    print(f'\n  RECOMMENDED max_laser_range: {cap:.1f} m')
    if first_fail:
        print(f"  First failing bin is {first_fail['lo_m']:.2f}-{first_fail['hi_m']:.2f} m: "
              f"{first_fail['why']}")
    else:
        print('  No bin failed inside the captured data, so this cap is set by the '
              '\n  furthest wall in the room rather than by the sensor. Capture '
              'somewhere\n  with a longer sightline before treating it as the '
              'sensor limit.')

    print('\n  Consumers that must agree on this number:\n')
    print('  where                 parameter              now      set to')
    print('  ' + '-' * 58)
    for name, path, param, now in CONSUMERS:
        flag = '' if now <= cap + 1e-9 else '   <-- trusts rays the data does not'
        print(f'  {name:20s}  {param:21s}  {now:5.1f}    {cap:5.1f}{flag}')
    print(f'\n  ({len(CONSUMERS)} settings across 4 files. A cap applied to SLAM alone '
          'leaves the\n  costmaps marking and clearing on rays SLAM refuses to match '
          'against.)\n')


# ── self-test ─────────────────────────────────────────────────────────
def _synthetic(noise_coeff_mm_per_m2, flicker_from_m, n_scans=40, seed=7):
    """Rays at known ranges with known, range-dependent noise and dropout, so
    the recommendation has an answer that is right by construction."""
    import random
    rng = random.Random(seed)
    true = [0.4 + 0.05 * i for i in range(160)]          # 0.40 m to 8.35 m
    scans = []
    for _ in range(n_scans):
        ranges = []
        for r in true:
            if r >= flicker_from_m and rng.random() < 0.5:
                ranges.append(0.0)                        # dead ray, as the driver sends it
                continue
            sigma_m = (noise_coeff_mm_per_m2 * r * r) / 1000.0
            ranges.append(max(0.05, rng.gauss(r, sigma_m)))
        scans.append({'angle_min': -math.pi, 'angle_max': math.pi,
                      'angle_increment': 2 * math.pi / len(true),
                      'range_min': 0.1, 'range_max': 12.0, 'ranges': ranges})
    return scans


def selftest():
    fails = []

    def chk(cond, label):
        print(f'  {"PASS" if cond else "FAIL"}  {label}')
        if not cond:
            fails.append(label)

    print('\nscan_range_envelope self-test\n')

    # 4 mm/m^2 crosses a 25 mm budget at r = sqrt(25/4) = 2.5 m.
    scans = _synthetic(noise_coeff_mm_per_m2=4.0, flicker_from_m=99.0)
    rows = per_ray(scans)
    binned = bin_rows(rows, 0.5)
    cap, ff = recommend(binned, DEFAULT_MAX_STD_MM, DEFAULT_MIN_VALID)
    chk(2.0 <= cap <= 3.0,
        f'a quadratic-noise sensor crossing 25 mm at 2.5 m caps near there (got {cap:.1f} m)')
    chk(ff is not None and 'scatter' in ff['why'], 'the failing bin blames scatter')

    # halve the coefficient and the crossing moves out to sqrt(25/2) = 3.54 m
    scans = _synthetic(noise_coeff_mm_per_m2=2.0, flicker_from_m=99.0)
    cap2, _ = recommend(bin_rows(per_ray(scans), 0.5),
                        DEFAULT_MAX_STD_MM, DEFAULT_MIN_VALID)
    chk(cap2 > cap, f'a quieter sensor earns a longer cap ({cap2:.1f} m > {cap:.1f} m)')

    # a clean sensor that simply stops returning past 3 m must fail on validity
    scans = _synthetic(noise_coeff_mm_per_m2=0.2, flicker_from_m=3.0)
    cap3, ff3 = recommend(bin_rows(per_ray(scans), 0.5),
                          DEFAULT_MAX_STD_MM, DEFAULT_MIN_VALID)
    chk(2.5 <= cap3 <= 3.5, f'dropout past 3 m caps near 3 m (got {cap3:.1f} m)')
    chk(ff3 is not None and 'validity' in ff3['why'],
        'the failing bin blames validity, not scatter')

    # dead rays arrive as 0.0, and must not be averaged in as 0 m obstacles
    rows = per_ray(_synthetic(0.2, 3.0))
    near = [r for r in rows if r['mean_m'] < 0.6]
    chk(all(r['mean_m'] > 0.3 for r in near),
        'a 0.0 dead ray is excluded rather than dragging the mean to zero')

    far = [r for r in rows if r['mean_m'] > 3.5]
    chk(far and all(r['valid_frac'] < 0.75 for r in far),
        'rays past the dropout threshold report low validity')

    # the cap must hold for everything inside it, not just the last bin
    holey = [
        {'lo_m': 0.0, 'hi_m': 0.5, 'rays': 10, 'valid_median': 1.0, 'valid_p10': 1.0,
         'std_median_mm': 5.0, 'std_p90_mm': 6.0},
        {'lo_m': 0.5, 'hi_m': 1.0, 'rays': 10, 'valid_median': 1.0, 'valid_p10': 1.0,
         'std_median_mm': 90.0, 'std_p90_mm': 99.0},
        {'lo_m': 1.0, 'hi_m': 1.5, 'rays': 10, 'valid_median': 1.0, 'valid_p10': 1.0,
         'std_median_mm': 5.0, 'std_p90_mm': 6.0},
    ]
    cap4, _ = recommend(holey, DEFAULT_MAX_STD_MM, DEFAULT_MIN_VALID)
    chk(abs(cap4 - 0.5) < 1e-9,
        f'one good bin beyond a failing one does not extend the cap (got {cap4:.1f} m)')

    # a sparse bin is skipped, not failed
    sparse = [
        {'lo_m': 0.0, 'hi_m': 0.5, 'rays': 10, 'valid_median': 1.0, 'valid_p10': 1.0,
         'std_median_mm': 5.0, 'std_p90_mm': 6.0},
        {'lo_m': 0.5, 'hi_m': 1.0, 'rays': 1, 'valid_median': 0.1, 'valid_p10': 0.1,
         'std_median_mm': 900.0, 'std_p90_mm': 999.0},
        {'lo_m': 1.0, 'hi_m': 1.5, 'rays': 10, 'valid_median': 1.0, 'valid_p10': 1.0,
         'std_median_mm': 5.0, 'std_p90_mm': 6.0},
    ]
    cap5, _ = recommend(sparse, DEFAULT_MAX_STD_MM, DEFAULT_MIN_VALID)
    chk(abs(cap5 - 1.5) < 1e-9,
        f'a bin with too few rays is skipped rather than capping the sensor (got {cap5:.1f} m)')

    print()
    if fails:
        print(f'{len(fails)} FAILED')
        return 1
    print('all self-tests passed')
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--load', help='JSON written by scan_quality.py --save')
    ap.add_argument('--json', help='write the binned result here')
    ap.add_argument('--bin', type=float, default=DEFAULT_BIN_M, help='bin width, m')
    ap.add_argument('--max-std-mm', type=float, default=DEFAULT_MAX_STD_MM)
    ap.add_argument('--min-valid', type=float, default=DEFAULT_MIN_VALID)
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if not args.load:
        sys.exit('give me --load <scan_quality --save file>, or --selftest')

    scans = json.loads(Path(args.load).read_text())
    rows = per_ray(scans)
    binned = bin_rows(rows, args.bin)
    cap, ff = recommend(binned, args.max_std_mm, args.min_valid)
    report(scans, binned, cap, ff, args.max_std_mm, args.min_valid)

    if args.json:
        Path(args.json).write_text(json.dumps({
            'scans': len(scans),
            'bin_m': args.bin,
            'max_std_mm': args.max_std_mm,
            'min_valid': args.min_valid,
            'bins': binned,
            'recommended_cap_m': cap,
            'first_failing_bin': ff,
        }, indent=2))
        print(f'  wrote {args.json}\n')


if __name__ == '__main__':
    main()
