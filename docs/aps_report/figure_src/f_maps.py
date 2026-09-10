"""Figure 29 — the three commissioning maps, with the area actually driven.

Each panel is the saved occupancy grid exactly as `map_saver_cli` wrote it,
placed in world coordinates from its own YAML origin and resolution. Over it
runs the pose the robot believed it had at the time, taken from the same log
that Figure 16 uses for the correction traces, with red dots marking where it
actually stood. The dots are the point of the figure: the mapped extent is much
larger than the ground the robot ever covered, which is what a sparse map looks
like when the drive procedure sweeps walls it never approaches.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np, csv

RUNS = [
    ('front leg, 31 Aug',            'run_20260831', 'run_20260831_155316',
     'run_20260831_155316_pose_trimmed.csv', C['defect']),
    ('right leg, 31 Aug',            'run_20260831', 'run_20260831_191509',
     'run_20260831_191509_pose.csv',          C['fixed']),
    ('front leg re-driven, 1 Sep',   'run_20260901', 'run_20260901_112335',
     'run_20260901_112335_pose.csv',          C['accent']),
]

UNKNOWN = 205          # the value map_saver writes for never-observed cells


def read_pgm(path):
    """Minimal binary P5 reader; the maps carry no comments."""
    with open(path, 'rb') as f:
        assert f.readline().strip() == b'P5'
        w, h = (int(v) for v in f.readline().split())
        maxval = int(f.readline())
        data = np.frombuffer(f.read(w*h), dtype=np.uint8).reshape(h, w)
    return data, maxval


def read_yaml(path):
    meta = {}
    for line in open(path):
        if ':' not in line:
            continue
        k, v = line.split(':', 1)
        meta[k.strip()] = v.strip()
    res = float(meta['resolution'])
    ox, oy = (float(v) for v in meta['origin'].strip('[]').split(',')[:2])
    return res, ox, oy


def read_pose(path):
    xs, ys = [], []
    for r in csv.DictReader(open(path)):
        try:
            x, y = float(r['map_x']), float(r['map_y'])
        except (TypeError, ValueError, KeyError):
            continue
        if np.isfinite(x) and np.isfinite(y):
            xs.append(x); ys.append(y)
    return np.array(xs), np.array(ys)


fig, axes = plt.subplots(1, 3, figsize=(10.6, 4.0))
REPO_RUNS = f'{REPO}/data/field_runs'

# One shared window across all three panels: the maps differ in size, and with
# an equal aspect that would render them at three different heights and make
# them look like three different places at three different scales.
bounds = []
for _, folder, stem, _, _ in RUNS:
    img, _m = read_pgm(f'{REPO_RUNS}/{folder}/{stem}.pgm')
    res, ox, oy = read_yaml(f'{REPO_RUNS}/{folder}/{stem}.yaml')
    h, w = img.shape
    bounds.append((ox, ox + w*res, oy, oy + h*res))
X0 = min(b[0] for b in bounds); X1 = max(b[1] for b in bounds)
Y0 = min(b[2] for b in bounds); Y1 = max(b[3] for b in bounds)

for ax, (name, folder, stem, posefile, col) in zip(axes, RUNS):
    img, _ = read_pgm(f'{REPO_RUNS}/{folder}/{stem}.pgm')
    res, ox, oy = read_yaml(f'{REPO_RUNS}/{folder}/{stem}.yaml')
    h, w = img.shape
    extent = [ox, ox + w*res, oy, oy + h*res]
    ax.imshow(img, cmap='gray', vmin=0, vmax=255, origin='upper',
              extent=extent, interpolation='nearest', zorder=1)

    known = float(np.mean(img != UNKNOWN) * 100)
    occ = int(np.sum(img < 100))

    xs, ys = read_pose(f'{REPO_RUNS}/{folder}/{posefile}')
    if len(xs):
        ax.plot(xs, ys, color=col, lw=1.3, zorder=3, solid_capstyle='round')
        # every twenty-fifth pose, so the dots read as a track rather than a smear
        ax.scatter(xs[::25], ys[::25], s=7, color=C['defect'], zorder=4,
                   edgecolors='none')
        ax.plot(xs[0], ys[0], marker='o', ms=6, mfc='white', mec=col, mew=1.4,
                zorder=5)

    ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1)
    ax.set_aspect('equal')
    ax.set_xlabel('map x (m)', fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.15)
    ax.set_title(f'{name}\n{known:.0f} % of cells observed · {occ} occupied',
                 loc='left', fontsize=8.4)

axes[0].set_ylabel('map y (m)', fontsize=8)
h1 = plt.Line2D([], [], color=C['neutral'], lw=1.3)
h2 = plt.Line2D([], [], marker='o', ls='none', ms=4, color=C['defect'])
h3 = plt.Line2D([], [], marker='o', ls='none', ms=6, mfc='white',
                mec=C['neutral'], mew=1.4)
fig.legend([h1, h2, h3],
           ['believed path during the drive', 'where the robot stood (every 25th pose)',
            'start of the drive'],
           loc='lower center', ncol=3, fontsize=7.6, bbox_to_anchor=(0.5, -0.10))
fig.suptitle('The three commissioning maps, with the ground actually covered marked in red. '
             'Grey is never observed.\nThe driven area is a small fraction of the mapped '
             'extent, which is the sparsity of §7.4 seen directly.',
             fontsize=9.5, y=1.04, x=0.02, ha='left')
plt.tight_layout()
plt.savefig(f'{FIGDIR}/fig29_field_maps.png', bbox_inches='tight')
plt.close()
print('ok')
