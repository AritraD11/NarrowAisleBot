#!/usr/bin/env python3
"""run_analyzer.py — one report for one drive: map, odometry, and where they disagree.

Every artefact a mapping run produces, read together instead of one at a time:

    run_<stamp>.pgm / .yaml    the map
    run_<stamp>_pose.csv       where SLAM thought it was, where the WHEELS
                               thought it was, and the correction between them
    run_<stamp>.csv            13-column per-wheel telemetry
    run_<stamp>_report.json    duration and sample counts

The point is the cross-checks, not the summaries. Three independent
instruments watched the same drive, and they can be asked whether they agree:

  * Wheel odometry is smooth by construction — it integrates encoder ticks and
    has no opinion about the world. It drifts, but it CANNOT jump. So when the
    map->odom correction moves while odom does not, the pose graph moved and
    the robot did not. §17.32 established that with a rosbag and a one-off
    tool; the dashboard now logs the same quantity on every run, so this is
    just reading it.

  * A false loop closure leaves TWO marks: a correction at the moment it
    fires, and a doubled wall at the place it fired. `map_integrity.py` finds
    the second. This finds the first. When both land within a metre of each
    other, that is two instruments agreeing, which is the strongest evidence
    this project has been able to produce about any closure.

  * A wheel that slipped corrupts odometry, which corrupts the scan matcher's
    starting guess. So a correction that coincides with wheel saturation or a
    commanded/actual sign mismatch is odometry's fault, not SLAM's, and the
    fix is mechanical rather than a parameter.

Usage — the stamp is enough, the rest is found alongside it:

    ./tools/run_analyzer.py ~/aislebot_logs/run_20260826_143000
    ./tools/run_analyzer.py run_20260826_143000 --png run.png
    ./tools/run_analyzer.py run_20260826_143000 --json run.json
    ./tools/run_analyzer.py --selftest

Pure standard library. `map_integrity.py` is imported if it sits next to this
file or next to the run; without it every other section still runs.
"""
import argparse
import csv
import importlib.util
import json
import math
import statistics
import struct
import sys
import zlib
from pathlib import Path

WHEELS = ('FR', 'FL', 'RR', 'RL')
WHEEL_RADIUS_M = 0.0762          # odometry_publisher's declared default
PWM_SATURATED = 245              # of 255
SIGN_MISMATCH_MIN_RADS = 0.5     # below this, noise flips sign harmlessly

DEF_CORR_JUMP_M = 0.05           # per-sample correction that counts as a jump
DEF_EVENT_GAP_S = 0.5            # samples closer than this are one event
DEF_COINCIDE_M = 1.0             # jump<->doubled-wall agreement radius
DEF_COINCIDE_S = 1.0             # jump<->wheel-anomaly agreement window


# ═════════════════════════════════════════════════════════════════════════
#  Loading
# ═════════════════════════════════════════════════════════════════════════
def find_map_integrity(hint_dirs):
    """map_integrity.py lives next to this file in the repo, but on the Pi it
    is usually dropped into the log folder instead. Look in both rather than
    making the caller care."""
    for d in hint_dirs:
        cand = Path(d) / 'map_integrity.py'
        if cand.is_file():
            spec = importlib.util.spec_from_file_location('map_integrity', cand)
            mod = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(mod)
                return mod, str(cand)
            except Exception as exc:
                print(f'  !! found {cand} but could not load it: {exc}', file=sys.stderr)
    return None, None


def read_csv_dicts(path):
    with open(path, newline='') as fh:
        return list(csv.DictReader(fh))


def _f(row, key):
    v = row.get(key, '')
    if v is None or v == '':
        return None
    try:
        return float(v)
    except ValueError:
        return None


def load_pose(path):
    """Parse the pose CSV by HEADER NAME, not column position.

    Runs recorded before 26 Aug have only `epoch_s, map_x, map_y, yaw_deg` —
    SLAM pose and nothing else. Those still load; the sections that need
    odometry say so instead of inventing it.
    """
    rows = read_csv_dicts(path)
    if not rows:
        return [], False
    yaw_key = 'map_yaw_deg' if 'map_yaw_deg' in rows[0] else 'yaw_deg'
    has_odom = 'odom_x' in rows[0]
    out = []
    for r in rows:
        t = _f(r, 'epoch_s')
        if t is None:
            continue
        out.append({
            't': t,
            'mx': _f(r, 'map_x'), 'my': _f(r, 'map_y'), 'myaw': _f(r, yaw_key),
            'ox': _f(r, 'odom_x'), 'oy': _f(r, 'odom_y'), 'oyaw': _f(r, 'odom_yaw_deg'),
            'cx': _f(r, 'corr_x'), 'cy': _f(r, 'corr_y'), 'cyaw': _f(r, 'corr_yaw_deg'),
        })
    out.sort(key=lambda r: r['t'])
    return out, has_odom


def load_telemetry(path):
    rows = read_csv_dicts(path)
    out = []
    for r in rows:
        t = _f(r, 'pi_time_s')
        if t is None:
            continue
        rec = {'t': t}
        for w in WHEELS:
            rec[w] = (_f(r, f'{w}_target_rads'), _f(r, f'{w}_actual_rads'),
                      _f(r, f'{w}_pwm'))
        out.append(rec)
    out.sort(key=lambda r: r['t'])
    return out


def load_run(base):
    """`base` may be a stamp, a stem, or any one of the run's files."""
    base = Path(base)
    if base.suffix in ('.pgm', '.yaml', '.csv', '.json'):
        stem = base.stem
        for suf in ('_pose', '_report'):
            if stem.endswith(suf):
                stem = stem[:-len(suf)]
        base = base.with_name(stem)
    folder = base.parent if str(base.parent) != '' else Path('.')
    stamp = base.name
    art = {
        'stamp': stamp, 'folder': folder,
        'pgm': folder / f'{stamp}.pgm',
        'yaml': folder / f'{stamp}.yaml',
        'pose': folder / f'{stamp}_pose.csv',
        'telem': folder / f'{stamp}.csv',
        'report': folder / f'{stamp}_report.json',
    }
    art['present'] = {k: v.is_file() for k, v in art.items()
                      if isinstance(v, Path) and k != 'folder'}
    return art


# ═════════════════════════════════════════════════════════════════════════
#  Trajectory and corrections
# ═════════════════════════════════════════════════════════════════════════
def _ang_diff(a, b):
    """Smallest signed difference between two angles in degrees."""
    if a is None or b is None:
        return None
    return (a - b + 180.0) % 360.0 - 180.0


def analyse_pose(rows, has_odom, corr_jump_m=DEF_CORR_JUMP_M,
                 event_gap_s=DEF_EVENT_GAP_S):
    if len(rows) < 2:
        return {'samples': len(rows), 'error': 'not enough pose samples to read'}

    t0, t1 = rows[0]['t'], rows[-1]['t']
    out = {'samples': len(rows), 'duration_s': round(t1 - t0, 1),
           'rate_hz': round((len(rows) - 1) / max(t1 - t0, 1e-6), 1),
           'has_odom': has_odom}

    def path_len(kx, ky):
        tot, n = 0.0, 0
        for a, b in zip(rows, rows[1:]):
            if None in (a[kx], a[ky], b[kx], b[ky]):
                continue
            tot += math.dist((a[kx], a[ky]), (b[kx], b[ky]))
            n += 1
        return tot, n

    map_len, _ = path_len('mx', 'my')
    out['map_path_m'] = round(map_len, 2)

    last_map = next((r for r in reversed(rows) if r['mx'] is not None), None)
    first_map = next((r for r in rows if r['mx'] is not None), None)
    if last_map:
        out['final_map_xy'] = [round(last_map['mx'], 3), round(last_map['my'], 3)]
        out['return_to_mark_m'] = round(math.hypot(last_map['mx'], last_map['my']), 3)
        out['final_map_yaw_deg'] = round(last_map['myaw'], 2) if last_map['myaw'] is not None else None
        if first_map and first_map['myaw'] is not None and last_map['myaw'] is not None:
            out['yaw_closure_deg'] = round(_ang_diff(last_map['myaw'], first_map['myaw']), 2)

    if not has_odom:
        out['note'] = ('this run predates odometry logging, so the correction '
                       'cannot be separated from the motion — only the SLAM '
                       'path is available')
        return out

    odom_len, _ = path_len('ox', 'oy')
    out['odom_path_m'] = round(odom_len, 2)
    last_od = next((r for r in reversed(rows) if r['ox'] is not None), None)
    if last_od:
        # If the robot physically returned to the mark, this IS the wheels'
        # accumulated drift over the whole run — a number this project has
        # never had separately from SLAM's correction of it.
        out['odom_closure_m'] = round(math.hypot(last_od['ox'], last_od['oy']), 3)
    last_c = next((r for r in reversed(rows) if r['cx'] is not None), None)
    if last_c:
        out['final_correction_m'] = round(math.hypot(last_c['cx'], last_c['cy']), 3)
        out['final_correction_yaw_deg'] = round(last_c['cyaw'], 2) if last_c['cyaw'] is not None else None

    # ── per-sample steps ────────────────────────────────────────────────
    steps = []
    for a, b in zip(rows, rows[1:]):
        if None in (a['cx'], a['cy'], b['cx'], b['cy']):
            continue
        d_corr = math.dist((a['cx'], a['cy']), (b['cx'], b['cy']))
        d_odom = (math.dist((a['ox'], a['oy']), (b['ox'], b['oy']))
                  if None not in (a['ox'], a['oy'], b['ox'], b['oy']) else None)
        d_map = (math.dist((a['mx'], a['my']), (b['mx'], b['my']))
                 if None not in (a['mx'], a['my'], b['mx'], b['my']) else None)
        steps.append({'t': b['t'], 'corr': d_corr, 'odom': d_odom, 'map': d_map,
                      'cyaw': _ang_diff(b['cyaw'], a['cyaw']),
                      'x': b['mx'], 'y': b['my']})
    if not steps:
        out['note'] = 'no correction samples — was SLAM running?'
        return out

    cvals = [s['corr'] for s in steps]
    ovals = [s['odom'] for s in steps if s['odom'] is not None]
    out['correction_step'] = {
        'median_m': round(statistics.median(cvals), 4),
        'p95_m': round(sorted(cvals)[min(len(cvals) - 1, int(0.95 * len(cvals)))], 4),
        'max_m': round(max(cvals), 4),
        'total_m': round(sum(cvals), 2),
    }
    odom_median = statistics.median(ovals) if ovals else None
    out['odom_step_median_m'] = round(odom_median, 4) if odom_median is not None else None

    # ── group jumps into events ─────────────────────────────────────────
    events, cur = [], None
    for s in steps:
        if s['corr'] < corr_jump_m:
            cur = None
            continue
        if cur is not None and s['t'] - cur['t_end'] <= event_gap_s:
            cur['t_end'] = s['t']
            cur['corr_m'] += s['corr']
            cur['samples'] += 1
            if s['odom'] is not None:
                cur['odom_m'] += s['odom']
            cur['peak_m'] = max(cur['peak_m'], s['corr'])
            cur['yaw_deg'] += s['cyaw'] or 0.0
            if s['x'] is not None:
                cur['x'], cur['y'] = s['x'], s['y']
        else:
            cur = {'t_start': s['t'], 't_end': s['t'], 'corr_m': s['corr'],
                   'odom_m': s['odom'] or 0.0, 'peak_m': s['corr'], 'samples': 1,
                   'yaw_deg': s['cyaw'] or 0.0, 'x': s['x'], 'y': s['y']}
            events.append(cur)

    for e in events:
        e['t_rel'] = round(e['t_start'] - t0, 1)
        e['corr_m'] = round(e['corr_m'], 3)
        e['odom_m'] = round(e['odom_m'], 3)
        e['peak_m'] = round(e['peak_m'], 3)
        e['yaw_deg'] = round(e['yaw_deg'], 2)
        e['map_x'] = round(e['x'], 2) if e['x'] is not None else None
        e['map_y'] = round(e['y'], 2) if e['y'] is not None else None
        # The discriminator. Wheel odometry cannot jump, so if it moved a
        # normal amount while the correction moved a lot, the robot did not
        # go anywhere unusual and the pose graph did.
        expected = (odom_median or 0.0) * e['samples']
        e['odom_normal'] = bool(odom_median is None or
                                e['odom_m'] <= max(3.0 * expected, 0.02))
        e['verdict'] = ('pose graph moved, robot did not' if e['odom_normal']
                        else 'odom moved too — robot was actually driving hard here')
        for k in ('t_start', 't_end', 'x', 'y'):
            e.pop(k, None)

    events.sort(key=lambda e: -e['corr_m'])
    out['jump_events'] = events
    out['jump_count'] = len(events)
    return out


# ═════════════════════════════════════════════════════════════════════════
#  Wheels
#
#  Deliberately per-wheel health only. Turning four wheel speeds into a
#  chassis position is the odometry node's job, it already does it, and the
#  pose CSV now records the result — re-deriving it here against a guessed
#  sign convention would only add a second thing to doubt.
# ═════════════════════════════════════════════════════════════════════════
def analyse_wheels(rows):
    if len(rows) < 2:
        return {'samples': len(rows), 'error': 'not enough telemetry to read'}
    t0, t1 = rows[0]['t'], rows[-1]['t']
    out = {'samples': len(rows), 'duration_s': round(t1 - t0, 1),
           'rate_hz': round((len(rows) - 1) / max(t1 - t0, 1e-6), 1), 'wheels': {}}

    anomalies = []
    for w in WHEELS:
        errs, sat, mism, arc, absv, maxpwm = [], 0, 0, 0.0, [], 0.0
        prev_t = None
        for r in rows:
            tgt, act, pwm = r[w]
            if act is None:
                continue
            if tgt is not None:
                errs.append(abs(tgt - act))
                if (tgt * act < 0 and abs(tgt) > SIGN_MISMATCH_MIN_RADS
                        and abs(act) > SIGN_MISMATCH_MIN_RADS):
                    mism += 1
                    anomalies.append({'t': r['t'], 'wheel': w, 'kind': 'sign'})
            if pwm is not None:
                maxpwm = max(maxpwm, abs(pwm))
                if abs(pwm) >= PWM_SATURATED:
                    sat += 1
                    anomalies.append({'t': r['t'], 'wheel': w, 'kind': 'saturated'})
            absv.append(abs(act))
            if prev_t is not None:
                arc += abs(act) * (r['t'] - prev_t) * WHEEL_RADIUS_M
            prev_t = r['t']
        n = max(len(absv), 1)
        out['wheels'][w] = {
            'rms_error_rads': round(math.sqrt(sum(e * e for e in errs) / len(errs)), 3) if errs else None,
            'saturated_pct': round(100.0 * sat / n, 1),
            'sign_mismatch_pct': round(100.0 * mism / n, 1),
            'max_abs_pwm': round(maxpwm, 0),
            'mean_abs_rads': round(sum(absv) / n, 3),
            'arc_m': round(arc, 2),
        }

    arcs = {w: out['wheels'][w]['arc_m'] for w in WHEELS}
    lo, hi = min(arcs.values()), max(arcs.values())
    out['arc_spread'] = {
        'min_m': lo, 'max_m': hi,
        'ratio': round(hi / lo, 2) if lo > 0.01 else None,
        'least': min(arcs, key=arcs.get), 'most': max(arcs, key=arcs.get),
    }
    anomalies.sort(key=lambda a: a['t'])
    out['anomalies'] = anomalies
    out['anomaly_count'] = len(anomalies)
    return out


# ═════════════════════════════════════════════════════════════════════════
#  Cross-checks — the reason all of this is in one tool
# ═════════════════════════════════════════════════════════════════════════
def cross_check(pose, wheels, mapres, coincide_m=DEF_COINCIDE_M,
                coincide_s=DEF_COINCIDE_S):
    out = {'jump_vs_map': [], 'jump_vs_wheels': [], 'notes': []}
    events = pose.get('jump_events') or []
    if not events:
        return out

    clusters = (mapres or {}).get('doubled_clusters') or []
    for e in events:
        if e['map_x'] is None or not clusters:
            continue
        best, bd = None, None
        for c in clusters:
            d = math.dist((e['map_x'], e['map_y']), (c['map_x'], c['map_y']))
            if bd is None or d < bd:
                best, bd = c, d
        if bd is not None and bd <= coincide_m:
            out['jump_vs_map'].append({
                't_rel': e['t_rel'], 'corr_m': e['corr_m'],
                'map_x': e['map_x'], 'map_y': e['map_y'],
                'cluster_gap_m': best['gap_m'], 'cluster_cells': best['cells'],
                'distance_m': round(bd, 2)})

    anomalies = (wheels or {}).get('anomalies') or []
    if anomalies and pose.get('duration_s'):
        # jump times are relative; anomaly times are epoch. Rebase.
        t0 = anomalies[0]['t'] - 0  # placeholder, corrected by caller-supplied base
    for e in events:
        hits = [a for a in anomalies
                if abs(a.get('t_rel', 1e9) - e['t_rel']) <= coincide_s]
        if hits:
            kinds = sorted({h['kind'] for h in hits})
            whs = sorted({h['wheel'] for h in hits})
            out['jump_vs_wheels'].append({
                't_rel': e['t_rel'], 'corr_m': e['corr_m'],
                'wheels': whs, 'kinds': kinds, 'n': len(hits)})

    if out['jump_vs_map']:
        out['notes'].append(
            f"{len(out['jump_vs_map'])} correction(s) happened within "
            f"{coincide_m} m of a doubled wall — two instruments pointing at "
            f"the same place, which is the strongest false-closure evidence "
            f"available here")
    if out['jump_vs_wheels']:
        out['notes'].append(
            f"{len(out['jump_vs_wheels'])} correction(s) coincided with wheel "
            f"saturation or a sign mismatch — suspect a slip corrupting "
            f"odometry rather than a bad scan match")
    graph_only = [e for e in events if e['odom_normal']]
    if graph_only:
        out['notes'].append(
            f"{len(graph_only)} of {len(events)} correction(s) happened while "
            f"wheel odometry stepped normally: the pose graph moved, the robot "
            f"did not (§17.32's Stage A conclusion, per event)")
    return out


# ═════════════════════════════════════════════════════════════════════════
#  Annotated PNG — map, both paths, and where the corrections happened
# ═════════════════════════════════════════════════════════════════════════
PAL = {0: (248, 250, 252), 1: (10, 14, 23), 2: (26, 35, 50)}
C_DOUBLED = (220, 38, 38)
C_SLAM = (37, 99, 235)
C_ODOM = (16, 185, 129)
C_JUMP = (250, 204, 21)


def _line(px, w, h, x0, y0, x1, y1, rgb):
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx - dy
    while True:
        if 0 <= x0 < w and 0 <= y0 < h:
            px[y0 * w + x0] = rgb
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def write_png(path, grid, doubled, pose_rows, events, scale=4):
    w, h = grid.w, grid.h
    px = [PAL[grid.cls[i]] for i in range(w * h)]
    for i in doubled:
        px[i] = C_DOUBLED

    def to_px(x, y):
        return (int(round((x - grid.ox) / grid.res)),
                int(round((h - 1) - (y - grid.oy) / grid.res)))

    for kx, ky, rgb in (('ox', 'oy', C_ODOM), ('mx', 'my', C_SLAM)):
        prev = None
        for r in pose_rows:
            if r[kx] is None:
                prev = None
                continue
            cur = to_px(r[kx], r[ky])
            if prev:
                _line(px, w, h, prev[0], prev[1], cur[0], cur[1], rgb)
            prev = cur

    for e in events:                      # a cross where each correction fired
        if e['map_x'] is None:
            continue
        cx, cy = to_px(e['map_x'], e['map_y'])
        for d in range(-3, 4):
            for a, b in ((cx + d, cy), (cx, cy + d)):
                if 0 <= a < w and 0 <= b < h:
                    px[b * w + a] = C_JUMP

    rows = []
    for r in range(h):
        row = bytearray()
        for c in range(w):
            row += bytes(px[r * w + c]) * scale
        rows.extend([bytes(row)] * scale)
    raw = b''.join(b'\x00' + r for r in rows)

    def chunk(tag, data):
        body = tag + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body) & 0xffffffff)

    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', w * scale, h * scale, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))
    Path(path).write_bytes(png)
    return len(png)


# ═════════════════════════════════════════════════════════════════════════
#  Report
# ═════════════════════════════════════════════════════════════════════════
def print_report(res):
    a = res['artefacts']
    print(f"\n{'=' * 72}\n  RUN {res['stamp']}\n{'=' * 72}")
    print('  files      ' + '  '.join(
        f"{'OK ' if v else '-- '}{k}" for k, v in a.items()))

    m = res.get('map')
    print(f"\n{'-' * 72}\n  MAP\n{'-' * 72}")
    if not m:
        print('  no map analysed (missing .pgm, or map_integrity.py not found)')
    elif 'error' in m:
        print(f"  {m['error']}")
    else:
        print(f"  verdict    {m['verdict']}")
        print(f"  extent     {m['extent_m']} m, {m['occupied']} occupied cells "
              f"= {m['wall_m']} m of wall")
        print(f"  doubled    {m.get('doubled_cells', 0)} cells "
              f"({100 * m.get('doubled_frac', 0):.1f}% of wall)")
        mf = m.get('manhattan_frac')
        print(f"  forks      {m.get('junctions', 0)} junctions "
              f"({m.get('junctions_per_10m', 0)}/10 m)     alignment  "
              f"{'n/a' if mf is None else format(mf, '.2f')}")
        for f in m.get('flags', []):
            print(f"    - {f}")

    p = res.get('pose')
    print(f"\n{'-' * 72}\n  TRAJECTORY\n{'-' * 72}")
    if not p or 'error' in p:
        print(f"  {(p or {}).get('error', 'no pose log')}")
    else:
        print(f"  {p['samples']} samples over {p['duration_s']} s "
              f"({p['rate_hz']} Hz)")
        print(f"  SLAM path        {p.get('map_path_m', '?')} m")
        if p.get('has_odom'):
            print(f"  wheel path       {p.get('odom_path_m', '?')} m   "
                  f"(dead reckoning, no scan matching)")
        print(f"  return to mark   {p.get('return_to_mark_m', '?')} m from (0,0), "
              f"nose {p.get('final_map_yaw_deg', '?')} deg "
              f"(closed {p.get('yaw_closure_deg', '?')} deg)")
        if p.get('has_odom'):
            print(f"  wheel closure    {p.get('odom_closure_m', '?')} m  <- if the robot "
                  f"physically ended on the mark,")
            print(f"                   this is the wheels' accumulated drift for the whole run")
            c = p.get('correction_step') or {}
            print(f"\n  SLAM applied     {p.get('final_correction_m', '?')} m net "
                  f"correction, {c.get('total_m', '?')} m cumulative")
            print(f"  correction step  median {c.get('median_m', '?')} m, "
                  f"p95 {c.get('p95_m', '?')} m, max {c.get('max_m', '?')} m")
            print(f"  odom step median {p.get('odom_step_median_m', '?')} m")
        if p.get('note'):
            print(f"\n  note: {p['note']}")

    ev = (p or {}).get('jump_events') or []
    if ev:
        print(f"\n{'-' * 72}\n  CORRECTIONS — {len(ev)} event(s), largest first"
              f"\n{'-' * 72}")
        print(f"    {'t+s':>8}{'corr_m':>9}{'peak':>8}{'yaw':>8}{'odom_m':>9}"
              f"   location            what it means")
        for e in ev[:12]:
            print(f"    {e['t_rel']:>8.1f}{e['corr_m']:>9.3f}{e['peak_m']:>8.3f}"
                  f"{e['yaw_deg']:>8.2f}{e['odom_m']:>9.3f}"
                  f"   map ({e['map_x']}, {e['map_y']})".ljust(24)
                  + f"   {e['verdict']}")

    wres = res.get('wheels')
    print(f"\n{'-' * 72}\n  WHEELS\n{'-' * 72}")
    if not wres or 'error' in wres:
        print(f"  {(wres or {}).get('error', 'no telemetry log')}")
    else:
        print(f"  {wres['samples']} samples over {wres['duration_s']} s "
              f"({wres['rate_hz']} Hz)")
        print(f"    {'':>4}{'rms_err':>10}{'sat%':>8}{'sign%':>8}"
              f"{'max_pwm':>9}{'mean|w|':>9}{'arc_m':>8}")
        for w in WHEELS:
            d = wres['wheels'][w]
            print(f"    {w:>4}{(d['rms_error_rads'] if d['rms_error_rads'] is not None else 0):>10.3f}"
                  f"{d['saturated_pct']:>8.1f}{d['sign_mismatch_pct']:>8.1f}"
                  f"{d['max_abs_pwm']:>9.0f}{d['mean_abs_rads']:>9.3f}{d['arc_m']:>8.2f}")
        s = wres['arc_spread']
        print(f"\n  wheel travel spread  {s['min_m']} m ({s['least']}) .. "
              f"{s['max_m']} m ({s['most']})"
              + (f", ratio {s['ratio']}" if s['ratio'] else ''))
        if s['ratio'] and s['ratio'] > 1.5:
            print('    one wheel did much less work than another — slip, or a '
                  'mechanical problem.')
            print('    Odometry is computed from all four, so this corrupts the '
                  'map through the pose estimate.')

    x = res.get('cross') or {}
    print(f"\n{'-' * 72}\n  CROSS-CHECKS\n{'-' * 72}")
    if not x.get('notes') and not x.get('jump_vs_map') and not x.get('jump_vs_wheels'):
        print('  nothing to correlate — needs both a correction log and a map, '
              'and at least one correction.')
    for row in x.get('jump_vs_map', []):
        print(f"  correction {row['corr_m']} m at t+{row['t_rel']} s, map "
              f"({row['map_x']}, {row['map_y']}), is {row['distance_m']} m from a "
              f"{row['cluster_cells']}-cell doubled wall (gap {row['cluster_gap_m']} m)")
    for row in x.get('jump_vs_wheels', []):
        print(f"  correction {row['corr_m']} m at t+{row['t_rel']} s coincided with "
              f"{'/'.join(row['kinds'])} on {'/'.join(row['wheels'])}")
    for n in x.get('notes', []):
        print(f"    - {n}")

    print(f"\n{'-' * 72}\n  VERDICT\n{'-' * 72}")
    for line in res['verdict']:
        print(f"  {line}")
    print()


def build_verdict(res):
    out, bad = [], False
    m, p, w, x = (res.get(k) or {} for k in ('map', 'pose', 'wheels', 'cross'))

    if m.get('verdict') == 'CLEAN':
        out.append('MAP        clean — no fold signature found.')
    elif m.get('verdict'):
        out.append(f"MAP        {m['verdict']} — {len(m.get('flags', []))} flag(s); "
                   f"see the map section.")
        bad = bad or m['verdict'] == 'FOLDED'
    else:
        out.append('MAP        not analysed.')

    r = p.get('return_to_mark_m')
    if r is not None:
        verdict = 'good' if r <= 0.05 else ('acceptable' if r <= 0.15 else 'poor')
        out.append(f'RETURN     {r} m from the mark — {verdict}. '
                   f'(Only meaningful if the robot was physically parked back on it.)')
        bad = bad or r > 0.15

    if p.get('has_odom'):
        n = p.get('jump_count', 0)
        gr = len([e for e in (p.get('jump_events') or []) if e['odom_normal']])
        if n == 0:
            out.append('CORRECTION no jump above threshold — the pose graph never '
                       'yanked the estimate.')
        else:
            out.append(f'CORRECTION {n} jump event(s), {gr} of them with wheel odometry '
                       f'stepping normally, i.e. the graph moved and the robot did not.')
    else:
        out.append('CORRECTION not separable — this run predates odometry logging. '
                   'Re-run after deploying the current dashboard.')

    sp = (w.get('arc_spread') or {}).get('ratio')
    if sp is not None:
        out.append(f'WHEELS     travel ratio {sp} between the busiest and laziest wheel'
                   + (' — investigate, this corrupts odometry.' if sp > 1.5 else '.'))

    if x.get('jump_vs_map'):
        out.append('AGREEMENT  a correction and a doubled wall land in the same place. '
                   'That is a false closure with two independent witnesses.')
        bad = True
    if x.get('jump_vs_wheels'):
        out.append('AGREEMENT  a correction coincides with a wheel anomaly — fix the '
                   'mechanics before blaming the scan matcher.')

    out.append('')
    out.append('NOT USABLE for AMCL — redo the drive.' if bad else
               'Nothing here disqualifies this run. Judge the map on its own section.')
    return out


# ═════════════════════════════════════════════════════════════════════════
#  Self-test
# ═════════════════════════════════════════════════════════════════════════
def _write_synth(folder, stamp, jump_at=None):
    """A synthetic run with a KNOWN answer: the robot drives a square, and if
    `jump_at` is set the correction leaps 0.4 m at that sample while wheel
    odometry keeps stepping smoothly — the exact signature §17.32 measured."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    n, step, t0 = 400, 0.02, 1_800_000_000.0
    rows = []
    cx = cy = 0.0
    x = y = 0.0
    for i in range(n):
        leg, k = divmod(i, n // 4)
        dx, dy = [(1, 0), (0, 1), (-1, 0), (0, -1)][leg % 4]
        x += dx * step
        y += dy * step
        if jump_at is not None and i == jump_at:
            cx += 0.40                      # the correction leaps
        rows.append((t0 + i * 0.1, x + cx, y + cy, 0.0, x, y, 0.0, cx, cy, 0.0))
    with open(folder / f'{stamp}_pose.csv', 'w', newline='') as fh:
        wtr = csv.writer(fh)
        wtr.writerow(['epoch_s', 'map_x', 'map_y', 'map_yaw_deg',
                      'odom_x', 'odom_y', 'odom_yaw_deg',
                      'corr_x', 'corr_y', 'corr_yaw_deg'])
        for r in rows:
            wtr.writerow(['{:.3f}'.format(r[0])] + ['{:.4f}'.format(v) for v in r[1:]])

    with open(folder / f'{stamp}.csv', 'w', newline='') as fh:
        wtr = csv.writer(fh)
        hdr = ['pi_time_s']
        for w in WHEELS:
            hdr += [f'{w}_target_rads', f'{w}_actual_rads', f'{w}_pwm']
        wtr.writerow(hdr)
        for i in range(n):
            row = ['{:.4f}'.format(t0 + i * 0.1)]
            for j, w in enumerate(WHEELS):
                tgt = 2.0
                act = 2.0 if not (jump_at and w == 'RL' and abs(i - jump_at) < 3) else -2.0
                pwm = 120.0
                row += ['{:.4f}'.format(tgt), '{:.4f}'.format(act), '{:.4f}'.format(pwm)]
            wtr.writerow(row)
    return folder / stamp


def selftest(args):
    import tempfile
    ok = True
    with tempfile.TemporaryDirectory() as td:
        # ── clean run: no correction jump anywhere
        base = _write_synth(td, 'run_20260101_000001', jump_at=None)
        res = analyse(base, args)
        p = res['pose']
        print(f"  clean run    {p['samples']} samples, {p['jump_count']} jump events, "
              f"SLAM path {p['map_path_m']} m, wheel path {p['odom_path_m']} m")
        if p['jump_count'] != 0:
            print('               FAIL: a run with no correction reported a jump')
            ok = False
        if abs(p['map_path_m'] - p['odom_path_m']) > 0.05:
            print('               FAIL: with no correction the two paths must match')
            ok = False

        # ── jump run: a 0.40 m correction with odom stepping normally
        base = _write_synth(td, 'run_20260101_000002', jump_at=200)
        res = analyse(base, args)
        p, w, x = res['pose'], res['wheels'], res['cross']
        print(f"  jump run     {p['jump_count']} jump event(s), "
              f"largest {p['jump_events'][0]['corr_m']} m, "
              f"odom stepped {p['jump_events'][0]['odom_m']} m")
        if p['jump_count'] != 1:
            print(f"               FAIL: expected exactly 1 jump event")
            ok = False
        elif abs(p['jump_events'][0]['corr_m'] - 0.40) > 0.02:
            print('               FAIL: the 0.40 m correction was not measured correctly')
            ok = False
        elif not p['jump_events'][0]['odom_normal']:
            print('               FAIL: odom stepped normally but was not recognised '
                  'as such — the whole discriminator is broken')
            ok = False
        else:
            print(f"               verdict: {p['jump_events'][0]['verdict']}")
        if w['wheels']['RL']['sign_mismatch_pct'] <= 0:
            print('               FAIL: a planted RL sign mismatch was not detected')
            ok = False
        else:
            print(f"               RL sign mismatch {w['wheels']['RL']['sign_mismatch_pct']}% "
                  f"detected, {len(x['jump_vs_wheels'])} correlated with the jump")
        if not x['jump_vs_wheels']:
            print('               FAIL: the wheel anomaly coincided with the jump but '
                  'was not correlated')
            ok = False

        # ── old-format run must still load
        with open(Path(td) / 'run_20260101_000003_pose.csv', 'w', newline='') as fh:
            wtr = csv.writer(fh)
            wtr.writerow(['epoch_s', 'map_x', 'map_y', 'yaw_deg'])
            for i in range(50):
                wtr.writerow([1_800_000_000.0 + i * 0.1, i * 0.01, 0.0, 0.0])
        res = analyse(Path(td) / 'run_20260101_000003', args)
        p = res['pose']
        print(f"  legacy run   loaded {p['samples']} samples, has_odom={p['has_odom']}, "
              f"path {p['map_path_m']} m")
        if p['has_odom'] or 'note' not in p:
            print('               FAIL: a pre-26-Aug pose CSV must load and say that '
                  'odometry is unavailable')
            ok = False

    print('\nselftest:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


# ═════════════════════════════════════════════════════════════════════════
def analyse(base, args):
    art = load_run(base)
    res = {'stamp': art['stamp'], 'artefacts': art['present']}

    mi, mi_path = find_map_integrity([Path(__file__).parent, art['folder'], Path.cwd()])
    res['map_integrity_from'] = mi_path
    grid = doubled = None
    if art['pgm'].is_file() and mi is not None:
        try:
            ns = argparse.Namespace(
                tensor_radius=mi.DEF_TENSOR_R, max_gap=mi.DEF_MAX_GAP_M,
                min_gap=mi.DEF_MIN_GAP_M, angle_tol=mi.DEF_ANGLE_TOL,
                min_coherence=mi.DEF_MIN_COHERENCE)
            mres, grid, doubled, _skel, _junc = mi.analyse(art['pgm'], ns)
            res['map'] = mres
        except Exception as exc:
            res['map'] = {'error': f'{type(exc).__name__}: {exc}'}
    elif art['pgm'].is_file():
        res['map'] = {'error': 'map_integrity.py not found next to this tool or the run'}

    pose_rows, has_odom = ([], False)
    if art['pose'].is_file():
        pose_rows, has_odom = load_pose(art['pose'])
        res['pose'] = analyse_pose(pose_rows, has_odom, args.corr_jump, args.event_gap)
    else:
        res['pose'] = {'error': 'no _pose.csv'}

    if art['telem'].is_file():
        trows = load_telemetry(art['telem'])
        res['wheels'] = analyse_wheels(trows)
        # rebase anomaly times onto the pose clock so the two can be compared
        if pose_rows:
            t0 = pose_rows[0]['t']
            for a in res['wheels'].get('anomalies', []):
                a['t_rel'] = round(a['t'] - t0, 1)
    else:
        res['wheels'] = {'error': 'no telemetry .csv'}

    if art['report'].is_file():
        try:
            res['report'] = json.loads(art['report'].read_text())
        except Exception:
            pass

    res['cross'] = cross_check(res.get('pose') or {}, res.get('wheels') or {},
                               res.get('map') or {}, args.coincide_m, args.coincide_s)
    res['verdict'] = build_verdict(res)
    res['_grid'], res['_doubled'], res['_pose_rows'] = grid, doubled, pose_rows
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('run', nargs='?', help='run stamp, stem, or any of its files')
    ap.add_argument('--png', help='annotated map: both paths + correction markers')
    ap.add_argument('--png-scale', type=int, default=4)
    ap.add_argument('--json', help='write the whole analysis as JSON')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--corr-jump', type=float, default=DEF_CORR_JUMP_M, dest='corr_jump',
                    help=f'per-sample correction counted as a jump (default {DEF_CORR_JUMP_M} m)')
    ap.add_argument('--event-gap', type=float, default=DEF_EVENT_GAP_S, dest='event_gap')
    ap.add_argument('--coincide-m', type=float, default=DEF_COINCIDE_M, dest='coincide_m')
    ap.add_argument('--coincide-s', type=float, default=DEF_COINCIDE_S, dest='coincide_s')
    args = ap.parse_args()

    if args.selftest:
        return selftest(args)
    if not args.run:
        ap.error('need a run stamp/path, or --selftest')

    res = analyse(args.run, args)
    print_report(res)

    if args.png:
        if res.get('_grid') is None:
            print('  --png needs the map and map_integrity.py; skipped.')
        else:
            n = write_png(args.png, res['_grid'], res['_doubled'] or {},
                          res['_pose_rows'], (res.get('pose') or {}).get('jump_events') or [],
                          args.png_scale)
            print(f'  wrote {args.png} ({n} bytes)')
            print('  red = doubled wall, blue = SLAM path, green = wheel path, '
                  'yellow cross = correction')
    if args.json:
        Path(args.json).write_text(json.dumps(
            {k: v for k, v in res.items() if not k.startswith('_')}, indent=2))
        print(f'  wrote {args.json}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
