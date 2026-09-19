"""Diagram toolkit for the APS report's block diagrams.

Separate from dg.py because the block diagrams are typeset to match the body
text: STIX serif with matching mathtext, so an equation inside a box sets in
the same face as the same equation in a paragraph. The plot figures stay on
dg.py's sans face, where a serif would only fight the axis labels.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mp
from matplotlib import rcParams
import os as _os

rcParams['font.family'] = 'STIXGeneral'
rcParams['mathtext.fontset'] = 'stix'
rcParams['figure.dpi'] = 200
rcParams['savefig.dpi'] = 260   # about 420 dpi once placed at full text width
rcParams['savefig.bbox'] = 'tight'
rcParams['savefig.pad_inches'] = 0.10
rcParams['savefig.facecolor'] = 'white'

# One colour per role, used the same way in every diagram.
P = dict(
    tel    = '#1f4e79',   # telemetry / measurement, and its band
    cmd    = '#c55a11',   # command / setpoint, and its band
    new    = '#2e7d32',   # what this year added
    bad    = '#c00000',   # a defect, a gap, a caveat
    note   = '#7030a0',   # the controller, and commentary
    grey   = '#5a5a5a',
)
# Band fills, one shade lighter than the stroke that names them.
F = dict(
    tel  = '#eef3f8', cmd = '#fdf1e6', new = '#ecf6ec',
    bad  = '#fdecec', note = '#f4eef9', grey = '#f4f6f8',
    box  = '#eef2f6', plain = '#ffffff',
)


def _upp(ax):
    """Data units per typographic point on this axes' y axis."""
    y0, y1 = ax.get_ylim()
    h_in = ax.get_position().height * ax.figure.get_figheight()
    return (y1 - y0) / (h_in * 72.0)


def canvas(w, h, xlim=100, ylim=100):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, xlim)
    ax.set_ylim(0, ylim)
    ax.axis('off')
    return fig, ax


def title(ax, x, y, main, sub='', fs=13.5, subfs=10.5, ha='left'):
    ax.text(x, y, main, ha=ha, va='top', fontsize=fs, fontweight='bold',
            color='k', zorder=9)
    if sub:
        ax.text(x, y - fs * 0.30, sub, ha=ha, va='top', fontsize=subfs,
                color='#222222', zorder=9, linespacing=1.3)


def band(ax, x, y, w, h, label, col='grey', fs=9.4, lw=1.1, pad=0.7,
         label_dx=0.6, label_dy=0.9):
    """A dashed grouping rectangle with its name sitting on the top edge."""
    ax.add_patch(mp.FancyBboxPatch((x, y), w, h,
                                   boxstyle=f'round,pad={pad}',
                                   fc=F[col], ec=P[col], lw=lw, ls='--',
                                   zorder=1))
    if label:
        ax.text(x + label_dx, y + h + pad + label_dy, label, ha='left',
                va='bottom', fontsize=fs, fontweight='bold', color=P[col],
                zorder=9)
    return (x, y, w, h)


def box(ax, x, y, w, h, txt='', col='grey', fc=None, fs=8.6, bold=False,
        lw=1.1, tc='k', pad=0.45, zorder=4, ls='-', hdr=None, hfs=None,
        hgap=1.0):
    """A rounded block. `hdr` sets a bold first line above `txt`, which is how
    a named service is written: the name in bold, what it does underneath.
    Real bold is used rather than mathtext \\bf, because mathtext respaces
    hyphens and full stops and turns Node-RED into Node-RED with a minus."""
    fc = F['box'] if fc is None else (F[fc] if fc in F else fc)
    ax.add_patch(mp.FancyBboxPatch((x, y), w, h, boxstyle=f'round,pad={pad}',
                                   fc=fc, ec=P[col], lw=lw, ls=ls,
                                   zorder=zorder))
    if hdr is None:
        ax.text(x + w / 2, y + h / 2, txt, ha='center', va='center', fontsize=fs,
                color=tc, fontweight='bold' if bold else 'normal',
                zorder=zorder + 1, linespacing=1.45)
    else:
        nb = txt.count('\n') + 1 if txt else 0
        hfs = hfs or fs
        u = _upp(ax) * hgap
        lh, lb = hfs * 1.32 * u, fs * 1.45 * u
        total = lh + nb * lb
        top = y + h / 2 + total / 2 - lh / 2
        ax.text(x + w / 2, top, hdr, ha='center', va='center', fontsize=hfs,
                color=tc, fontweight='bold', zorder=zorder + 1)
        if txt:
            ax.text(x + w / 2, top - lh / 2 - nb * lb / 2, txt, ha='center',
                    va='center', fontsize=fs, color=tc, zorder=zorder + 1,
                    linespacing=1.45)
    return (x, y, w, h)


def head(ax, x, y, w, h, txt, col='tel', fs=9.6, sub='', subfs=8.2):
    """The title strip that names a column of a three-column diagram."""
    ax.add_patch(mp.Rectangle((x, y), w, h, fc=F[col], ec='none', zorder=2))
    u = _upp(ax)
    nb = (sub.count('\n') + 1) if sub else 0
    lh, lb = fs * 1.35 * u, subfs * 1.45 * u
    total = lh + nb * lb
    top = y + h / 2 + total / 2 - lh / 2
    ax.text(x + w / 2, top, txt, ha='center', va='center', fontsize=fs,
            fontweight='bold', color='k', zorder=3)
    if sub:
        ax.text(x + w / 2, top - lh / 2 - nb * lb / 2, sub, ha='center',
                va='center', fontsize=subfs, color='#222222', zorder=3,
                linespacing=1.45)


def summ(ax, x, y, w, h, txt, col='grey', fs=8.0, tc=None):
    ax.add_patch(mp.FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.45',
                                   fc='none', ec=P[col], lw=0.9, ls='--',
                                   zorder=2))
    ax.text(x + w / 2, y + h / 2, txt, ha='center', va='center', fontsize=fs,
            color=tc or '#222222', zorder=3, linespacing=1.4)


def node(ax, x, y, r=1.9, txt=r'$\Sigma$', fs=12, col='k', lw=1.2):
    ax.add_patch(mp.Circle((x, y), r, fc='white', ec=col, lw=lw, zorder=5))
    ax.text(x, y, txt, ha='center', va='center', fontsize=fs, zorder=6)
    return (x, y, r)


def arr(ax, p0, p1, col='grey', lw=1.4, ls='-', txt='', fs=7.6, tdx=0, tdy=1.6,
        rad=0.0, tc=None, zorder=6, ha='center', va='center', mask=True,
        style='-|>', shrink=2.0):
    c = P[col] if col in P else col
    ax.annotate('', xy=p1, xytext=p0, zorder=zorder,
                arrowprops=dict(arrowstyle=style, color=c, lw=lw, ls=ls,
                                connectionstyle=f'arc3,rad={rad}',
                                shrinkA=shrink, shrinkB=shrink,
                                mutation_scale=13))
    if txt:
        ax.text((p0[0] + p1[0]) / 2 + tdx, (p0[1] + p1[1]) / 2 + tdy, txt,
                ha=ha, va=va, fontsize=fs, color=tc or c, zorder=zorder + 1,
                linespacing=1.35,
                bbox=dict(fc='white', ec='none', pad=0.15) if mask else None)


def elbow(ax, p0, p1, via='h', col='grey', lw=1.4, ls='-', zorder=6,
          style='-|>', txt='', fs=7.6, tdx=0, tdy=1.6, tc=None, at=0.5):
    """Right-angled connector. `via='h'` leaves p0 horizontally."""
    c = P[col] if col in P else col
    mid = (p1[0], p0[1]) if via == 'h' else (p0[0], p1[1])
    ax.plot([p0[0], mid[0]], [p0[1], mid[1]], color=c, lw=lw, ls=ls,
            zorder=zorder, solid_capstyle='round')
    ax.annotate('', xy=p1, xytext=mid, zorder=zorder,
                arrowprops=dict(arrowstyle=style, color=c, lw=lw, ls=ls,
                                shrinkA=0, shrinkB=2.0, mutation_scale=13))
    if txt:
        px = p0[0] + (mid[0] - p0[0]) * at, p0[1] + (mid[1] - p0[1]) * at
        ax.text(px[0] + tdx, px[1] + tdy, txt, ha='center', va='center',
                fontsize=fs, color=tc or c, zorder=zorder + 1, linespacing=1.35,
                bbox=dict(fc='white', ec='none', pad=0.15))


def route(ax, pts, col='grey', lw=1.4, ls='-', zorder=6, style='-|>'):
    """Multi-segment orthogonal run, arrowhead on the last leg."""
    c = P[col] if col in P else col
    for a, b in zip(pts[:-2], pts[1:-1]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color=c, lw=lw, ls=ls,
                zorder=zorder, solid_capstyle='round')
    ax.annotate('', xy=pts[-1], xytext=pts[-2], zorder=zorder,
                arrowprops=dict(arrowstyle=style, color=c, lw=lw, ls=ls,
                                shrinkA=0, shrinkB=2.0, mutation_scale=13))


def legend(ax, x, y, w, h, rows, fs=8.2, tfs=8.6, title_txt='Arrow legend'):
    ax.add_patch(mp.FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.5',
                                   fc='white', ec=P['grey'], lw=0.9, zorder=7))
    ax.text(x + 1.0, y + h - 0.8, title_txt, ha='left', va='top', fontsize=tfs,
            fontweight='bold', zorder=8)
    # Rows are spread over whatever is left below the title, so a short box
    # cannot push the last row out through its own bottom edge.
    u = _upp(ax)
    title_h = tfs * 1.7 * u
    avail = max(h - title_h - 0.5, 0.1)
    n = max(len(rows), 1)
    for i, (col, lab, ls) in enumerate(rows):
        yy = y + h - title_h - avail * (i + 0.5) / n
        ax.annotate('', xy=(x + 10.5, yy), xytext=(x + 1.2, yy), zorder=8,
                    arrowprops=dict(arrowstyle='-|>', color=P[col], lw=1.5,
                                    ls=ls, mutation_scale=12))
        ax.text(x + 11.8, yy, lab, ha='left', va='center', fontsize=fs,
                zorder=8)


def caveat(ax, x, y, txt, fs=8.2, col='bad', ha='left'):
    ax.text(x, y, txt, ha=ha, va='top', fontsize=fs, color=P[col], zorder=9,
            linespacing=1.4)


def R(b): return (b[0] + b[2], b[1] + b[3] / 2)
def L(b): return (b[0], b[1] + b[3] / 2)
def T(b): return (b[0] + b[2] / 2, b[1] + b[3])
def B(b): return (b[0] + b[2] / 2, b[1])
def Cn(b): return (b[0] + b[2] / 2, b[1] + b[3] / 2)


_HERE = _os.path.dirname(_os.path.abspath(__file__))
FIGDIR = _os.path.join(_os.path.dirname(_HERE), 'figures')


def save(fig, name):
    p = _os.path.join(FIGDIR, name)
    fig.savefig(p)
    plt.close(fig)
    from PIL import Image
    print('%-34s %s' % (name, '%dx%d' % Image.open(p).size))
    return p
