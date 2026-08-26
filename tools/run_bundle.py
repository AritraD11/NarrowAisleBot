#!/usr/bin/env python3
"""run_bundle.py — package one drive into a single file, on the Pi.

A run is everything between tapping MAP and tapping MAP again. It leaves four
files behind, and reading them one at a time is how this project spent three
weeks drawing conclusions from single runs. This gathers all of it, runs the
full analysis on the Pi where the data already is, and writes ONE file you can
carry to Windows and open in `docs/tools/run_viewer.html`.

    ./tools/run_bundle.py run_20260826_143000
    ./tools/run_bundle.py --latest
    ./tools/run_bundle.py --all
    ./tools/run_bundle.py --purge              # list runs under the minimum
    ./tools/run_bundle.py --purge --apply      # and delete them

WHY THERE IS A MINIMUM LENGTH. Of the 80 maps in ~/aislebot_logs, most are
seconds-long fragments from testing something else, and two of them
(run_20260825_113735 and _151713) were analysed at length on 26 Aug before
anyone noticed they were 30-second bug-fix checks rather than commissioning
drives. A run too short to contain a lap cannot answer a question about a lap.
Anything under --min-seconds is refused with the duration named, so the
mistake announces itself instead of producing a confident report about
nothing.

The bundle is plain JSON, not an archive: the viewer is a single HTML file
with no libraries, and JSON.parse is something a browser can already do. Use
--zip as well when you want the raw files kept verbatim for the archive.
"""
import argparse
import base64
import csv
import importlib.util
import json
import sys
import time
import zipfile
from pathlib import Path

MIN_SECONDS = 60.0
BUNDLE_VERSION = 1


def load_sibling(name, hint_dirs):
    for d in hint_dirs:
        cand = Path(d) / name
        if cand.is_file():
            spec = importlib.util.spec_from_file_location(name[:-3], cand)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name[:-3]] = mod
            try:
                spec.loader.exec_module(mod)
                return mod
            except Exception as exc:
                print(f'  !! {cand}: {exc}', file=sys.stderr)
    return None


def run_duration(art):
    """Longest span any of the run's own logs agrees on.

    The report's own `duration` is preferred when present, but a run killed
    mid-flight (§17.34's whole subject) may not have one, and then the pose
    and telemetry spans are what is left.
    """
    best = 0.0
    if art['report'].is_file():
        try:
            best = max(best, float(json.loads(art['report'].read_text()).get('duration', 0)))
        except Exception:
            pass
    for key, tcol in (('pose', 'epoch_s'), ('telem', 'pi_time_s')):
        if not art[key].is_file():
            continue
        try:
            with open(art[key], newline='') as fh:
                ts = [float(r[tcol]) for r in csv.DictReader(fh) if r.get(tcol)]
            if len(ts) >= 2:
                best = max(best, max(ts) - min(ts))
        except Exception:
            pass
    return best


def csv_rows(path, cols):
    if not path.is_file():
        return []
    out = []
    with open(path, newline='') as fh:
        for r in csv.DictReader(fh):
            row = []
            for c in cols:
                v = r.get(c, '')
                try:
                    row.append(float(v))
                except (TypeError, ValueError):
                    row.append(None)
            out.append(row)
    return out


POSE_COLS_NEW = ['epoch_s', 'map_x', 'map_y', 'map_yaw_deg',
                 'odom_x', 'odom_y', 'odom_yaw_deg',
                 'corr_x', 'corr_y', 'corr_yaw_deg']
POSE_COLS_OLD = ['epoch_s', 'map_x', 'map_y', 'yaw_deg']


def pose_cols_for(path):
    with open(path, newline='') as fh:
        hdr = next(csv.reader(fh), [])
    return POSE_COLS_NEW if 'map_yaw_deg' in hdr else POSE_COLS_OLD


def build(stamp_or_path, ra, args):
    art = ra.load_run(stamp_or_path)
    stamp = art['stamp']
    if not any(art['present'].values()):
        return None, f'{stamp}: no files found'

    dur = run_duration(art)
    if dur < args.min_seconds and not args.force:
        return None, (f'{stamp}: {dur:.1f} s is under the {args.min_seconds:.0f} s '
                      f'minimum — too short to contain a lap. --force to override.')

    res = ra.analyse(art['folder'] / stamp, args)
    grid = res.pop('_grid', None)
    doubled = res.pop('_doubled', None) or {}
    res.pop('_pose_rows', None)

    bundle = {
        'bundle_version': BUNDLE_VERSION,
        'stamp': stamp,
        'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'duration_s': round(dur, 1),
        'artefacts': art['present'],
        'analysis': res,
    }

    if grid is not None:
        # One byte per cell, 0 free / 1 occupied / 2 unknown — already
        # classified, so the viewer does not repeat the trinary/205/inverted
        # -brightness reasoning that map_corpus.py's header warns about.
        bundle['map'] = {
            'w': grid.w, 'h': grid.h, 'res': grid.res,
            'origin_x': grid.ox, 'origin_y': grid.oy,
            'cells': base64.b64encode(bytes(grid.cls)).decode('ascii'),
            'doubled': sorted(int(i) for i in doubled),
        }

    if art['pose'].is_file():
        cols = pose_cols_for(art['pose'])
        bundle['pose'] = {'columns': cols, 'rows': csv_rows(art['pose'], cols)}
    if art['telem'].is_file():
        tcols = ['pi_time_s']
        for w in ra.WHEELS:
            tcols += [f'{w}_target_rads', f'{w}_actual_rads', f'{w}_pwm']
        bundle['telemetry'] = {'columns': tcols, 'rows': csv_rows(art['telem'], tcols)}
    if art['report'].is_file():
        try:
            bundle['report'] = json.loads(art['report'].read_text())
        except Exception:
            pass

    out = Path(args.out_dir or art['folder']) / f'{stamp}_bundle.json'
    out.write_text(json.dumps(bundle, separators=(',', ':')))

    zpath = None
    if args.zip:
        zpath = out.with_suffix('.zip')
        with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
            for key, path in art.items():
                if isinstance(path, Path) and path.is_file():
                    z.write(path, path.name)
            z.write(out, out.name)
    return (out, zpath, bundle), None


def find_runs(folder):
    import re
    return sorted({m.group(1) for f in Path(folder).iterdir()
                   if (m := re.match(r'(run_\d{8}_\d{6})\.(pgm|csv)$', f.name))})


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('run', nargs='?', help='run stamp, stem, or any of its files')
    ap.add_argument('--folder', default='.', help='where the runs are (default .)')
    ap.add_argument('--latest', action='store_true', help='bundle the newest run')
    ap.add_argument('--all', action='store_true', help='bundle every run long enough')
    ap.add_argument('--purge', action='store_true',
                    help='list runs under the minimum; add --apply to delete them')
    ap.add_argument('--apply', action='store_true', help='with --purge, actually delete')
    ap.add_argument('--zip', action='store_true', help='also archive the raw files')
    ap.add_argument('--out-dir', help='where to write bundles (default: alongside)')
    ap.add_argument('--min-seconds', type=float, default=MIN_SECONDS)
    ap.add_argument('--force', action='store_true', help='bundle even if too short')
    # forwarded to run_analyzer
    ap.add_argument('--corr-jump', type=float, default=0.05, dest='corr_jump')
    ap.add_argument('--event-gap', type=float, default=0.5, dest='event_gap')
    ap.add_argument('--coincide-m', type=float, default=1.0, dest='coincide_m')
    ap.add_argument('--coincide-s', type=float, default=1.0, dest='coincide_s')
    args = ap.parse_args()

    here = Path(__file__).parent
    ra = load_sibling('run_analyzer.py', [here, Path(args.folder), Path.cwd()])
    if ra is None:
        sys.exit('run_analyzer.py not found next to this tool, the folder, or the cwd.')

    folder = Path(args.folder)

    if args.purge:
        short = []
        for s in find_runs(folder):
            art = ra.load_run(folder / s)
            d = run_duration(art)
            if d < args.min_seconds:
                files = [p for k, p in art.items()
                         if isinstance(p, Path) and p.is_file()]
                short.append((s, d, files))
        if not short:
            print(f'no runs under {args.min_seconds:.0f} s.')
            return 0
        total = sum(p.stat().st_size for _, _, fs in short for p in fs)
        print(f'{len(short)} run(s) under {args.min_seconds:.0f} s, '
              f'{total / 1e6:.1f} MB:')
        for s, d, fs in short:
            print(f'  {s}  {d:6.1f} s  {len(fs)} file(s)')
        if not args.apply:
            print('\ndry run — nothing deleted. Add --apply to delete these.')
            return 0
        n = 0
        for _, _, fs in short:
            for p in fs:
                try:
                    p.unlink()
                    n += 1
                except OSError as exc:
                    print(f'  !! {p}: {exc}', file=sys.stderr)
        print(f'\ndeleted {n} file(s), {total / 1e6:.1f} MB reclaimed.')
        return 0

    targets = []
    if args.all:
        targets = [folder / s for s in find_runs(folder)]
    elif args.latest:
        runs = find_runs(folder)
        if not runs:
            sys.exit(f'no runs in {folder}')
        targets = [folder / runs[-1]]
    elif args.run:
        targets = [args.run]
    else:
        ap.error('need a run, --latest, --all, or --purge')

    made, skipped = 0, 0
    for tgt in targets:
        result, err = build(tgt, ra, args)
        if err:
            print(f'  skip  {err}')
            skipped += 1
            continue
        out, zpath, bundle = result
        v = (bundle['analysis'].get('map') or {}).get('verdict', '?')
        print(f'  ok    {bundle["stamp"]}  {bundle["duration_s"]:.0f} s  '
              f'map {v}  ->  {out.name} ({out.stat().st_size / 1000:.0f} kB)'
              + (f' + {zpath.name}' if zpath else ''))
        made += 1

    print(f'\n{made} bundle(s) written, {skipped} skipped.')
    if made:
        print('Copy the _bundle.json to Windows and drop it into '
              'docs/tools/run_viewer.html.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
