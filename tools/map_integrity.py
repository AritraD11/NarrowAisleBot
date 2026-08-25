#!/usr/bin/env python3
"""map_integrity.py — measure whether a saved map folded, instead of eyeballing it.

§17.32's acceptance gate is "map integrity + return-to-mark", and §17.34
closes with the integrity check still undone because it needs "eyes on the
grid, not more arithmetic". That is true of the arithmetic that existed.
This is different arithmetic: it looks for the *geometry* a false loop
closure leaves behind, which is exactly what an eye is looking for when it
scans a grid for a doubled wall.

The three failure signatures named in the acceptance gate, made countable:

  doubled wall     -> D2, the headline detector. Two near-parallel walls
                      with FREE space between them and a gap too narrow for
                      the robot to have driven down. The free cells are the
                      proof: something stood between the two walls and saw
                      through. If the gap is under the robot's own 0.48 m
                      width, that something cannot have been this robot, so
                      one of the two walls is a ghost of the other.
  fork             -> D3, junction count on the thinned wall skeleton. A
                      corridor that splits where the real one does not has a
                      branch point; a clean room outline is almost all
                      degree-2.
  corridor twice   -> D2 at long range plus D4's orientation histogram. A
                      chunk of map rotated a few degrees by a bad closure
                      puts a satellite peak next to the dominant wall axis.

Plus two supporting measures: D1 wall thickness (a fold that lands nearly on
top of itself fattens the wall rather than duplicating it) and D5 free-space
connectivity (a fold can strand free space outside the room outline).

WHAT THIS IS NOT. It does not know what the room looks like. Every threshold
below is provisional and is flagged as such in the output. The way they stop
being guesses is `--corpus` over the 70 maps in the archive: run the same
room many times, and the distribution tells you where "unusual" actually
sits. Until then, treat a verdict as a ranked reason to go look, not as a
replacement for looking.

    ./tools/map_integrity.py data/field_runs/run_20260825_151713.pgm
    ./tools/map_integrity.py --corpus data/field_runs
    ./tools/map_integrity.py run_20260825_151713.pgm --png annotated.png
    ./tools/map_integrity.py --selftest

Pure standard library, same as map_corpus.py — this has to run on the Pi and
on a Windows laptop with no numpy, no PIL and no PyYAML.
"""
import argparse
import csv
import json
import math
import re
import struct
import sys
import zlib
from collections import deque
from pathlib import Path

FREE, OCC, UNK = 0, 1, 2

# ── provisional thresholds ───────────────────────────────────────────────
# Named, in one place, because they are the part of this tool most likely to
# be wrong. --corpus prints the distribution that should replace them.
ROBOT_NARROW_M = 0.48       # the 1.12 x 0.48 m footprint's narrow dimension
DEF_MAX_GAP_M = 0.60        # doubled-wall search range; just over the width
DEF_MIN_GAP_M = 0.10        # below this it is wall thickness, not a pair
DEF_ANGLE_TOL = 20.0        # degrees; how parallel two walls must be
DEF_MIN_COHERENCE = 0.30    # below this the local patch is a blob, not a wall
DEF_TENSOR_R = 3            # structure-tensor window radius, cells

FLAG_DOUBLED_FRAC = 0.10    # >10% of wall cells doubled -> call it folded
SUSPECT_DOUBLED_FRAC = 0.03
SUSPECT_FORKS_PER_10M = 4.0
SUSPECT_THICK_P95_M = 0.30
SUSPECT_MANHATTAN = 0.55
SUSPECT_FREE_COMPONENTS = 2


# ═════════════════════════════════════════════════════════════════════════
#  Reading the map.  Lifted deliberately from map_corpus.py rather than
#  reimplemented: the 205-is-unknown and inverted-brightness details are
#  each a silent-corruption bug if got wrong, and that version is proven.
# ═════════════════════════════════════════════════════════════════════════
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
    if len(px) != w * h:
        raise ValueError(f'{path}: got {len(px)} pixels, header says {w}x{h}={w * h}')
    return w, h, maxval, px


def read_yaml(path):
    """The flat keys map_saver_cli writes. Not a general YAML parser and does
    not pretend to be — avoids a PyYAML dependency on the Pi."""
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


def classify(px, occ_thresh, free_thresh, negate=0):
    """map_saver_cli trinary: 205 = unknown, and the rest is INVERTED
    brightness, so occupancy = (255 - p)/255 while the yaml thresholds are on
    occupancy. Getting that backwards silently swaps free and occupied."""
    cls = bytearray(len(px))
    for n, p in enumerate(px):
        if negate:
            p = 255 - p
        if p == 205:
            cls[n] = UNK
            continue
        o = (255 - p) / 255.0
        if o >= occ_thresh:
            cls[n] = OCC
        elif o <= free_thresh:
            cls[n] = FREE
        else:
            cls[n] = UNK
    return cls


class Grid:
    """A classified occupancy grid plus the frame conversion.

    Image row 0 is the TOP of the picture and therefore the HIGHEST map y —
    OccupancyGrid row 0 is the lowest. §17.34 records this as one of the two
    details that silently corrupt a map write; it silently corrupts a map
    *read* the same way, so the conversion lives here and nowhere else.
    """

    def __init__(self, w, h, cls, res, origin):
        self.w, self.h, self.cls = w, h, cls
        self.res = res
        self.ox, self.oy = origin[0], origin[1]
        self.occ = [i for i, c in enumerate(cls) if c == OCC]

    def at(self, r, c):
        if 0 <= r < self.h and 0 <= c < self.w:
            return self.cls[r * self.w + c]
        return UNK                      # off-map reads as unmeasured, not free

    def rc(self, i):
        return divmod(i, self.w)

    def to_map(self, r, c):
        return (self.ox + (c + 0.5) * self.res,
                self.oy + (self.h - 1 - r + 0.5) * self.res)


def load(pgm_path):
    pgm_path = Path(pgm_path)
    yml_path = pgm_path.with_suffix('.yaml')
    w, h, _, px = read_pgm(pgm_path)
    meta = read_yaml(yml_path) if yml_path.exists() else {}
    cls = classify(px, meta.get('occupied_thresh', 0.65),
                   meta.get('free_thresh', 0.196), int(meta.get('negate', 0) or 0))
    return Grid(w, h, cls, meta.get('resolution', 0.05),
                meta.get('origin', [0.0, 0.0, 0.0]))


# ═════════════════════════════════════════════════════════════════════════
#  Local wall orientation — the primitive the rest is built on
# ═════════════════════════════════════════════════════════════════════════
def orientations(g, radius=DEF_TENSOR_R):
    """Per-occupied-cell wall direction and how line-like the patch is.

    Second moments of the occupied neighbours inside a (2r+1)^2 window. The
    principal axis is the wall direction; the normalised anisotropy is how
    much we should believe it. A corner or a blob comes out near 0 and gets
    excluded from the parallelism test, which is what stops furniture being
    reported as a doubled wall.

    Angles are in IMAGE coordinates (+col right, +row down). Map-frame angle
    is the negation, because row increases as map y decreases. Only the
    reported dominant axis converts; everything internal stays in image
    space, where parallel is parallel either way.
    """
    out = {}
    for i in g.occ:
        r, c = g.rc(i)
        sxx = syy = sxy = 0.0
        n = 0
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                if dr == 0 and dc == 0:
                    continue
                if g.at(r + dr, c + dc) == OCC:
                    sxx += dc * dc
                    syy += dr * dr
                    sxy += dc * dr
                    n += 1
        if n < 3:
            continue
        tr = sxx + syy
        if tr <= 0:
            continue
        coh = math.hypot(sxx - syy, 2 * sxy) / tr
        theta = 0.5 * math.atan2(2 * sxy, sxx - syy)
        out[i] = (theta, coh, n)
    return out


def _march(g, r, c, nr, nc, max_steps):
    """Walk outward from (r,c) along a unit normal, yielding each new cell.

    Half-cell steps then de-duplicated, so a near-diagonal normal does not
    tunnel through a one-cell-thick wall and report the far side of it as a
    separate wall — which would manufacture doubled walls out of nothing.
    """
    seen = (r, c)
    t = 0.5
    while t <= max_steps:
        rr, cc = int(round(r + t * nr)), int(round(c + t * nc))
        if (rr, cc) != seen:
            seen = (rr, cc)
            if not (0 <= rr < g.h and 0 <= cc < g.w):
                return
            yield rr, cc
        t += 0.5


# ═════════════════════════════════════════════════════════════════════════
#  D1  wall thickness
# ═════════════════════════════════════════════════════════════════════════
def wall_thickness(g, ori, cap=24):
    """Occupied run length across the wall, measured along its own normal.

    A fold that lands nearly on top of itself does not duplicate the wall, it
    fattens it — so thickness catches the near-miss case that D2's
    free-space-between requirement deliberately excludes.
    """
    th = {}
    for i in g.occ:
        r, c = g.rc(i)
        if i in ori:
            theta, _, _ = ori[i]
            nr, nc = math.cos(theta), -math.sin(theta)   # normal = axis + 90
        else:
            nr, nc = 1.0, 0.0
        n = 1
        for sgn in (1, -1):
            for rr, cc in _march(g, r, c, sgn * nr, sgn * nc, cap):
                if g.at(rr, cc) != OCC:
                    break
                n += 1
                if n >= cap:
                    break
        th[i] = n
    return th


# ═════════════════════════════════════════════════════════════════════════
#  D2  doubled walls — the headline detector
# ═════════════════════════════════════════════════════════════════════════
def doubled_walls(g, ori, max_gap_m=DEF_MAX_GAP_M, min_gap_m=DEF_MIN_GAP_M,
                  angle_tol=DEF_ANGLE_TOL, min_coh=DEF_MIN_COHERENCE):
    """Find wall cells that have a near-parallel twin across a narrow gap of
    free space.

    The argument, stated so it can be attacked:

      1. The cells between the two walls are FREE, not UNKNOWN. Free means
         the LiDAR returned through that space — the robot observed it empty.
      2. The gap is narrower than the robot's own 0.48 m width, so the robot
         cannot have driven between them.
      3. A wall's far face is only observable from the far side.

    Two walls the robot saw both faces of, with a gap it cannot fit through,
    is the geometry a false loop closure produces when it fuses two poses
    that are not the same pose.

    The honest hole in it: a genuine narrow gap between two shelves, viewed
    end-on down its length, also shows free space between two parallel faces.
    That is why the flagged cells are clustered and reported with map
    coordinates rather than just counted — a real end-on gap is one place you
    can go and look at, a fold is a wall's whole length duplicated.
    """
    max_steps = max_gap_m / g.res + 4
    min_free = max(1, int(round(min_gap_m / g.res)))
    flagged = {}                                   # i -> gap in metres
    for i in g.occ:
        if i in flagged or i not in ori:
            continue
        theta, coh, _ = ori[i]
        if coh < min_coh:
            continue
        r, c = g.rc(i)
        nr, nc = math.cos(theta), -math.sin(theta)
        for sgn in (1, -1):
            n_free = 0
            left_own_wall = False
            for rr, cc in _march(g, r, c, sgn * nr, sgn * nc, max_steps):
                v = g.at(rr, cc)
                if v == UNK:
                    break                          # unmeasured: proves nothing
                if v == FREE:
                    left_own_wall = True
                    n_free += 1
                    if n_free * g.res > max_gap_m:
                        break
                    continue
                # occupied
                if not left_own_wall:
                    continue                       # still crossing our own wall
                if n_free < min_free:
                    break
                j = rr * g.w + cc
                if j not in ori or ori[j][1] < min_coh:
                    break
                d = abs(math.degrees(theta - ori[j][0])) % 180.0
                if min(d, 180.0 - d) <= angle_tol:
                    gap = n_free * g.res
                    flagged[i] = gap
                    flagged[j] = gap
                break
            if i in flagged:
                break
    return flagged


def cluster(g, cells, min_size=4, link=2):
    """Group flagged cells into runs of wall, largest first.

    Counting flagged cells alone cannot separate one duplicated wall from
    scattered noise. Clusters can, and their centroids are somewhere the user
    can actually point map_viewer.html at.

    Linked at Chebyshev distance `link` rather than 8-connected, because a
    real scan drops the occasional cell out of a wall and a one-cell hole
    would otherwise cut one 4 m ghost into five unimpressive fragments. It
    stays well below the gap being measured, so a wall and its own ghost are
    still reported as the two separate walls they are.
    """
    todo = set(cells)
    out = []
    while todo:
        seed = todo.pop()
        comp = [seed]
        q = deque([seed])
        while q:
            i = q.popleft()
            r, c = g.rc(i)
            for dr in range(-link, link + 1):
                for dc in range(-link, link + 1):
                    rr, cc = r + dr, c + dc
                    if not (0 <= rr < g.h and 0 <= cc < g.w):
                        continue
                    j = rr * g.w + cc
                    if j in todo:
                        todo.discard(j)
                        comp.append(j)
                        q.append(j)
        if len(comp) >= min_size:
            rs = [g.rc(i)[0] for i in comp]
            cs = [g.rc(i)[1] for i in comp]
            mr, mc = sum(rs) / len(rs), sum(cs) / len(cs)
            x, y = g.to_map(mr, mc)
            out.append({'cells': len(comp),
                        'length_m': round(len(comp) * g.res, 2),
                        'map_x': round(x, 2), 'map_y': round(y, 2),
                        'gap_m': round(sum(cells[i] for i in comp) / len(comp), 2)})
    return sorted(out, key=lambda d: -d['cells'])


# ═════════════════════════════════════════════════════════════════════════
#  D3  forks — Zhang-Suen thinning, then crossing numbers
# ═════════════════════════════════════════════════════════════════════════
_RING = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]


def _ring(skel, w, h, r, c):
    return [1 if (0 <= r + dr < h and 0 <= c + dc < w
                  and ((r + dr) * w + (c + dc)) in skel) else 0
            for dr, dc in _RING]


def _crossings(p):
    return sum(1 for k in range(8) if p[k] == 0 and p[(k + 1) % 8] == 1)


def skeleton(g):
    """Thin the occupied set to one-cell-wide centrelines.

    Works over the live pixel set rather than rescanning the whole raster
    each pass, because a warehouse map is mostly empty and the occupied
    fraction here is ~2%.
    """
    skel = set(g.occ)
    changed = True
    passes = 0
    while changed and passes < 64:
        changed = False
        passes += 1
        for sub in (0, 1):
            doomed = []
            for i in skel:
                r, c = g.rc(i)
                p = _ring(skel, g.w, g.h, r, c)
                b = sum(p)
                if not (2 <= b <= 6):
                    continue
                if _crossings(p) != 1:
                    continue
                # p[0]=N p[2]=E p[4]=S p[6]=W
                if sub == 0:
                    if p[0] * p[2] * p[4] or p[2] * p[4] * p[6]:
                        continue
                else:
                    if p[0] * p[2] * p[6] or p[0] * p[4] * p[6]:
                        continue
                doomed.append(i)
            if doomed:
                skel.difference_update(doomed)
                changed = True
    return skel


def fork_stats(g, skel):
    junctions, endpoints = [], []
    for i in skel:
        r, c = g.rc(i)
        p = _ring(skel, g.w, g.h, r, c)
        b = sum(p)
        if b == 1:
            endpoints.append(i)
        elif _crossings(p) >= 3:
            junctions.append(i)
    return junctions, endpoints


# ═════════════════════════════════════════════════════════════════════════
#  D4  orientation coherence
# ═════════════════════════════════════════════════════════════════════════
def orientation_hist(g, ori, min_coh=DEF_MIN_COHERENCE):
    """Wall-angle histogram folded modulo 90 degrees.

    A rectilinear room puts nearly everything in one bin. A closure that
    rotates part of the map by a few degrees leaves the rest where it was and
    puts a satellite peak beside the dominant one — which is the same event
    as "the corridor appears twice", seen in angle rather than in position.

    Low coherence is meaningless for a curved or angled site. Compare this
    across runs of the SAME room, not against an absolute.
    """
    bins = [0.0] * 90
    total = 0.0
    for i, (theta, coh, _) in ori.items():
        if coh < min_coh:
            continue
        deg = math.degrees(theta) % 90.0
        bins[int(deg) % 90] += coh
        total += coh
    if total <= 0:
        return None
    sm = [(bins[(k - 1) % 90] + bins[k] + bins[(k + 1) % 90]) for k in range(90)]
    peak = max(range(90), key=lambda k: sm[k])

    def circ(a, b):
        d = abs(a - b) % 90
        return min(d, 90 - d)

    near = sum(bins[k] for k in range(90) if circ(k, peak) <= 10)
    cand = [k for k in range(90) if circ(k, peak) >= 3]
    sec = max(cand, key=lambda k: sm[k]) if cand else None
    return {
        # map frame negates the image-frame angle (row grows as y shrinks)
        'dominant_deg': round(-((peak + 0.5) - 90 if peak > 45 else peak + 0.5), 1),
        'manhattan_frac': round(near / total, 3),
        'secondary_offset_deg': round(circ(sec, peak), 1) if sec is not None else None,
        'secondary_rel': round(sm[sec] / sm[peak], 3) if sec is not None and sm[peak] else None,
    }


# ═════════════════════════════════════════════════════════════════════════
#  D5  free-space connectivity
# ═════════════════════════════════════════════════════════════════════════
def free_components(g, min_cells=20):
    seen = bytearray(g.w * g.h)
    sizes = []
    for start in range(g.w * g.h):
        if seen[start] or g.cls[start] != FREE:
            continue
        n = 0
        q = deque([start])
        seen[start] = 1
        while q:
            i = q.popleft()
            n += 1
            r, c = divmod(i, g.w)
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < g.h and 0 <= cc < g.w:
                    j = rr * g.w + cc
                    if not seen[j] and g.cls[j] == FREE:
                        seen[j] = 1
                        q.append(j)
        sizes.append(n)
    sizes.sort(reverse=True)
    big = [s for s in sizes if s >= min_cells]
    return big


# ═════════════════════════════════════════════════════════════════════════
#  Analysis
# ═════════════════════════════════════════════════════════════════════════
def analyse(pgm_path, args):
    g = load(pgm_path)
    n_occ = len(g.occ)
    n_free = sum(1 for c in g.cls if c == FREE)
    n_unk = g.w * g.h - n_occ - n_free
    res = {
        'run': Path(pgm_path).stem,
        'w': g.w, 'h': g.h, 'res': g.res,
        'extent_m': f'{g.w * g.res:.1f}x{g.h * g.res:.1f}',
        'occupied': n_occ, 'free': n_free, 'unknown': n_unk,
        'wall_m': round(n_occ * g.res, 1),
    }
    if n_occ < 20:
        res.update({'verdict': 'NO WALLS', 'flags': ['fewer than 20 occupied cells'],
                    'doubled_frac': 0.0})
        return res, g, {}, set(), []

    ori = orientations(g, args.tensor_radius)
    th = wall_thickness(g, ori)
    dbl = doubled_walls(g, ori, args.max_gap, args.min_gap,
                        args.angle_tol, args.min_coherence)
    skel = skeleton(g)
    junc, ends = fork_stats(g, skel)
    hist = orientation_hist(g, ori, args.min_coherence)
    comps = free_components(g)

    tvals = sorted(th.values())
    p95 = tvals[min(len(tvals) - 1, int(0.95 * len(tvals)))]
    wall_10m = max(n_occ * g.res / 10.0, 1e-6)

    res.update({
        'doubled_cells': len(dbl),
        'doubled_frac': round(len(dbl) / n_occ, 4),
        'doubled_clusters': cluster(g, dbl)[:5],
        'thick_median_m': round(tvals[len(tvals) // 2] * g.res, 3),
        'thick_p95_m': round(p95 * g.res, 3),
        'skeleton_cells': len(skel),
        'junctions': len(junc),
        'endpoints': len(ends),
        'junctions_per_10m': round(len(junc) / wall_10m, 2),
        'endpoints_per_10m': round(len(ends) / wall_10m, 2),
        'free_components': len(comps),
        'free_largest_frac': round(comps[0] / max(sum(comps), 1), 3) if comps else 0.0,
    })
    res.update(hist or {'dominant_deg': None, 'manhattan_frac': None,
                        'secondary_offset_deg': None, 'secondary_rel': None})

    flags = []
    if res['doubled_frac'] >= FLAG_DOUBLED_FRAC:
        flags.append(f"doubled walls on {res['doubled_frac']:.0%} of wall cells")
    elif res['doubled_frac'] >= SUSPECT_DOUBLED_FRAC:
        flags.append(f"doubled walls on {res['doubled_frac']:.0%} of wall cells (marginal)")
    if res['junctions_per_10m'] > SUSPECT_FORKS_PER_10M:
        flags.append(f"{res['junctions_per_10m']} skeleton junctions per 10 m of wall")
    if res['thick_p95_m'] > SUSPECT_THICK_P95_M:
        flags.append(f"95th-percentile wall thickness {res['thick_p95_m']} m")
    if res['manhattan_frac'] is not None and res['manhattan_frac'] < SUSPECT_MANHATTAN:
        flags.append(f"only {res['manhattan_frac']:.0%} of wall within 10 deg of the dominant axis")
    if res['free_components'] >= SUSPECT_FREE_COMPONENTS:
        flags.append(f"{res['free_components']} disconnected regions of free space")

    if res['doubled_frac'] >= FLAG_DOUBLED_FRAC or len(flags) >= 3:
        res['verdict'] = 'FOLDED'
    elif flags:
        res['verdict'] = 'SUSPECT'
    else:
        res['verdict'] = 'CLEAN'
    res['flags'] = flags
    return res, g, dbl, skel, junc


# ═════════════════════════════════════════════════════════════════════════
#  Annotated PNG — so the number and the picture can be checked against
#  each other.  Pure zlib+struct; no PIL on the Pi or on Windows.
# ═════════════════════════════════════════════════════════════════════════
PAL = {FREE: (248, 250, 252), OCC: (10, 14, 23), UNK: (26, 35, 50)}
C_DOUBLED = (220, 38, 38)
C_JUNCTION = (245, 158, 11)


def write_png(path, g, dbl, junc, scale=4):
    w, h = g.w * scale, g.h * scale
    rows = []
    for r in range(g.h):
        row = bytearray()
        for c in range(g.w):
            i = r * g.w + c
            if i in dbl:
                rgb = C_DOUBLED
            elif i in junc:
                rgb = C_JUNCTION
            else:
                rgb = PAL[g.cls[i]]
            row += bytes(rgb) * scale
        rows.extend([bytes(row)] * scale)
    raw = b''.join(b'\x00' + r for r in rows)

    def chunk(tag, data):
        body = tag + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body) & 0xffffffff)

    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw, 9))
           + chunk(b'IEND', b''))
    Path(path).write_bytes(png)
    return len(png)


# ═════════════════════════════════════════════════════════════════════════
#  Self-test — synthetic clean room vs synthetic folded room
#
#  §17.34 round-tripped a synthetic grid through map_corpus.py before it went
#  near the robot. Same standard here: a detector that has never been shown a
#  fold it is known to contain has not been tested, it has only been run.
# ═════════════════════════════════════════════════════════════════════════
def _synth(mode, w=140, h=140, res=0.05):
    """A room with a known answer.

    Every case is a claim the detector makes, written down so it can fail:
    the fold must be found, and the two things that most resemble a fold
    without being one must not be.
    """
    cls = bytearray([UNK] * (w * h))

    def rect(r0, r1, c0, c1, v):
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if 0 <= r < h and 0 <= c < w:
                    cls[r * w + c] = v

    def hline(r, c0, c1):
        for c in range(c0, c1 + 1):
            cls[r * w + c] = OCC

    def vline(c, r0, r1):
        for r in range(r0, r1 + 1):
            cls[r * w + c] = OCC

    rect(20, 120, 20, 120, FREE)
    hline(20, 20, 120)
    hline(120, 20, 120)
    vline(20, 20, 120)
    vline(120, 20, 120)

    if mode == 'fold':
        # A ghost of the top wall 7 free cells (0.35 m) below it. That is the
        # geometry a closure produces when it fuses two poses a third of a
        # metre apart — the scale of §17.32's measured 39.57 cm map->odom jump.
        hline(28, 30, 110)
    elif mode == 'unknown_gap':
        # Two parallel walls 0.30 m apart with UNKNOWN between them, outside
        # the observed room. Nothing ever saw through that space, so the
        # free-space argument does not apply and this must NOT be flagged.
        # This is the test of the discriminator, not of the geometry.
        hline(6, 30, 110)
        hline(12, 30, 110)
    elif mode == 'aisle':
        # A real aisle 0.85 m wide: free between two parallel walls, but wide
        # enough for a 0.48 m robot to have driven down. Must NOT be flagged.
        vline(38, 25, 115)
    elif mode == 'thickwall':
        # A genuinely 3-cell-thick wall. No free space inside it, so D2 must
        # stay silent and only D1 should have anything to say.
        hline(21, 20, 120)
        hline(22, 20, 120)
    return Grid(w, h, cls, res, [0.0, 0.0, 0.0])


# mode, must-flag, note
_CASES = [
    ('clean', False, 'bare rectangular room'),
    ('fold', True, 'ghost wall 0.35 m below the real one, free between'),
    ('unknown_gap', False, 'parallel walls 0.30 m apart with UNKNOWN between'),
    ('aisle', False, 'real 0.85 m aisle, free between'),
    ('thickwall', False, '3-cell-thick wall, no free space inside it'),
]


def selftest(args):
    ok = True
    for mode, must_flag, note in _CASES:
        g = _synth(mode)
        ori = orientations(g, args.tensor_radius)
        dbl = doubled_walls(g, ori, args.max_gap, args.min_gap,
                            args.angle_tol, args.min_coherence)
        frac = len(dbl) / max(len(g.occ), 1)
        cl = cluster(g, dbl)
        skel = skeleton(g)
        junc, ends = fork_stats(g, skel)
        hist = orientation_hist(g, ori, args.min_coherence)
        th = wall_thickness(g, ori)
        tv = sorted(th.values())
        p95 = tv[min(len(tv) - 1, int(0.95 * len(tv)))] * g.res

        print(f'  {mode:<12} {note}')
        print(f'  {"":<12} {len(g.occ):4d} wall cells, {len(dbl):4d} doubled ({frac:5.1%}), '
              f'{len(junc)} junctions, {len(ends)} endpoints')
        print(f'  {"":<12} thickness p95 {p95:.2f} m, manhattan '
              f'{hist["manhattan_frac"]:.2f}' if hist else '')
        if cl:
            print(f'  {"":<12} largest cluster {cl[0]["cells"]} cells, gap '
                  f'{cl[0]["gap_m"]} m at map ({cl[0]["map_x"]}, {cl[0]["map_y"]})')

        flagged = frac >= SUSPECT_DOUBLED_FRAC
        if must_flag and not flagged:
            print(f'  {"":<12} FAIL: a known fold was not flagged')
            ok = False
        elif must_flag and (not cl or cl[0]['cells'] < 40):
            print(f'  {"":<12} FAIL: fold found but not clustered as one wall')
            ok = False
        elif not must_flag and flagged:
            print(f'  {"":<12} FAIL: flagged as doubled when it is not')
            ok = False
        if mode == 'clean':
            if len(junc) > 2:
                print(f'  {"":<12} FAIL: a bare rectangle should have no junctions')
                ok = False
            if hist['manhattan_frac'] < 0.8:
                print(f'  {"":<12} FAIL: an axis-aligned rectangle is not Manhattan')
                ok = False
        if mode == 'thickwall' and p95 < 0.10:
            print(f'  {"":<12} FAIL: D1 did not see a 3-cell wall as thick')
            ok = False
        print()

    print('selftest:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


# ═════════════════════════════════════════════════════════════════════════
#  Output
# ═════════════════════════════════════════════════════════════════════════
def print_report(r):
    v = r['verdict']
    print(f"\n{'=' * 68}\n  {r['run']}   ->   {v}\n{'=' * 68}")
    print(f"  grid          {r['w']}x{r['h']} @ {r['res']} m = {r['extent_m']} m")
    print(f"  cells         {r['occupied']} occupied / {r['free']} free / {r['unknown']} unknown")
    print(f"  wall          {r['wall_m']} m of occupied cells")
    if v == 'NO WALLS':
        print('\n  Nothing to check: the map has essentially no occupied cells.')
        print('  Not a fold — a drive that never got close enough to a wall.')
        return
    print()
    print(f"  D1 thickness  median {r['thick_median_m']} m, p95 {r['thick_p95_m']} m")
    print(f"  D2 doubled    {r['doubled_cells']} cells ({r['doubled_frac']:.1%} of wall)")
    for c in r['doubled_clusters']:
        print(f"       cluster   {c['cells']:4d} cells ~{c['length_m']} m of wall, "
              f"gap {c['gap_m']} m, at map ({c['map_x']}, {c['map_y']})")
    print(f"  D3 forks      {r['junctions']} junctions ({r['junctions_per_10m']}/10 m), "
          f"{r['endpoints']} endpoints ({r['endpoints_per_10m']}/10 m)")
    mf = r['manhattan_frac']
    print(f"  D4 alignment  dominant axis {r['dominant_deg']} deg, "
          f"manhattan {mf if mf is None else format(mf, '.2f')}"
          + (f", secondary peak +{r['secondary_offset_deg']} deg "
             f"at {r['secondary_rel']:.2f} relative"
             if r.get('secondary_offset_deg') is not None else ''))
    print(f"  D5 free space {r['free_components']} regions, "
          f"largest holds {r['free_largest_frac']:.1%}")
    if r['flags']:
        print('\n  flags:')
        for f in r['flags']:
            print(f'    - {f}')
    else:
        print('\n  no flags raised')
    print()
    if v == 'CLEAN':
        print('  No fold signature found. This clears the map-integrity half of')
        print("  §17.32's gate. Return-to-mark is the other half and is not")
        print('  measurable from a .pgm — read it off the dashboard HUD.')
    elif v == 'SUSPECT':
        print('  Go look at the flagged locations in docs/tools/map_viewer.html')
        print('  before accepting this map. --png writes the same picture with')
        print('  the flagged cells in red.')
    else:
        print('  Treat this map as unusable for AMCL and redo the drive.')
    print('\n  Thresholds are provisional (see the header). --corpus over the')
    print('  archived runs is what turns them from guesses into percentiles.')


CORPUS_COLS = ['run', 'verdict', 'extent_m', 'occupied', 'wall_m', 'doubled_frac',
               'doubled_cells', 'thick_median_m', 'thick_p95_m', 'junctions',
               'junctions_per_10m', 'endpoints', 'manhattan_frac', 'dominant_deg',
               'free_components']


def print_corpus(rows):
    hdr = (f"{'run':<22}{'verdict':>9}{'wall_m':>8}{'dbl%':>7}{'thk95':>7}"
           f"{'junc/10m':>10}{'manh':>7}{'free#':>7}")
    print(hdr)
    print('-' * len(hdr))
    for r in sorted(rows, key=lambda x: (x.get('doubled_frac') or 0, -(x.get('wall_m') or 0)),
                    reverse=True):
        mf = r.get('manhattan_frac')
        print(f"{r['run']:<22}{r['verdict']:>9}{r.get('wall_m', 0):>8.1f}"
              f"{100 * (r.get('doubled_frac') or 0):>7.1f}"
              f"{r.get('thick_p95_m') or 0:>7.2f}{r.get('junctions_per_10m') or 0:>10.2f}"
              f"{(mf if mf is not None else float('nan')):>7.2f}"
              f"{r.get('free_components', 0):>7d}")
    print()
    for key, label in (('doubled_frac', 'doubled fraction'),
                       ('junctions_per_10m', 'junctions / 10 m'),
                       ('thick_p95_m', 'thickness p95 (m)'),
                       ('manhattan_frac', 'manhattan fraction')):
        vals = sorted(v for v in (r.get(key) for r in rows) if v is not None)
        if len(vals) < 3:
            continue
        def q(p):
            return vals[min(len(vals) - 1, int(p * len(vals)))]
        print(f"  {label:<22} min {vals[0]:.3f}   median {q(0.5):.3f}   "
              f"p90 {q(0.9):.3f}   max {vals[-1]:.3f}")
    print('\n  Those percentiles, not the constants at the top of this file,')
    print('  are what a threshold should be set from once the corpus is in.')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('target', nargs='?', help='a run_<stamp>.pgm, or a folder with --corpus')
    ap.add_argument('--corpus', action='store_true', help='treat target as a folder of runs')
    ap.add_argument('--png', help='write an annotated PNG (single-map mode)')
    ap.add_argument('--png-scale', type=int, default=4)
    ap.add_argument('--json', help='write the full result as JSON')
    ap.add_argument('--csv', help='write the corpus table as CSV')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--max-gap', type=float, default=DEF_MAX_GAP_M,
                    help=f'doubled-wall search range, m (default {DEF_MAX_GAP_M}; '
                         f'robot is {ROBOT_NARROW_M} m wide)')
    ap.add_argument('--min-gap', type=float, default=DEF_MIN_GAP_M)
    ap.add_argument('--angle-tol', type=float, default=DEF_ANGLE_TOL)
    ap.add_argument('--min-coherence', type=float, default=DEF_MIN_COHERENCE)
    ap.add_argument('--tensor-radius', type=int, default=DEF_TENSOR_R)
    args = ap.parse_args()

    if args.selftest:
        return selftest(args)
    if not args.target:
        ap.error('need a .pgm, a folder with --corpus, or --selftest')

    target = Path(args.target)
    if args.corpus or target.is_dir():
        if not target.is_dir():
            sys.exit(f'not a directory: {target}')
        pgms = sorted(f for f in target.iterdir()
                      if re.match(r'run_\d{8}_\d{6}\.pgm$', f.name))
        if not pgms:
            sys.exit(f'no run_*.pgm found in {target}')
        rows = []
        for p in pgms:
            try:
                r, *_ = analyse(p, args)
                rows.append(r)
            except Exception as exc:
                print(f'  !! {p.name}: {exc}', file=sys.stderr)
        print_corpus(rows)
        if args.csv:
            with open(args.csv, 'w', newline='') as fh:
                wtr = csv.DictWriter(fh, fieldnames=CORPUS_COLS, extrasaction='ignore')
                wtr.writeheader()
                wtr.writerows(rows)
            print(f'  wrote {args.csv}')
        if args.json:
            Path(args.json).write_text(json.dumps(rows, indent=2))
            print(f'  wrote {args.json}')
        return 0

    r, g, dbl, skel, junc = analyse(target, args)
    print_report(r)
    if args.png:
        n = write_png(args.png, g, dbl, set(junc), args.png_scale)
        print(f'  wrote {args.png} ({n} bytes) — red = doubled wall, amber = fork')
    if args.json:
        Path(args.json).write_text(json.dumps(r, indent=2))
        print(f'  wrote {args.json}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
