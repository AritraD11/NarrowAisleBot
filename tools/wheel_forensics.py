#!/usr/bin/env python3
"""wheel_forensics.py — everything the wheels know about where the robot went.

The encoders are the most trustworthy instrument on this robot. On 28 Aug
2026 (§17.42) wheel odometry closed an 18 m rotation-heavy drive to 0.229 m
— 1.27%, dead on its measured spec — while SLAM's corrected pose closed the
same drive to 0.477 m. When those two disagree, this tool exists to say what
the wheels actually reported, independently of the node that integrated them.

    ./tools/wheel_forensics.py run_20260828_152344_bundle.json
    ./tools/wheel_forensics.py ~/aislebot_logs/run_20260828_152344.csv
    ./tools/wheel_forensics.py <run> --csv out.csv     # every sample, flat
    ./tools/wheel_forensics.py --selftest

Stdlib only: it has to run on the Pi, which has no numpy.

═══════════════════════════════════════════════════════════════════════════
  WHAT IT COMPUTES THAT NOTHING ELSE DOES
═══════════════════════════════════════════════════════════════════════════

1. AN INDEPENDENT POSITION RECONSTRUCTION. odometry_publisher integrates the
   four wheel velocities live and publishes odom. This re-integrates the
   SAME recorded velocities with the SAME model, offline. If the two agree,
   odometry is faithfully reporting what the wheels said and the argument
   moves upstream to the wheels or downstream to SLAM. If they DISAGREE,
   something between the encoders and odom is wrong, and that is a different
   and much more serious problem. Nothing else in this repo checks that.

2. THE SLIP RESIDUAL — the part worth the tool.
   Four wheels drive three degrees of freedom, so the wheel-speed vector is
   over-determined by exactly one dimension. Any motion of a rigid,
   non-slipping base produces a wheel vector lying in the 3-D image of the
   inverse kinematics (mecanum_teleop_asymmetric.py:75-79). That image has a
   1-D orthogonal complement, derived here rather than guessed:

       slip = FR + (Ko/Ki)*FL - (Ko/Ki)*RR - RL          [rad/s]

   It is identically zero for ANY rigid twist — verified to 1e-14 over 20000
   random twists in --selftest — and non-zero only when at least one wheel is
   not tracking the body. A 15% slip on one wheel during a 0.2 m/s translation
   shows up as 0.45 rad/s.

   This is a DIRECT measurement of slip from encoders alone. It needs no
   ground truth, no LiDAR, and no map. On a mecanum base on uneven tile it is
   the number that says how much of the odometry error is physical.

3. WHERE THE THREE ESTIMATES DIVERGE, per second: wheels-only, recorded odom,
   and SLAM's map pose on one time axis.

WHAT IT CANNOT DO. It cannot tell you absolute truth. If a wheel slips
steadily and smoothly the residual catches it; if ALL FOUR slip identically
(a robot dragged sideways on ice) the wheel vector stays rigid-consistent and
nothing here will notice. Encoder scale errors are likewise invisible to the
residual — they need a tape measure. Say which of these you are relying on.
"""
import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

WHEELS = ('FR', 'FL', 'RR', 'RL')

# Geometry — odometry_publisher.py:92-95, mecanum_teleop_asymmetric.py.
# Defaults only: --geometry overrides them, and they should be checked with
# `ros2 param get /odometry_publisher <name>` against the live node, because
# a value in this repo is not a value on the robot.
R_WHEEL       = 0.0762
L1            = 0.403
L2            = 0.333
D_HALF        = 0.15769
LATERAL_SCALE = 0.92        # roller-scrub correction, §17.21
PWM_SATURATED = 230         # run_report.py's threshold


def geometry(r=R_WHEEL, l1=L1, l2=L2, d=D_HALF):
    ko, ki = l1 + d, l2 + d
    return {'r': r, 'Ko': ko, 'Ki': ki, 'slip_k': ko / ki}


def slip_residual(w, g):
    """FR + (Ko/Ki)*FL - (Ko/Ki)*RR - RL. Zero for any rigid-body motion."""
    k = g['slip_k']
    return w['FR'] + k * w['FL'] - k * w['RR'] - w['RL']


def body_twist(w, g, lateral_scale=LATERAL_SCALE):
    """Forward kinematics, odometry_publisher.py:216-231. REP-103 internally."""
    r = g['r']
    vx = (r / 4.0) * (w['FR'] + w['FL'] + w['RR'] + w['RL'])
    vy = (r / 4.0) * (w['FR'] - w['FL'] - w['RR'] + w['RL']) * lateral_scale
    wz = (r / 4.0) * (w['FR'] / g['Ko'] - w['FL'] / g['Ki']
                      + w['RR'] / g['Ki'] - w['RL'] / g['Ko'])
    return vx, vy, wz


def integrate(samples, g, lateral_scale=LATERAL_SCALE):
    """Re-integrate the recorded wheel velocities exactly as the live node
    does: midpoint rule, then the published-frame rotation of §17.38
    (pub_x = -y, pub_y = +x) so the output is directly comparable with the
    odom_x/odom_y columns in the pose CSV rather than to REP-103."""
    x = y = th = 0.0
    path = 0.0
    out = []
    prev_t = None
    for s in samples:
        t = s['t']
        if prev_t is None:
            prev_t = t
            out.append({'t': t, 'x': 0.0, 'y': 0.0, 'yaw_deg': 0.0,
                        'path_m': 0.0, 'vx': 0.0, 'vy': 0.0, 'wz': 0.0,
                        'slip': slip_residual(s['w'], g)})
            continue
        dt = t - prev_t
        prev_t = t
        # Same guard as the live node: a gap this large is a dropout, not motion.
        if dt <= 0.0 or dt > 1.0:
            continue
        vx, vy, wz = body_twist(s['w'], g, lateral_scale)
        half = wz * dt * 0.5
        c, sn = math.cos(th + half), math.sin(th + half)
        dx = (vx * c - vy * sn) * dt
        dy = (vx * sn + vy * c) * dt
        x += dx; y += dy; th += wz * dt
        th = math.atan2(math.sin(th), math.cos(th))
        path += math.hypot(dx, dy)
        out.append({'t': t,
                    'x': -y, 'y': x,                 # published-frame, §17.38
                    'yaw_deg': math.degrees(th),
                    'path_m': path,
                    'vx': vx, 'vy': vy, 'wz': wz,
                    'slip': slip_residual(s['w'], g)})
    return out


# ═════════════════════════════════════════════════════════════════════════
#  Loading
# ═════════════════════════════════════════════════════════════════════════
def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_rows(cols, rows):
    """columns + rows (bundle form) -> [{'t':.., 'w':{FR..}, 'pwm':{..}, 'tgt':{..}}]"""
    idx = {c: i for i, c in enumerate(cols)}
    tkey = 'pi_time_s' if 'pi_time_s' in idx else cols[0]
    out = []
    for r in rows:
        t = _f(r[idx[tkey]])
        if t is None:
            continue
        w, pwm, tgt = {}, {}, {}
        ok = True
        for name in WHEELS:
            a = idx.get(f'{name}_actual_rads')
            if a is None or _f(r[a]) is None:
                ok = False
                break
            w[name] = _f(r[a])
            p = idx.get(f'{name}_pwm')
            g = idx.get(f'{name}_target_rads')
            pwm[name] = _f(r[p]) if p is not None else None
            tgt[name] = _f(r[g]) if g is not None else None
        if ok:
            out.append({'t': t, 'w': w, 'pwm': pwm, 'tgt': tgt})
    return out


def load_pose(cols, rows):
    idx = {c: i for i, c in enumerate(cols)}
    out = []
    for r in rows:
        rec = {'t': _f(r[idx['epoch_s']])}
        for k in ('map_x', 'map_y', 'map_yaw_deg', 'odom_x', 'odom_y', 'odom_yaw_deg'):
            rec[k] = _f(r[idx[k]]) if k in idx else None
        if rec['t'] is not None:
            out.append(rec)
    return out


def load_any(target):
    """Accept a bundle .json, a telemetry .csv, or a run stem."""
    p = Path(target)
    if p.suffix == '.json':
        d = json.loads(p.read_text())
        tel = load_rows(d['telemetry']['columns'], d['telemetry']['rows'])
        pose = load_pose(d['pose']['columns'], d['pose']['rows']) if d.get('pose') else []
        return d.get('stamp', p.stem), tel, pose
    if p.suffix != '.csv':
        cand = [Path(str(p) + '.csv'), p.with_suffix('.csv')]
        p = next((c for c in cand if c.exists()), p)
    with open(p, newline='') as fh:
        rd = list(csv.reader(fh))
    tel = load_rows(rd[0], rd[1:])
    pose, pp = [], Path(str(p)[:-4] + '_pose.csv')
    if pp.exists():
        with open(pp, newline='') as fh:
            pr = list(csv.reader(fh))
        pose = load_pose(pr[0], pr[1:])
    return p.stem, tel, pose


# ═════════════════════════════════════════════════════════════════════════
#  Per-wheel health
# ═════════════════════════════════════════════════════════════════════════
def wheel_stats(tel, g):
    out = {}
    for name in WHEELS:
        errs, arc, absw, sat, mism, maxpwm = [], 0.0, [], 0, 0, 0.0
        prev_t = None
        for s in tel:
            a, t_, p = s['w'][name], s['tgt'][name], s['pwm'][name]
            absw.append(abs(a))
            if t_ is not None:
                errs.append(a - t_)
                # A commanded direction the wheel does not follow is an
                # odometry fault, not a SLAM one — worth separating.
                if abs(t_) > 0.05 and abs(a) > 0.05 and (t_ > 0) != (a > 0):
                    mism += 1
            if p is not None:
                maxpwm = max(maxpwm, abs(p))
                if abs(p) >= PWM_SATURATED:
                    sat += 1
            if prev_t is not None:
                dt = s['t'] - prev_t
                if 0 < dt <= 1.0:
                    arc += abs(a) * g['r'] * dt
            prev_t = s['t']
        n = max(len(tel), 1)
        out[name] = {
            'rms_err': (sum(e * e for e in errs) / len(errs)) ** 0.5 if errs else 0.0,
            'max_abs_err': max((abs(e) for e in errs), default=0.0),
            'sat_pct': 100.0 * sat / n,
            'sign_mismatch': mism,
            'max_pwm': maxpwm,
            'mean_abs_rads': statistics.fmean(absw) if absw else 0.0,
            'arc_m': arc,
        }
    return out


def slip_episodes(recon, thresh, min_gap=0.5):
    """Group consecutive over-threshold samples into episodes."""
    eps, cur = [], None
    for s in recon:
        if abs(s['slip']) >= thresh:
            if cur and s['t'] - cur['t_end'] <= min_gap:
                cur['t_end'] = s['t']
                cur['peak'] = max(cur['peak'], abs(s['slip']), key=abs) \
                    if False else max(cur['peak'], abs(s['slip']))
            else:
                if cur:
                    eps.append(cur)
                cur = {'t_start': s['t'], 't_end': s['t'], 'peak': abs(s['slip'])}
        # a quiet sample does not close the episode; the gap test above does
    if cur:
        eps.append(cur)
    return sorted(eps, key=lambda e: -e['peak'])


# ═════════════════════════════════════════════════════════════════════════
#  Comparison against what was actually published
# ═════════════════════════════════════════════════════════════════════════
def resample(series, t, key_t='t'):
    """Nearest sample at or before t. Linear scan is fine: both series are
    time-ordered and this is called once per second of run, not per sample."""
    best = None
    for s in series:
        if s[key_t] <= t:
            best = s
        else:
            break
    return best


def compare(recon, pose):
    """Wheels-only vs recorded odom vs SLAM map, on one time axis."""
    if not pose or not recon:
        return None
    t0 = recon[0]['t']
    # The recon starts at (0,0,0); odom may not, so difference against its
    # own first sample rather than assuming the run began at the origin.
    p0 = resample(pose, t0) or pose[0]
    if p0['odom_x'] is None:
        return None
    rows = []
    for s in recon:
        p = resample(pose, s['t'])
        if not p or p['odom_x'] is None:
            continue
        ox, oy = p['odom_x'] - p0['odom_x'], p['odom_y'] - p0['odom_y']
        rec = {'t_rel': s['t'] - t0,
               'wheel_x': s['x'], 'wheel_y': s['y'], 'wheel_yaw': s['yaw_deg'],
               'odom_x': ox, 'odom_y': oy,
               'odom_yaw': (p['odom_yaw_deg'] - (p0['odom_yaw_deg'] or 0.0))
                           if p['odom_yaw_deg'] is not None else None,
               'map_x': p['map_x'], 'map_y': p['map_y'], 'map_yaw': p['map_yaw_deg'],
               'd_wheel_odom': math.hypot(s['x'] - ox, s['y'] - oy)}
        rows.append(rec)
    return rows


# ═════════════════════════════════════════════════════════════════════════
#  Report
# ═════════════════════════════════════════════════════════════════════════
def report(stamp, tel, recon, pose, wstats, g, args):
    W = 72
    print()
    print('=' * W)
    print(f'  WHEEL FORENSICS   {stamp}')
    print('=' * W)
    dur = tel[-1]['t'] - tel[0]['t'] if len(tel) > 1 else 0.0
    hz = (len(tel) - 1) / dur if dur > 0 else 0.0
    print(f'  telemetry   {len(tel)} samples over {dur:.1f} s ({hz:.1f} Hz)')
    print(f'  geometry    r={g["r"]} Ko={g["Ko"]:.5f} Ki={g["Ki"]:.5f} '
          f'lateral_scale={args.lateral_scale}')
    print(f'              slip constant Ko/Ki = {g["slip_k"]:.6f}')

    # ── position from wheels alone ────────────────────────────────────
    print()
    print('-' * W)
    print('  POSITION FROM WHEEL ROTATION ALONE')
    print('-' * W)
    last = recon[-1]
    net = math.hypot(last['x'], last['y'])
    print(f'  path driven      {last["path_m"]:.3f} m')
    print(f'  net displacement {net:.3f} m   at ({last["x"]:+.3f}, {last["y"]:+.3f})')
    print(f'  net yaw          {last["yaw_deg"]:+.2f} deg')
    if last['path_m'] > 0.5:
        print(f'  closure          {net:.3f} m = {100*net/last["path_m"]:.2f}% of path')
        print('                   (only a closure if the robot physically ended '
              'where it started)')

    # ── slip ──────────────────────────────────────────────────────────
    slips = [abs(s['slip']) for s in recon]
    moving = [abs(s['slip']) for s in recon
              if max(abs(v) for v in (s['vx'], s['vy'], s['wz'])) > 0.01]
    print()
    print('-' * W)
    print('  SLIP RESIDUAL   FR + %.6f*FL - %.6f*RR - RL   [rad/s]'
          % (g['slip_k'], g['slip_k']))
    print('-' * W)
    print('  Zero for ANY rigid non-slipping motion. Non-zero means at least')
    print('  one wheel is not tracking the body.')
    if slips:
        srt = sorted(slips)
        p50 = srt[len(srt) // 2]
        p95 = srt[min(len(srt) - 1, int(0.95 * len(srt)))]
        print(f'  all samples      median {p50:.4f}   p95 {p95:.4f}   max {max(slips):.4f}')
        if moving:
            m = sorted(moving)
            print(f'  while moving     median {m[len(m)//2]:.4f}   '
                  f'p95 {m[min(len(m)-1, int(0.95*len(m)))]:.4f}   max {max(moving):.4f}')
        # In metres-per-second at the rim, which is easier to judge.
        print(f'  worst as rim speed  {max(slips) * g["r"]:.3f} m/s')
        eps = slip_episodes(recon, args.slip_thresh)
        print(f'\n  episodes over {args.slip_thresh} rad/s: {len(eps)}')
        for e in eps[:8]:
            print(f'    t+{e["t_start"] - recon[0]["t"]:7.1f} s  '
                  f'lasting {e["t_end"] - e["t_start"]:5.1f} s  peak {e["peak"]:.3f} rad/s')

    # ── per wheel ─────────────────────────────────────────────────────
    print()
    print('-' * W)
    print('  PER WHEEL')
    print('-' * W)
    print(f'  {"":<6}{"rms_err":>9}{"max_err":>9}{"sat%":>7}{"sign":>6}'
          f'{"max_pwm":>9}{"mean|w|":>9}{"arc_m":>8}')
    for name in WHEELS:
        d = wstats[name]
        print(f'  {name:<6}{d["rms_err"]:>9.3f}{d["max_abs_err"]:>9.3f}'
              f'{d["sat_pct"]:>7.1f}{d["sign_mismatch"]:>6}{d["max_pwm"]:>9.0f}'
              f'{d["mean_abs_rads"]:>9.3f}{d["arc_m"]:>8.2f}')
    arcs = [wstats[w]['arc_m'] for w in WHEELS]
    if min(arcs) > 0:
        lo = min(WHEELS, key=lambda w: wstats[w]['arc_m'])
        hi = max(WHEELS, key=lambda w: wstats[w]['arc_m'])
        print(f'\n  travel spread  {min(arcs):.2f} m ({lo}) .. {max(arcs):.2f} m ({hi}), '
              f'ratio {max(arcs)/min(arcs):.2f}')
    # The diagonal pairs contribute oppositely to yaw, so an imbalance here
    # biases heading every time the robot turns — the dominant error on a
    # corner-heavy drive (§17.42: 10.53 deg over 18 m).
    d1 = wstats['FR']['arc_m'] + wstats['RL']['arc_m']
    d2 = wstats['FL']['arc_m'] + wstats['RR']['arc_m']
    if min(d1, d2) > 0:
        print(f'  diagonal pairs FR+RL {d1:.2f} m vs FL+RR {d2:.2f} m  '
              f'-> {100*(d1-d2)/max(d1, d2):+.1f}%  (biases yaw when non-zero)')

    # ── three estimates ───────────────────────────────────────────────
    cmp = compare(recon, pose)
    print()
    print('-' * W)
    print('  WHEELS vs RECORDED ODOM vs SLAM')
    print('-' * W)
    if not cmp:
        print('  no pose CSV alongside this run — wheels-only above is all there is.')
    else:
        dv = [c['d_wheel_odom'] for c in cmp]
        print(f'  wheels vs odom   max divergence {max(dv):.4f} m, '
              f'final {dv[-1]:.4f} m')
        if max(dv) < 0.02:
            print('    -> odometry_publisher is faithfully integrating what the')
            print('       wheels reported. Any error is upstream (slip, scale) or')
            print('       downstream (SLAM), not in the integration.')
        else:
            print('    -> DISAGREEMENT. The live node did not integrate these same')
            print('       velocities to this same answer. Check wheel_radius, l1, l2,')
            print('       d and lateral_scale on the LIVE node with ros2 param get')
            print('       before trusting either estimate.')
        f = cmp[-1]
        print(f'\n  {"":<10}{"x":>10}{"y":>10}{"|pos|":>10}{"yaw deg":>10}')
        print(f'  {"wheels":<10}{f["wheel_x"]:>10.3f}{f["wheel_y"]:>10.3f}'
              f'{math.hypot(f["wheel_x"], f["wheel_y"]):>10.3f}{f["wheel_yaw"]:>10.2f}')
        print(f'  {"odom":<10}{f["odom_x"]:>10.3f}{f["odom_y"]:>10.3f}'
              f'{math.hypot(f["odom_x"], f["odom_y"]):>10.3f}'
              f'{(f["odom_yaw"] if f["odom_yaw"] is not None else float("nan")):>10.2f}')
        if f['map_x'] is not None:
            print(f'  {"SLAM map":<10}{f["map_x"]:>10.3f}{f["map_y"]:>10.3f}'
                  f'{math.hypot(f["map_x"], f["map_y"]):>10.3f}'
                  f'{(f["map_yaw"] if f["map_yaw"] is not None else float("nan")):>10.2f}')
            print('\n  If the robot physically ended on the zero mark, every row above')
            print('  should read ~0 and the ones that do not are that estimate\'s error.')
    print()
    return cmp


# ═════════════════════════════════════════════════════════════════════════
#  Flat export — every sample, one row, for a spreadsheet
# ═════════════════════════════════════════════════════════════════════════
def write_csv(path, tel, recon, cmp_rows):
    by_t = {round(c['t_rel'], 3): c for c in (cmp_rows or [])}
    t0 = recon[0]['t']
    hdr = ['t_rel_s']
    for w in WHEELS:
        hdr += [f'{w}_target_rads', f'{w}_actual_rads', f'{w}_err_rads', f'{w}_pwm']
    hdr += ['slip_rads', 'vx_mps', 'vy_mps', 'wz_radps',
            'wheel_x', 'wheel_y', 'wheel_yaw_deg', 'wheel_path_m',
            'odom_x', 'odom_y', 'odom_yaw_deg', 'map_x', 'map_y', 'map_yaw_deg',
            'wheel_minus_odom_m']
    tel_by_t = {round(s['t'], 4): s for s in tel}
    n = 0
    with open(path, 'w', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(hdr)
        for s in recon:
            src = tel_by_t.get(round(s['t'], 4))
            row = [f'{s["t"] - t0:.4f}']
            for w in WHEELS:
                if src:
                    tg, ac, pw = src['tgt'][w], src['w'][w], src['pwm'][w]
                    row += ['' if tg is None else f'{tg:.4f}', f'{ac:.4f}',
                            '' if tg is None else f'{ac - tg:.4f}',
                            '' if pw is None else f'{pw:.1f}']
                else:
                    row += ['', '', '', '']
            row += [f'{s["slip"]:.5f}', f'{s["vx"]:.5f}', f'{s["vy"]:.5f}',
                    f'{s["wz"]:.5f}', f'{s["x"]:.5f}', f'{s["y"]:.5f}',
                    f'{s["yaw_deg"]:.3f}', f'{s["path_m"]:.5f}']
            c = by_t.get(round(s['t'] - t0, 3))
            for k in ('odom_x', 'odom_y', 'odom_yaw', 'map_x', 'map_y', 'map_yaw',
                      'd_wheel_odom'):
                v = c.get(k) if c else None
                row.append('' if v is None else f'{v:.5f}')
            wr.writerow(row)
            n += 1
    print(f'  wrote {path}  ({n} rows x {len(hdr)} columns)')


# ═════════════════════════════════════════════════════════════════════════
#  Self-test
# ═════════════════════════════════════════════════════════════════════════
def selftest():
    import random
    g = geometry()
    fails = 0

    def check(ok, label, detail=''):
        nonlocal fails
        if not ok:
            fails += 1
        print(f'  {"ok  " if ok else "FAIL"}  {label}{("  " + detail) if detail else ""}')

    # 1. the slip residual must vanish for every rigid twist
    random.seed(11)
    worst = 0.0
    inv_r = 1.0 / g['r']
    for _ in range(20000):
        vx, vy, wz = (random.uniform(-0.6, 0.6) for _ in range(3))
        w = {'FR': inv_r * (vx + vy + g['Ko'] * wz),
             'FL': inv_r * (vx - vy - g['Ki'] * wz),
             'RR': inv_r * (vx - vy + g['Ki'] * wz),
             'RL': inv_r * (vx + vy - g['Ko'] * wz)}
        worst = max(worst, abs(slip_residual(w, g)))
    check(worst < 1e-9, 'slip residual is zero for 20000 rigid twists',
          f'worst {worst:.2e}')

    # 2. and must NOT vanish when a wheel slips
    w = {'FR': inv_r * 0.2, 'FL': inv_r * 0.2, 'RR': inv_r * 0.2, 'RL': inv_r * 0.2}
    w['FL'] *= 0.85
    check(abs(slip_residual(w, g)) > 0.3, 'a 15% wheel slip is detected',
          f'{abs(slip_residual(w, g)):.3f} rad/s')

    # 3. forward kinematics must invert the teleop's inverse exactly
    worst = 0.0
    for _ in range(2000):
        vx, vy, wz = (random.uniform(-0.5, 0.5) for _ in range(3))
        w = {'FR': inv_r * (vx + vy + g['Ko'] * wz),
             'FL': inv_r * (vx - vy - g['Ki'] * wz),
             'RR': inv_r * (vx - vy + g['Ki'] * wz),
             'RL': inv_r * (vx + vy - g['Ko'] * wz)}
        gvx, gvy, gwz = body_twist(w, g, lateral_scale=1.0)
        worst = max(worst, abs(gvx - vx), abs(gvy - vy), abs(gwz - wz))
    check(worst < 1e-9, 'forward kinematics inverts teleop exactly',
          f'worst {worst:.2e}')

    # 4. a straight 1 m forward drive must integrate to +1 m on published Y
    #    (published +Y = forward since §17.38), and 0 on X.
    v, dur, hz = 0.2, 5.0, 20.0
    samples = []
    for i in range(int(dur * hz) + 1):
        w = {k: inv_r * v for k in WHEELS}
        samples.append({'t': i / hz, 'w': w})
    rec = integrate(samples, g)[-1]
    check(abs(rec['y'] - 1.0) < 1e-6 and abs(rec['x']) < 1e-9,
          'a 1 m forward drive integrates to published (0, +1)',
          f'({rec["x"]:+.6f}, {rec["y"]:+.6f})')

    # 5. a pure right strafe must land on published +X, scaled by lateral_scale
    samples = []
    for i in range(int(dur * hz) + 1):
        # vy is LEFT in REP-103, so a right strafe is negative vy
        w = {'FR': -inv_r * v, 'FL': inv_r * v, 'RR': inv_r * v, 'RL': -inv_r * v}
        samples.append({'t': i / hz, 'w': w})
    rec = integrate(samples, g)[-1]
    check(abs(rec['x'] - LATERAL_SCALE) < 1e-6 and abs(rec['y']) < 1e-9,
          'a 1 m right strafe integrates to published (+lateral_scale, 0)',
          f'({rec["x"]:+.6f}, {rec["y"]:+.6f})')

    # 6. the dt guard must skip a dropout rather than integrating across it
    samples = [{'t': 0.0, 'w': {k: inv_r * v for k in WHEELS}},
               {'t': 5.0, 'w': {k: inv_r * v for k in WHEELS}}]
    rec = integrate(samples, geometry())[-1]
    check(rec['path_m'] == 0.0, 'a >1 s gap is skipped, not integrated across',
          f'path {rec["path_m"]:.4f} m')

    print(f'\nselftest: {"PASS" if not fails else str(fails) + " FAILURE(S)"}')
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('target', nargs='?',
                    help='run bundle .json, telemetry .csv, or run stem')
    ap.add_argument('--csv', help='write every sample to this flat CSV')
    ap.add_argument('--json', help='write the summary as JSON')
    ap.add_argument('--lateral-scale', type=float, default=LATERAL_SCALE,
                    dest='lateral_scale',
                    help=f'roller-scrub correction (default {LATERAL_SCALE}); '
                         'verify against the live node, not this default')
    ap.add_argument('--geometry', help='r,l1,l2,d  override, comma separated')
    ap.add_argument('--slip-thresh', type=float, default=0.5, dest='slip_thresh',
                    help='slip residual (rad/s) counted as an episode (default 0.5)')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.target:
        ap.error('give a run to analyse, or --selftest')

    g = geometry(*[float(x) for x in args.geometry.split(',')]) if args.geometry \
        else geometry()
    stamp, tel, pose = load_any(args.target)
    if len(tel) < 2:
        sys.exit(f'no usable telemetry rows in {args.target}')
    recon = integrate(tel, g, args.lateral_scale)
    wstats = wheel_stats(tel, g)
    cmp_rows = report(stamp, tel, recon, pose, wstats, g, args)
    if args.csv:
        write_csv(args.csv, tel, recon, cmp_rows)
    if args.json:
        last = recon[-1]
        Path(args.json).write_text(json.dumps({
            'stamp': stamp, 'samples': len(tel),
            'wheels_only': {'path_m': last['path_m'], 'x': last['x'], 'y': last['y'],
                            'yaw_deg': last['yaw_deg']},
            'slip': {'max': max(abs(s['slip']) for s in recon),
                     'thresh': args.slip_thresh,
                     'episodes': len(slip_episodes(recon, args.slip_thresh))},
            'per_wheel': wstats,
        }, indent=2))
        print(f'  wrote {args.json}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
