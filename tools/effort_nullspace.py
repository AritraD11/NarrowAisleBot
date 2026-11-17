#!/usr/bin/env python3
"""effort_nullspace.py - what the motors are doing that moves nothing.

    ./tools/effort_nullspace.py --air data/bench_logs/bench/run_20260805_140048.csv \
        data/field_runs/run_20260901/run_20260901_112335.csv [more runs ...]
    ./tools/effort_nullspace.py --sensitivity
    ./tools/effort_nullspace.py --selftest

Stdlib only, same reason as wheel_forensics.py.

WHY THIS EXISTS. wheel_forensics.py's slip residual lives in VELOCITY space:
    s = FR + k*FL - k*RR - RL,   k = Ko/Ki
The firmware closes a velocity loop on every wheel, and the four targets it is
given are rigid-consistent by construction. So s is driven to zero by the PID
whether the wheels are slipping or not. It measures tracking error. It cannot
see a wheel that holds its commanded speed while the floor moves under it.

The same one spare dimension exists in EFFORT space, and there the loop does
not hide it. Motor torques map to a body wrench through J^T, where J is the
inverse-kinematics matrix. J^T has a one-dimensional null space, and it is the
same vector n = [1, k, -k, -1] (FR, FL, RR, RL). Torque along n pushes the
chassis nowhere: it is the wheels working against each other through the
floor. On a rigid chassis with no fight it is zero.

WHAT IT COMPUTES. Per motor, an air model pwm = Kff*w + Kstat*sgn(w), fitted
from a wheels-off-the-ground run. On a floor run, load = pwm - air_model(w) is
what the floor costs each motor, in PWM counts. That 4-vector is then split
into the three wrench directions (forward, strafe, yaw) and the null direction.

WHAT IT CANNOT DO. PWM is not torque: battery voltage moves the scale by a few
percent, and the air model comes from a different day. Treat anything under
about 1.5 counts as inside the floor. A motor's own rolling resistance and a
force passed through the chassis both show up as load, and this tool cannot
separate them. It says a fight exists. It does not say which wheel is wrong.
"""
import argparse
import csv
import math
import random
import statistics
import sys

WHEELS = ('FR', 'FL', 'RR', 'RL')
R_WHEEL, L1, L2, D_HALF = 0.0762, 0.403, 0.333, 0.15769
KO, KI = L1 + D_HALF, L2 + D_HALF
K = KO / KI
N = (1.0, K, -K, -1.0)
N_NORM = math.sqrt(sum(x * x for x in N))
PWM_SATURATED = 230
BLOCK = 20                      # samples per block for the standard error, ~1 s


def twist(w):
    """Commanded twist from four wheel speeds (FR, FL, RR, RL), no lateral scale."""
    vx = (R_WHEEL / 4) * (w[0] + w[1] + w[2] + w[3])
    vy = (R_WHEEL / 4) * (w[0] - w[1] - w[2] + w[3])
    wz = (R_WHEEL / 4) * (w[0] / KO - w[1] / KI + w[2] / KI - w[3] / KO)
    return vx, vy, wz


def split(load):
    """(forward, strafe, yaw, null) parts of a 4-vector of motor loads."""
    fwd = sum(load)
    strafe = load[0] - load[1] - load[2] + load[3]
    yaw = KO * load[0] - KI * load[1] + KI * load[2] - KO * load[3]
    null = sum(a * b for a, b in zip(N, load)) / N_NORM
    return fwd, strafe, yaw, null


def read(path):
    rows = []
    with open(path, newline='') as fh:
        for r in csv.DictReader(fh):
            try:
                rows.append((
                    tuple(float(r[f'{w}_target_rads']) for w in WHEELS),
                    tuple(float(r[f'{w}_actual_rads']) for w in WHEELS),
                    tuple(float(r[f'{w}_pwm']) for w in WHEELS)))
            except (KeyError, ValueError):
                continue
    return rows


def steady_mask(rows, hold=10):
    """True where the command has been constant for `hold` samples, every wheel
    is turning, tracking is inside 15 %, and nothing is saturated."""
    mask = []
    for i, (tgt, act, pwm) in enumerate(rows):
        ok = i >= hold
        if ok:
            ok = all(all(abs(tgt[j] - rows[i - h][0][j]) < 1e-6 for j in range(4))
                     for h in range(1, hold))
        ok = ok and all(abs(t) > 0.3 for t in tgt)
        ok = ok and all(abs(a - t) < 0.15 * abs(t) + 0.03 for a, t in zip(act, tgt))
        ok = ok and all(abs(p) < PWM_SATURATED for p in pwm)
        mask.append(ok)
    return mask


def fit_air(rows):
    """Least squares pwm = Kff*w + Kstat*sgn(w), per motor, on steady samples."""
    mask = steady_mask(rows)
    model = []
    for j in range(4):
        sxx = sx = n = sxy = sy = 0.0
        for (tgt, act, pwm), ok in zip(rows, mask):
            if not ok:
                continue
            x, s, y = act[j], math.copysign(1.0, act[j]), pwm[j]
            sxx += x * x; sx += x * s; n += 1; sxy += x * y; sy += s * y
        det = sxx * n - sx * sx
        if n < 50 or abs(det) < 1e-9:
            sys.exit(f'air fit failed for {WHEELS[j]}: {int(n)} steady samples')
        model.append(((sxy * n - sx * sy) / det, (sxx * sy - sx * sxy) / det))
    return model


def classify(tw):
    vx, vy, wz = tw
    rot = abs(wz) * 0.5         # rim speed of a point 0.5 m out, to compare with m/s
    if abs(vx) > 3 * abs(vy) and abs(vx) > 3 * rot:
        return 'forward' if vx > 0 else 'reverse'
    if abs(vy) > 3 * abs(vx) and abs(vy) > 3 * rot:
        return 'strafe+' if vy > 0 else 'strafe-'
    if rot > 3 * abs(vx) and rot > 3 * abs(vy):
        return 'rotate+' if wz > 0 else 'rotate-'
    return 'mixed'


def mean_se(vals):
    blocks = [vals[i:i + BLOCK] for i in range(0, len(vals) - BLOCK + 1, BLOCK)]
    means = [statistics.fmean(b) for b in blocks]
    m = statistics.fmean(vals)
    se = statistics.stdev(means) / math.sqrt(len(means)) if len(means) > 1 else float('nan')
    return m, se


def analyse(path, model):
    rows = read(path)
    mask = steady_mask(rows)
    groups = {}
    for (tgt, act, pwm), ok in zip(rows, mask):
        if not ok:
            continue
        load = tuple(pwm[j] - (model[j][0] * act[j] + model[j][1] * math.copysign(1.0, act[j]))
                     for j in range(4))
        groups.setdefault(classify(twist(tgt)), []).append((load, tgt))
    print(f'\n{path}\n  {sum(mask)} steady samples of {len(rows)}')
    print('  motion    n     m/s   load FR   FL    RR    RL   | yaw-effort   null  +- se')
    for name in ('forward', 'reverse', 'strafe+', 'strafe-', 'rotate+', 'rotate-', 'mixed'):
        g = groups.get(name, [])
        if len(g) < 2 * BLOCK:
            continue
        loads = [x[0] for x in g]
        mean_load = [statistics.fmean(l[j] for l in loads) for j in range(4)]
        speed = statistics.fmean(math.hypot(*twist(x[1])[:2]) for x in g)
        null, se = mean_se([split(l)[3] for l in loads])
        yaw = split(mean_load)[2]
        print(f'  {name:8s} {len(g):5d} {speed:6.3f}   '
              + ' '.join(f'{v:5.1f}' for v in mean_load)
              + f'  |   {yaw:6.2f}    {null:6.2f}  {se:5.2f}')


def creep_drift(l1, l2, eps, weights, d=D_HALF):
    """Yaw drift in deg per metre of straight-ahead driving, quasi-static creep
    model: each wheel pushes in proportion to its slip speed and its weight, so
    the body takes the weighted least-squares twist of the four rim speeds.
    eps = fractional radius error per wheel, weights = relative normal load."""
    ko, ki = l1 + d, l2 + d
    rows = ((1, 1, ko), (1, -1, -ki), (1, -1, ki), (1, 1, -ko))
    a = [[sum(w * r[i] * r[j] for w, r in zip(weights, rows)) for j in range(3)] for i in range(3)]
    b = [sum(w * r[i] * (1 + e) for w, r, e in zip(weights, rows, eps)) for i in range(3)]

    def det(m):
        return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
                - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))

    def swap(col):
        return [[b[i] if j == col else a[i][j] for j in range(3)] for i in range(3)]
    return math.degrees(det(swap(2)) / det(swap(0)))


def sensitivity():
    lm = (L1 + L2) / 2
    cases = (
        ('front pair 1 % larger than rear, even load', (.005, .005, -.005, -.005), (1, 1, 1, 1)),
        ('same, 70/30 load on the FR-RL diagonal',     (.005, .005, -.005, -.005), (.7, .3, .3, .7)),
        ('FR alone 1 % large, even load',              (.01, 0, 0, 0),             (1, 1, 1, 1)),
        ('right pair 1 % larger than left, even load', (.005, -.005, .005, -.005), (1, 1, 1, 1)),
    )
    print('yaw drift driving straight ahead, deg per metre (creep model, not a measurement)')
    print(f'  {"imperfection":46s} this chassis   symmetric')
    for label, eps, w in cases:
        print(f'  {label:46s} {creep_drift(L1, L2, eps, w):+9.3f}   {creep_drift(lm, lm, eps, w):+9.3f}')


def selftest():
    ok_all = True

    def check(ok, label):
        nonlocal ok_all
        ok_all &= bool(ok)
        print(('PASS  ' if ok else 'FAIL  ') + label)

    cols = ((1, 1, 1, 1), (1, -1, -1, 1), (KO, -KI, KI, -KO))
    check(all(abs(sum(a * b for a, b in zip(N, c))) < 1e-12 for c in cols),
          'null vector is orthogonal to forward, strafe and yaw wheel patterns')
    rng = random.Random(7)
    worst = 0.0
    for _ in range(5000):
        a, b, c = (rng.uniform(-5, 5) for _ in range(3))
        load = tuple(a * cols[0][j] + b * cols[1][j] + c * cols[2][j] for j in range(4))
        worst = max(worst, abs(split(load)[3]))
    check(worst < 1e-9, f'a load made only of body wrench has zero null part ({worst:.1e})')
    fight = tuple(2.5 * x / N_NORM for x in N)
    f, s, y, nl = split(fight)
    check(abs(nl - 2.5) < 1e-9 and max(abs(f), abs(s), abs(y)) < 1e-9,
          'a 2.5-count fight is recovered as 2.5 null and no wrench')
    rows = []
    for _ in range(40):
        w = tuple(rng.choice((-1, 1)) * rng.uniform(0.5, 2.0) for _ in range(4))
        for _ in range(30):
            rows.append((w, w, tuple(38.0 * x + 7.0 * math.copysign(1, x) + rng.gauss(0, 0.5)
                                     for x in w)))
    model = fit_air(rows)
    check(all(abs(kff - 38) < 0.3 and abs(ks - 7) < 0.3 for kff, ks in model),
          'air fit recovers Kff 38 and Kstat 7 from noisy synthetic data')
    lm = (L1 + L2) / 2
    fr = (.005, .005, -.005, -.005)
    check(abs(creep_drift(lm, lm, fr, (1, 1, 1, 1))) < 1e-9 and abs(creep_drift(L1, L2, fr, (1, 1, 1, 1))) > 0.02,
          'creep model: front-rear mismatch yaws this chassis and not a symmetric one')
    check(abs(creep_drift(L1, L2, (0, 0, 0, 0), (.7, .3, .4, .6))) < 1e-9,
          'creep model: perfect wheels drive straight whatever the load split')
    check(classify(twist((1, 1, 1, 1))) == 'forward' and classify(twist((1, -1, -1, 1))) == 'strafe+',
          'motion classes: all-equal is forward, FR/RL against FL/RR is strafe')
    return 0 if ok_all else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('runs', nargs='*', help='floor telemetry CSVs')
    ap.add_argument('--air', help='wheels-off-ground telemetry CSV for the motor model')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--sensitivity', action='store_true',
                    help='print the creep-model drift table and exit')
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    if args.sensitivity:
        sensitivity()
        return
    if not args.air or not args.runs:
        ap.error('need --air <csv> and at least one run')
    model = fit_air(read(args.air))
    print('air model  ' + '  '.join(f'{w}: Kff {m[0]:.2f} Kstat {m[1]:.2f}' for w, m in zip(WHEELS, model)))
    for path in [args.air] + args.runs:
        analyse(path, model)


if __name__ == '__main__':
    main()
