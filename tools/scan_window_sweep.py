#!/usr/bin/env python3
"""scan_window_sweep.py — make scan_quality.py's flicker number comparable.

WHY THIS EXISTS. On 3 Sep a 30 s capture reported 84.8% flicker against
§17.45's 74.8-78%, and the obvious reading was "the scan got worse". It is
not a valid comparison, for a reason that is arithmetic rather than
arguable:

    flicker_pct = (ever_valid - always_valid) / ever_valid

`always_valid` requires a ray to be valid in EVERY scan of the window.
Lengthen the window and that set can only SHRINK, never grow, so
flicker_pct rises monotonically with capture length. A 30 s window is
simply a stricter test than a 10 s one. Two captures of different lengths
cannot be compared at all, and §17.45 does not record the length it used.

This replays a saved capture at many window lengths so the curve is
visible, and so the number at ANY window can be read off and compared
like-for-like against a historical figure whose window is known.

    ./tools/scan_quality.py --seconds 30 --save cap.json     # capture
    ./tools/scan_window_sweep.py cap.json                    # then this
    ./tools/scan_window_sweep.py cap.json --match 76         # find the window
    ./tools/scan_window_sweep.py --selftest

Deliberately a SEPARATE tool, not a flag on scan_quality.py. §17.46's rule:
changing an instrument mid-campaign destroys the baseline it is being
compared against. scan_quality.py's output must stay byte-comparable with
every run already recorded in the journal."""
import argparse
import json
import math
import statistics
import sys
from pathlib import Path


def valid_mask(ranges, rmin, rmax):
    """Byte-identical to scan_quality.py's. If that one changes, change this
    one in the same commit or the two tools silently stop agreeing."""
    out = []
    for r in ranges:
        ok = (r is not None and not math.isinf(r) and not math.isnan(r)
              and r > max(rmin, 1e-3) and r < rmax)
        out.append(ok)
    return out


def flicker_over(masks, scans=None, lo=None, hi=None):
    """scan_quality.py's stability() metric, for one window of scans.

    Also returns per-ray range noise when the raw scans are supplied, because
    that number carries the SAME window confound and for the same reason:
    the std is computed only over rays valid in EVERY scan, and lengthening
    the window shrinks that set to the most stable rays, biasing the noise
    figure DOWN. §17.45's p90 22.8-24.5 mm and a 30 s capture's p90 11.9 mm
    are no more comparable than the flicker numbers were."""
    if len(masks) < 2:
        return None
    n = min(len(m) for m in masks)
    always_idx = [i for i in range(n) if all(m[i] for m in masks)]
    ever = sum(1 for i in range(n) if any(m[i] for m in masks))
    if ever == 0:
        return None
    out = {
        'always': len(always_idx),
        'ever': ever,
        'flicker_pct': round(100.0 * (ever - len(always_idx)) / ever, 1),
    }
    if scans is not None and always_idx:
        stds = []
        for i in always_idx:
            vals = [scans[k]['ranges'][i] for k in range(lo, hi)]
            if len(vals) >= 2:
                stds.append(statistics.pstdev(vals))
        if stds:
            ss = sorted(stds)
            out['noise_p90_mm'] = round(
                1000 * ss[min(len(ss) - 1, int(0.9 * len(ss)))], 1)
    return out


def sweep(masks, hz, windows=None, scans=None):
    """flicker_pct at each window length, averaged over every disjoint
    window of that length in the capture. Disjoint rather than sliding:
    overlapping windows share scans and would understate the spread."""
    total = len(masks)
    if windows is None:
        windows = [w for w in (2, 3, 5, 10, 20, 30, 50, 75, 100, 150, 200,
                               300, 500) if w <= total]
        if total not in windows:
            windows.append(total)
    rows = []
    for w in windows:
        vals, noise, always = [], [], []
        for start in range(0, total - w + 1, w):
            r = flicker_over(masks[start:start + w], scans, start, start + w)
            if r:
                vals.append(r['flicker_pct'])
                always.append(r['always'])
                if 'noise_p90_mm' in r:
                    noise.append(r['noise_p90_mm'])
        if not vals:
            continue
        rows.append({
            'window_scans': w,
            'window_s': round(w / hz, 1) if hz else None,
            'n_windows': len(vals),
            'flicker_mean': round(statistics.mean(vals), 1),
            'flicker_min': min(vals),
            'flicker_max': max(vals),
            'always_mean': round(statistics.mean(always), 1),
            'noise_p90_mm': round(statistics.mean(noise), 1) if noise else None,
        })
    return rows


def selftest():
    """A synthetic capture with a KNOWN answer, so the monotonicity claim
    this whole tool rests on is demonstrated rather than asserted."""
    fails = []

    def chk(cond, msg):
        print(('  PASS  ' if cond else '  FAIL  ') + msg)
        if not cond:
            fails.append(msg)

    # 100 scans, 10 rays. Ray 0 always valid. Ray 1 drops out on scan 50
    # only. Rays 2-9 never valid.
    masks = []
    for s in range(100):
        m = [True, s != 50] + [False] * 8
        masks.append(m)

    r2 = flicker_over(masks[:2])          # scans 0,1: ray 1 valid in both
    chk(r2['flicker_pct'] == 0.0,
        f"a 2-scan window before the dropout sees 0% flicker (got {r2['flicker_pct']})")

    r100 = flicker_over(masks)            # includes scan 50
    chk(r100['ever'] == 2 and r100['always'] == 1,
        f"over 100 scans: 2 rays ever valid, 1 always (got {r100['ever']}, {r100['always']})")
    chk(r100['flicker_pct'] == 50.0,
        f"one ray dropping out ONCE in 100 scans scores 50% flicker "
        f"(got {r100['flicker_pct']}) — this is the metric's whole character")

    rows = sweep(masks, hz=10.0)
    seq = [r['flicker_mean'] for r in rows]
    chk(seq == sorted(seq),
        f"flicker_pct is monotonically non-decreasing in window length {seq}")
    chk(seq[0] < seq[-1],
        "and it genuinely rises — so two captures of different lengths are "
        "NOT comparable")

    print()
    if fails:
        print(f'{len(fails)} FAILED')
        return 1
    print('selftest passed')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('capture', nargs='?', help='JSON from scan_quality.py --save')
    ap.add_argument('--match', type=float,
                    help='find the window length whose flicker_pct is closest '
                         'to this (e.g. 76 for §17.45)')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not a.capture:
        ap.error('need a capture file, or --selftest')

    scans = json.loads(Path(a.capture).read_text())
    if len(scans) < 3:
        print('need at least 3 scans')
        return 1

    masks = [valid_mask(s['ranges'], s['range_min'], s['range_max'])
             for s in scans]

    # Rate from the capture itself where timestamps allow, else the
    # measured free-run figure. Only used to label windows in seconds.
    hz = None
    ts = [s.get('t') or s.get('stamp') for s in scans]
    if all(isinstance(t, (int, float)) for t in ts) and ts[-1] > ts[0]:
        hz = (len(ts) - 1) / (ts[-1] - ts[0])
    rows = sweep(masks, hz or 11.45, scans=scans)

    print('=' * 70)
    print(f'  SCAN FLICKER vs WINDOW LENGTH   {a.capture}')
    print(f'  {len(scans)} scans' + (f' @ {hz:.2f} Hz' if hz else
                                     ' @ ~11.45 Hz assumed'))
    print('=' * 70)
    print()
    print('  flicker_pct = (ever_valid - always_valid) / ever_valid')
    print('  always_valid can only SHRINK as the window grows, so this rises')
    print('  monotonically. Compare captures ONLY at equal window length.')
    print()
    print(f"  {'scans':>7} {'~sec':>6} {'n':>4}   {'flick':>6} {'min':>6} {'max':>6}"
          f"   {'always':>6} {'noise':>7}")
    print('  ' + '-' * 62)
    for r in rows:
        npm = r.get('noise_p90_mm')
        print(f"  {r['window_scans']:>7} {r['window_s'] or 0:>6.1f} "
              f"{r['n_windows']:>4}   {r['flicker_mean']:>6.1f} "
              f"{r['flicker_min']:>6.1f} {r['flicker_max']:>6.1f}   "
              f"{r['always_mean']:>6.1f} "
              f"{(f'{npm:.1f}mm' if npm else '—'):>7}")
    print()
    print('  always = rays valid in EVERY scan of the window. It shrinks as')
    print('  the window grows, which is what drives flicker up AND drags the')
    print('  noise p90 down — both numbers carry the same confound.')

    if a.match is not None:
        best = min(rows, key=lambda r: abs(r['flicker_mean'] - a.match))
        print()
        print(f'  Closest to {a.match}%: a {best["window_scans"]}-scan '
              f'(~{best["window_s"]} s) window, at {best["flicker_mean"]}%.')
        print('  If the historical figure used a window near that length,')
        print('  THE INPUT HAS NOT CHANGED. If it used a much longer one,')
        print('  this capture is genuinely better; a much shorter one, worse.')

    print()
    print('  §17.45 recorded 74.8-78% but NOT its capture length, so the')
    print('  comparison cannot be closed from the journal alone. Re-run')
    print('  scan_quality.py at a known --seconds and save it, and every')
    print('  future comparison is exact.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
