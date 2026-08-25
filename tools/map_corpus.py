#!/usr/bin/env python3
"""map_corpus.py — compare every mapping run in a folder, at once.

Every finding in Research_Journal.md Part XVII comes from reading exactly
one run. This reads all of them and puts the numbers side by side, which is
the only way to answer "is this map better than the last one" without
eyeballing 70 grids.

Takes a directory of run_<stamp>.{pgm,yaml,_report.json} sets — the files
the dashboard writes per run.

    ./tools/map_corpus.py data/field_runs
    ./tools/map_corpus.py data/field_runs --csv out.csv

Reads the .pgm directly rather than trusting the report's cached stats, so
a run whose report is missing still gets counted and a disagreement between
the two surfaces instead of being silently preferred.
"""
import argparse, csv, json, re, sys
from pathlib import Path


def read_pgm(path):
    """Parse P5/P2 PGM. Handles comment lines anywhere in the header, which
    map_saver_cli emits and a naive split() parser trips over."""
    data = Path(path).read_bytes()
    tokens, i = [], 0
    while len(tokens) < 4:
        while i < len(data) and data[i:i + 1].isspace():
            i += 1
        if data[i:i + 1] == b'#':
            while i < len(data) and data[i:i + 1] not in (b'\n', b'\r'):
                i += 1
            continue
        start = i
        while i < len(data) and not data[i:i + 1].isspace():
            i += 1
        tokens.append(data[start:i])
    magic, w, h, maxval = tokens[0].decode(), int(tokens[1]), int(tokens[2]), int(tokens[3])
    i += 1
    if magic == 'P5':
        px = list(data[i:i + w * h])
    elif magic == 'P2':
        px = [int(v) for v in data[i:].split()][:w * h]
    else:
        raise ValueError(f'{path}: unsupported PGM magic {magic}')
    return w, h, maxval, px


def read_yaml(path):
    """The flat keys map_saver_cli writes. Not a general YAML parser and
    does not pretend to be — avoids a PyYAML dependency on the Pi."""
    out = {}
    for line in Path(path).read_text().splitlines():
        if ':' not in line or line.strip().startswith('#'):
            continue
        k, v = line.split(':', 1)
        v = v.strip()
        if v.startswith('['):
            out[k.strip()] = [float(x) for x in v.strip('[]').split(',')]
        else:
            try:
                out[k.strip()] = float(v)
            except ValueError:
                out[k.strip()] = v
    return out


def classify(px, occ_thresh, free_thresh):
    """map_saver_cli trinary: 205 = unknown, and the rest is INVERTED
    brightness, so occupancy = (255 - p)/255 while the yaml thresholds are
    on occupancy. Getting that backwards silently swaps free and occupied."""
    occ = free = unk = 0
    for p in px:
        if p == 205:
            unk += 1
            continue
        o = (255 - p) / 255.0
        if o >= occ_thresh:
            occ += 1
        elif o <= free_thresh:
            free += 1
        else:
            unk += 1
    return occ, free, unk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('--csv')
    args = ap.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        sys.exit(f'not a directory: {folder}')

    stamps = sorted({m.group(1) for f in folder.iterdir()
                     if (m := re.match(r'(run_\d{8}_\d{6})\.pgm$', f.name))})
    if not stamps:
        sys.exit(f'no run_*.pgm found in {folder}')

    rows = []
    for s in stamps:
        pgm, yml, rep = folder / f'{s}.pgm', folder / f'{s}.yaml', folder / f'{s}_report.json'
        try:
            w, h, _, px = read_pgm(pgm)
        except Exception as exc:
            print(f'  !! {s}: {exc}', file=sys.stderr)
            continue
        meta = read_yaml(yml) if yml.exists() else {}
        res = meta.get('resolution', 0.05)
        occ, free, unk = classify(px, meta.get('occupied_thresh', 0.65),
                                      meta.get('free_thresh', 0.196))
        total = max(w * h, 1)
        r = {'run': s, 'w': w, 'h': h, 'res': res,
             'extent_m': f'{w * res:.1f}x{h * res:.1f}',
             'occupied': occ, 'free': free, 'unknown': unk,
             'occ_pct': 100 * occ / total, 'free_pct': 100 * free / total,
             'unk_pct': 100 * unk / total,
             # Occupied cells are ~1 cell thick, so cells*res approximates
             # metres of wall seen; against the bounding perimeter that is
             # "did the drive actually get round the room".
             'wall_m': occ * res, 'perim_m': 2 * (w * res + h * res),
             'duration_s': '', 'samples': '', 'health': ''}
        r['wall_frac'] = r['wall_m'] / r['perim_m'] if r['perim_m'] else 0
        if rep.exists():
            try:
                j = json.loads(rep.read_text())
                r['duration_s'] = round(j.get('duration', 0), 1)
                r['samples'] = j.get('samples', '')
                r['health'] = j.get('health', '')
            except Exception:
                pass
        rows.append(r)

    hdr = (f"{'run':<22}{'extent':>11}{'occ%':>7}{'free%':>7}{'unk%':>7}"
           f"{'wall_m':>8}{'/perim':>8}{'dur_s':>8}")
    print(hdr); print('-' * len(hdr))
    for r in sorted(rows, key=lambda x: -x['occ_pct']):
        print(f"{r['run']:<22}{r['extent_m']:>11}{r['occ_pct']:>7.2f}{r['free_pct']:>7.2f}"
              f"{r['unk_pct']:>7.2f}{r['wall_m']:>8.1f}{r['wall_frac']:>8.2f}"
              f"{str(r['duration_s']):>8}")

    print(f"\n{len(rows)} runs, ranked by occupied-cell fraction — the criterion that")
    print("matters for AMCL, which localises against walls, not free space.")
    print("wall_m/perim above ~0.5 means the drive got round most of the boundary.")

    if args.csv:
        with open(args.csv, 'w', newline='') as fh:
            wtr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            wtr.writeheader(); wtr.writerows(rows)
        print(f'\nwrote {args.csv}')


if __name__ == '__main__':
    main()
