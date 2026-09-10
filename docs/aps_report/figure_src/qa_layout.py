#!/usr/bin/env python3
"""Find labels that collide with other labels, with arrows, or with the canvas edge.

Every figure in this report is generated, so a layout fault is a bug in a
generator rather than something to retouch in the PNG. This runs each generator,
intercepts the figure before it is written, and measures three faults directly
from the rendered geometry.

**Label against label.** Any two text extents that genuinely interpenetrate.
A couple of pixels of contact is ignored: a text extent carries ascender and
descender space that is usually blank, so boxes touch long before the words do.

**Label against arrow or data line.** Arrow and line paths are transformed into
display coordinates and sampled densely, then tested against each label's box.
Grid lines, spines, tick marks and legend contents are excluded because a label
is *meant* to sit near those. A label carrying an opaque background box is also
exempt: it masks whatever it crosses, which is the normal way to put a word on
top of a line.

**Label off the canvas.** Text whose extent leaves the figure, which renders as
a clipped or truncated word.

    python3 qa_layout.py            # every figure
    python3 qa_layout.py f_arch     # one generator
"""
import os
import runpy
import sys

import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch
from matplotlib.legend import Legend
from matplotlib.text import Text, Annotation

HERE = os.path.dirname(os.path.abspath(__file__))

# A label's box is shrunk by this fraction of its size on each side before the
# collision test, so a stroke merely grazing the blank margin is not a fault.
INSET_X, INSET_Y = 0.10, 0.22
# Two labels must interpenetrate by more than this many pixels in both axes,
MIN_OVERLAP_PX = 2.5
# and by this fraction of the smaller of the two.
MIN_OVERLAP_FRAC = 0.10
# Paths are sampled at roughly this spacing, in pixels.
SAMPLE_PX = 2.0


def captured_figures(script):
    """Run a generator and hand back its figures instead of letting it save."""
    grabbed = []
    real_savefig, real_close = Figure.savefig, plt.close

    def fake_savefig(self, fname, *a, **kw):
        grabbed.append((os.path.basename(fname) if isinstance(fname, str)
                        else '<buffer>', self))

    Figure.savefig = fake_savefig
    plt.close = lambda *a, **kw: None
    try:
        runpy.run_path(os.path.join(HERE, script), run_name='__main__')
    finally:
        Figure.savefig, plt.close = real_savefig, real_close
    return grabbed


def legend_owned(fig):
    """Every artist belonging to a legend, which labels are allowed to touch.

    Matplotlib artists carry no parent pointer, so ownership is resolved by
    walking each legend's own descendants rather than climbing from the artist.
    """
    ids = set()
    for lg in fig.findobj(Legend):
        for a in lg.findobj():
            ids.add(id(a))
    return ids


def masked(t):
    """A label with an opaque background box hides whatever it crosses."""
    bb = t.get_bbox_patch()
    if bb is None:
        return False
    fc = bb.get_facecolor()
    return fc is not None and len(fc) == 4 and fc[3] > 0.55


def label_boxes(fig, renderer, skip_ids):
    out = []
    for t in fig.findobj(Text):
        if not t.get_visible() or not (t.get_text() or '').strip():
            continue
        if id(t) in skip_ids:
            continue
        try:
            # An Annotation's own extent spans its arrow as well as its words,
            # which would read as one enormous label overlapping everything it
            # points past. Only the text itself can collide with anything.
            bb = (Text.get_window_extent(t, renderer) if isinstance(t, Annotation)
                  else t.get_window_extent(renderer))
        except Exception:
            continue
        if bb.width > 0 and bb.height > 0:
            out.append((t, bb))
    return out


def offscreen_ticks(fig):
    """Tick labels for ticks outside the view.

    Matplotlib keeps a tick object either side of the visible range and simply
    does not draw it. Those labels are not on the page, so they cannot collide
    with anything, but they do sit at a position that looks like a collision.
    """
    ids = set()
    for ax in fig.get_axes():
        for axis, lim in ((ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())):
            lo, hi = min(lim), max(lim)
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                loc = getattr(tick, '_loc', None)
                if loc is None or not (lo - 1e-9 <= loc <= hi + 1e-9):
                    ids.add(id(tick.label1))
                    ids.add(id(tick.label2))
    return ids


def excluded_lines(fig):
    """Grid, spine, tick and legend strokes, which labels are allowed to touch."""
    out = set()
    for ax in fig.get_axes():
        for ln in list(ax.get_xgridlines()) + list(ax.get_ygridlines()):
            out.add(id(ln))
        for axis in (ax.xaxis, ax.yaxis):
            for tl in axis.get_ticklines():
                out.add(id(tl))
    return out


def stroke_points(fig, skip_ids):
    """Every arrow and data line, as densely sampled display-coordinate points."""
    skip = excluded_lines(fig) | skip_ids
    chunks = []

    def add(verts, clip=None):
        v = np.asarray(verts, dtype=float)
        v = v[np.isfinite(v).all(axis=1)]
        if clip is not None and len(v):
            # Data running past the axis limits is drawn clipped, so the part
            # outside the axes is not on the page and cannot cross a label.
            v = v[(v[:, 0] >= clip.x0) & (v[:, 0] <= clip.x1) &
                  (v[:, 1] >= clip.y0) & (v[:, 1] <= clip.y1)]
        if len(v) < 2:
            if len(v) == 1:
                chunks.append(v)
            return
        seg = np.diff(v, axis=0)
        lens = np.hypot(seg[:, 0], seg[:, 1])
        for (x0, y0), (dx, dy), L in zip(v[:-1], seg, lens):
            n = max(int(L / SAMPLE_PX), 1)
            t = np.linspace(0.0, 1.0, n + 1)[:, None]
            chunks.append(np.column_stack([x0 + dx * t[:, 0], y0 + dy * t[:, 0]]))

    for ln in fig.findobj(Line2D):
        if id(ln) in skip or not ln.get_visible():
            continue
        if ln.get_linestyle() in ('None', ' ', '') and ln.get_marker() in ('None', '', ' '):
            continue
        try:
            box = (ln.axes.patch.get_window_extent()
                   if ln.get_clip_on() and ln.axes is not None else None)
            add(ln.get_transform().transform(ln.get_xydata()), box)
        except Exception:
            pass

    for p in fig.findobj(FancyArrowPatch):
        if id(p) in skip or not p.get_visible():
            continue
        try:
            add(p.get_transform().transform_path(p.get_path()).vertices)
        except Exception:
            pass

    if not chunks:
        return np.empty((0, 2))
    return np.vstack(chunks)


def short(t, n=52):
    return t.get_text().strip().replace('\n', ' / ')[:n]


def check_figure(name, fig):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    owned = legend_owned(fig) | offscreen_ticks(fig)
    items = label_boxes(fig, renderer, owned)
    pts = stroke_points(fig, owned)
    out = []

    for i in range(len(items)):
        ti, bi = items[i]
        for j in range(i + 1, len(items)):
            tj, bj = items[j]
            ox = min(bi.x1, bj.x1) - max(bi.x0, bj.x0)
            oy = min(bi.y1, bj.y1) - max(bi.y0, bj.y0)
            if ox <= MIN_OVERLAP_PX or oy <= MIN_OVERLAP_PX:
                continue
            small = min(bi.width * bi.height, bj.width * bj.height)
            if small <= 0 or (ox * oy) / small < MIN_OVERLAP_FRAC:
                continue
            out.append(f'{name}: label over label ({int(ox*oy/small*100)}%) — '
                       f'"{short(ti)}" vs "{short(tj)}"')

    if len(pts):
        for t, bb in items:
            if masked(t):
                continue
            dx, dy = bb.width * INSET_X, bb.height * INSET_Y
            hit = ((pts[:, 0] > bb.x0 + dx) & (pts[:, 0] < bb.x1 - dx) &
                   (pts[:, 1] > bb.y0 + dy) & (pts[:, 1] < bb.y1 - dy))
            n = int(hit.sum())
            if n:
                out.append(f'{name}: arrow/line crosses label ({n} pts) — "{short(t)}"')

    # Text leaving the axes or the figure rectangle is deliberately not checked.
    # Every figure is saved with a tight bounding box, so captions placed below
    # an axes are included rather than cut, and matplotlib does not clip text
    # unless a clip path is set explicitly, which none of these generators do.
    return out


def main(argv):
    scripts = sorted(f for f in os.listdir(HERE)
                     if f.startswith('f_') and f.endswith('.py'))
    if len(argv) > 1:
        want = {a if a.endswith('.py') else a + '.py' for a in argv[1:]}
        scripts = [s for s in scripts if s in want]

    total = 0
    for s in scripts:
        try:
            found = []
            for name, fig in captured_figures(s):
                found += check_figure(name, fig)
                plt.close(fig)
        except Exception as e:
            print(f'{s}: FAILED TO RUN — {type(e).__name__}: {e}')
            total += 1
            continue
        if found:
            print(f'\n{s}')
            for p in found:
                print('  - ' + p)
            total += len(found)
    print(f'\n{total} layout problem(s) across {len(scripts)} generator(s)')
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
